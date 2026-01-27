import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import time
import random
import re
import os
from dotenv import load_dotenv

# Custom modules
from utils.processor import process_data
from utils.session import save_session, load_session, list_sessions, delete_session
from utils.sender import EmailSender

# Load Env
load_dotenv()

st.set_page_config(page_title="Cold Mail Dashboard", layout="wide")
st.title("📨 Project Mail Sender")

# --- 0. HELPER: AUTO-SAVE ---
def trigger_save():
    """Helper to save current state to the active session"""
    if st.session_state.get('current_session'):
        # Get Template Data
        tpl_data = {
            "subject": st.session_state.get('input_subject', ''),
            "body": st.session_state.get('input_body', ''),
            "is_html": st.session_state.get('input_is_html', False)
        }
        
        save_session(
            st.session_state.current_session,
            tpl_data,
            st.session_state.get('mapping', {}),
            st.session_state.get('df_processed'),
            st.session_state.get('sent_ids', set())
        )

# --- 1. SESSION STATE INIT ---
if 'df_processed' not in st.session_state:
    st.session_state.df_processed = None
if 'sent_ids' not in st.session_state:
    st.session_state.sent_ids = set()
if 'current_session' not in st.session_state:
    st.session_state.current_session = None
if 'mapping' not in st.session_state:
    st.session_state.mapping = {}

# --- 2. SIDEBAR: SESSION MANAGER ---
with st.sidebar:
    st.header("📂 Session Manager")
    
    # Create New Session
    with st.expander("Create New Session", expanded=False):
        new_session_name = st.text_input("New Session Name", placeholder="e.g. Winter_Campaign")
        if st.button("➕ Create & Switch"):
            if new_session_name:
                clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', new_session_name)
                st.session_state.current_session = clean_name
                st.session_state.df_processed = None
                st.session_state.sent_ids = set()
                st.session_state.mapping = {}
                # Clear inputs
                st.session_state.input_subject = ""
                st.session_state.input_body = ""
                trigger_save()
                st.rerun()

    # Load Existing Session
    available_sessions = list_sessions()
    
    # Determine index for selectbox
    idx = 0
    if st.session_state.current_session in available_sessions:
        idx = available_sessions.index(st.session_state.current_session)
    
    selected_session = st.selectbox(
        "Select Active Session", 
        options=["-- Select --"] + available_sessions,
        index=idx + 1 if st.session_state.current_session else 0
    )

    if selected_session != "-- Select --" and selected_session != st.session_state.current_session:
        # Load logic
        state = load_session(selected_session)
        if state:
            st.session_state.current_session = selected_session
            st.session_state.df_processed = state['data']
            st.session_state.sent_ids = state['sent_ids']
            st.session_state.mapping = state['mapping']
            
            # Load template into session state for widgets
            st.session_state.input_subject = state['template'].get('subject', '')
            st.session_state.input_body = state['template'].get('body', '')
            st.session_state.input_is_html = state['template'].get('is_html', False)
            
            st.success(f"Loaded: {selected_session}")
            st.rerun()

    if st.session_state.current_session:
        st.info(f"🔵 Active: **{st.session_state.current_session}**")
        if st.button("💾 Force Save"):
            trigger_save()
            st.toast("Saved successfully!")
    else:
        st.warning("Please create or select a session to start.")
        st.stop() # Stop execution if no session

    st.divider()
    
    # Settings
    st.subheader("⚙️ Settings")
    min_delay = st.number_input("Min Delay (s)", 20)
    max_delay = st.number_input("Max Delay (s)", 50)
    batch_size = st.number_input("Batch Size", 20)
    batch_delay = st.number_input("Batch Pause (s)", 300)

# --- 3. DATA INPUT ---
st.header("1. Data & Recipients")

# Only show upload if we don't have data, or want to replace it
if st.session_state.df_processed is None:
    uploaded_file = st.file_uploader("Upload Excel/CSV", type=['xlsx', 'csv'])
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
        
        cols = df_raw.columns.tolist()
        guess_idx = next((i for i, c in enumerate(cols) if 'email' in c.lower()), 0)
        email_col = st.selectbox("Select Email Column", cols, index=guess_idx)
        
        if st.button("⚡ Process & Save Data"):
            with st.spinner("Processing..."):
                processed_df = process_data(df_raw, email_col)
                st.session_state.df_processed = processed_df
                trigger_save() # <--- SAVES IMMEDIATELY
                st.rerun()
else:
    # Data is loaded
    st.success(f"✅ Data Loaded: {len(st.session_state.df_processed)} recipients")
    with st.expander("View Data"):
        st.dataframe(st.session_state.df_processed.head())
    
    if st.button("🗑️ Clear Data & Upload New"):
        st.session_state.df_processed = None
        st.session_state.sent_ids = set()
        st.rerun()

# --- 4. TEMPLATE ENGINE (WRITE & PREVIEW) ---
if st.session_state.df_processed is not None:
    st.header("2. Compose Email")
    
    # Tabs for Write vs Preview
    tab_write, tab_preview = st.tabs(["✏️ Write & Map", "👁️ Preview"])
    
    with tab_write:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            subject = st.text_input("Subject", key="input_subject")
            body = st.text_area("Email Body", height=300, key="input_body", help="Use {Variable} for placeholders")
            is_html = st.checkbox("Send as HTML", key="input_is_html")
            
            if st.button("💾 Save Template"):
                trigger_save()
                st.toast("Template saved!")
        
        with col2:
            st.markdown("### 🗺️ Map Variables")
            st.info("Map your {Placeholders} to Excel Columns")
            
            # Find variables
            vars_in_text = set(re.findall(r'\{([^}]+)\}', subject + body))
            cols = [c for c in st.session_state.df_processed.columns if c != '_id']
            
            # Dynamic Mapping Inputs
            current_mapping = st.session_state.mapping
            new_mapping = {}
            
            for v in vars_in_text:
                # Try to find existing map or guess
                default_idx = 0
                if v in current_mapping and current_mapping[v] in cols:
                    default_idx = cols.index(current_mapping[v])
                else:
                    # Guess
                    default_idx = next((i for i, c in enumerate(cols) if v.lower() in c.lower()), 0)
                
                selected_col = st.selectbox(f"{{{v}}}", cols, index=default_idx, key=f"map_{v}")
                new_mapping[v] = selected_col
            
            # Update mapping in state
            st.session_state.mapping = new_mapping

    with tab_preview:
        st.markdown("### 📧 Preview")
        st.caption("This preview simulates a Light Mode email client to ensure colors appear correctly.")
        
        if st.session_state.df_processed is not None and len(st.session_state.df_processed) > 0:
            # Controls to cycle through recipients
            prev_col, next_col, _ = st.columns([1, 1, 4])
            if 'preview_idx' not in st.session_state:
                st.session_state.preview_idx = 0
                
            if prev_col.button("⬅️ Previous"):
                st.session_state.preview_idx = max(0, st.session_state.preview_idx - 1)
            if next_col.button("Next ➡️"):
                st.session_state.preview_idx = min(len(st.session_state.df_processed) - 1, st.session_state.preview_idx + 1)
            
            # Get Data Row
            row = st.session_state.df_processed.iloc[st.session_state.preview_idx]
            
            try:
                # Substitute
                ctx = {v: str(row[st.session_state.mapping.get(v, v)]) for v in vars_in_text}
                prev_subj = subject.format(**ctx)
                prev_body = body.format(**ctx)
                
                # Display Headers
                st.markdown(f"**To:** {row.get('Email', 'Unknown')}")
                st.markdown(f"**Subject:** {prev_subj}")
                st.divider()
                
                if is_html:
                    # --- FIX: FORCE LIGHT MODE WRAPPER ---
                    html_preview = f"""
                    <div style="
                        background-color: #ffffff; 
                        color: #000000; 
                        padding: 20px; 
                        border: 1px solid #e0e0e0;
                        border-radius: 5px; 
                        font-family: Arial, sans-serif;
                    ">
                        {prev_body}
                    </div>
                    """
                    # Render with sufficient height
                    components.html(html_preview, height=600, scrolling=True)
                else:
                    st.text(prev_body)
                    
            except KeyError as e:
                st.error(f"Mapping Error: {e}. Please check the 'Map Variables' section.")
            except Exception as e:
                st.error(f"Preview Error: {e}")
        else:
            st.warning("No data loaded to preview.")

# --- 5. SENDING ---
if st.session_state.df_processed is not None:
    st.header("3. Launch Campaign")
    
    # Identify Email Column
    cols = st.session_state.df_processed.columns.tolist()
    target_email_col = st.selectbox("Confirm Column to Send To:", cols, 
                                    index=next((i for i, c in enumerate(cols) if 'email' in c.lower()), 0))

    if st.button("🚀 Start / Resume Campaign", type="primary"):
        if not os.getenv("SENDER_EMAIL"):
            st.error("Missing .env credentials!")
            st.stop()
            
        sender = EmailSender()
        trigger_save() # Save before starting
        
        progress_bar = st.progress(0)
        status = st.empty()
        log = st.container()
        
        df = st.session_state.df_processed
        total = len(df)
        batch_count = 0
        
        for idx, row in df.iterrows():
            uid = row['_id']
            email_addr = row[target_email_col]
            
            # SKIP IF SENT
            if uid in st.session_state.sent_ids:
                continue
            
            # BATCH PAUSE
            if batch_count > 0 and batch_count % batch_size == 0:
                status.warning(f"Batch limit hit. Pausing for {batch_delay}s...")
                time.sleep(batch_delay)
            
            try:
                # PREPARE: read template values from session state to avoid unbound variables
                subject = st.session_state.get('input_subject', '')
                body = st.session_state.get('input_body', '')
                is_html = st.session_state.get('input_is_html', False)

                vars_in_text = set(re.findall(r'\{([^}]+)\}', subject + body))
                ctx = {v: str(row[st.session_state.mapping.get(v, v)]) for v in vars_in_text}
                
                final_subj = subject.format(**ctx)
                final_body = body.format(**ctx)
                
                # SEND
                status.text(f"Sending to {email_addr}...")
                ok, msg = sender.send_email(email_addr, final_subj, final_body, is_html=is_html)
                
                if ok:
                    st.session_state.sent_ids.add(uid)
                    batch_count += 1
                    with log:
                        st.success(f"✅ Sent: {email_addr}")
                    
                    # SAVE PROGRESS IMMEDIATELY
                    trigger_save()
                else:
                    with log:
                        st.error(f"❌ Failed: {email_addr} - {msg}")
                
                time.sleep(random.randint(min_delay, max_delay))
                
            except Exception as e:
                st.error(f"Row Error: {e}")
                
        st.success("Campaign Run Complete!")