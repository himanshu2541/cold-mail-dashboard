import streamlit as st
import pandas as pd
import time
import random
import re
import os
from dotenv import load_dotenv

# Custom modules
from utils.processor import process_data
from utils.session import save_state, load_state
from utils.sender import EmailSender

# Load Env
load_dotenv()

st.set_page_config(page_title="Mail Dashboard", layout="wide")
st.title("📨 Project Mail Sender")

# --- 1. CREDENTIAL CHECK ---
if not os.getenv("SENDER_EMAIL") or not os.getenv("APP_PASSWORD"):
    st.error("⛔ CRITICAL ERROR: Credentials not found!")
    st.info("Please create a `.env` file in the project folder with:\n\nSENDER_EMAIL=...\nAPP_PASSWORD=...")
    st.stop()

# --- 2. SESSION MANAGEMENT ---
if 'df_processed' not in st.session_state:
    st.session_state.df_processed = None
if 'sent_ids' not in st.session_state:
    st.session_state.sent_ids = set()

# Load previous session
if st.sidebar.button("📂 Load Last Session"):
    saved_state = load_state()
    if saved_state:
        st.session_state.df_processed = saved_state['data']
        st.session_state.sent_ids = saved_state['sent_ids']
        st.success("Loaded previous project data!")
    else:
        st.warning("No saved session found.")

# --- SIDEBAR CONFIG ---
with st.sidebar:
    st.header("⚙️ Configuration")
    st.success(f"Logged in as: {os.getenv('SENDER_EMAIL')}")
    
    st.divider()
    st.subheader("⏱️ Time Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        min_delay = st.number_input("Min Delay (s)", value=20, help="Wait at least this long between emails")
    with col2:
        max_delay = st.number_input("Max Delay (s)", value=50, help="Wait at most this long between emails")
    
    st.markdown("---")
    st.markdown("**Batch Control**")
    batch_size = st.number_input("Emails per Batch", value=20, help="How many emails to send before taking a break")
    
    # UPDATED: Default set to 300 seconds (5 minutes)
    batch_delay = st.number_input(
        "Batch Pause (seconds)", 
        value=300, 
        step=10,
        help="Time to wait between batches. Default: 300s (5 mins)"
    )

# --- STEP 1: UPLOAD & PROCESS ---
st.header("1. Data Input")

uploaded_file = st.file_uploader("Upload Excel/CSV", type=['xlsx', 'csv'])

if uploaded_file:
    # Read Raw
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)
    
    # Try to guess email column
    cols = df_raw.columns.tolist()
    guess_idx = next((i for i, c in enumerate(cols) if 'email' in c.lower()), 0)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"Loaded raw file with {len(df_raw)} rows.")
    with col2:
        email_col = st.selectbox("Select Email Column", cols, index=guess_idx)
    
    if st.button("⚡ Process Data (Split Multiple Emails & Fix Errors)"):
        with st.spinner("Normalizing data..."):
            processed_df = process_data(df_raw, email_col)
            st.session_state.df_processed = processed_df
            st.success(f"Processed! Generated {len(processed_df)} unique mail tasks.")

# Show Processed Data
if st.session_state.df_processed is not None:
    st.subheader("Recipients List")
    st.dataframe(st.session_state.df_processed.head(3))
    
    # Progress Metric
    total = len(st.session_state.df_processed)
    sent = len([i for i in st.session_state.df_processed['_id'] if i in st.session_state.sent_ids])
    st.progress(sent / total if total > 0 else 0)
    st.caption(f"Progress: {sent} sent out of {total} total tasks")

if st.session_state.df_processed is not None:
    st.header("2. Template & Mapping")
    
    col1, col2 = st.columns(2)
    with col1:
        subject_tpl = st.text_input("Subject", "Hello {Name}")
        body_tpl = st.text_area("Body", "Hi {Name},\n\nI am writing to you...", height=200)
    
    with col2:
        st.markdown("**Variable Mapping**")
        vars_needed = set(re.findall(r'\{([^}]+)\}', subject_tpl + body_tpl))
        cols = st.session_state.df_processed.columns.tolist()
        
        mapping = {}
        # Filter out the internal ID column
        display_cols = [c for c in cols if c != '_id']
        
        for v in vars_needed:
            # Smart auto-select
            default_idx = next((i for i, c in enumerate(display_cols) if v.lower() in c.lower()), 0)
            mapping[v] = st.selectbox(f"Map '{{{v}}}' to:", display_cols, index=default_idx)

# --- STEP 3: SEND ---
if st.session_state.df_processed is not None:
    st.header("3. Launch Campaign")
    
    if st.button("🚀 Start / Resume", type="primary"):
        sender = EmailSender() 
        
        # UI Elements
        status_box = st.status("Running Campaign...", expanded=True)
        log_area = st.container()
        
        df = st.session_state.df_processed
        
        # Counters for this run
        batch_counter = 0
        
        for idx, row in df.iterrows():
            uid = row['_id']
            email = row[email_col]
            
            # 1. Skip if already sent
            if uid in st.session_state.sent_ids:
                continue
            
            # 2. Check Batch Limit
            # We check if we have sent any emails this session to avoid immediate pause
            if batch_counter > 0 and batch_counter % batch_size == 0:
                status_box.update(label=f"Sleeping for {batch_delay}s (Batch limit reached)...", state="running")
                time.sleep(batch_delay)
                status_box.update(label="Resuming...", state="running")
                
            try:
                # 3. Prepare Content
                ctx = {v: str(row[mapping[v]]) for v in vars_needed}
                final_subj = subject_tpl.format(**ctx)
                final_body = body_tpl.format(**ctx)
                
                # 4. Send
                status_box.write(f"Sending to {email}...")
                ok, msg = sender.send_email(email, final_subj, final_body)
                
                if ok:
                    # Mark as sent
                    st.session_state.sent_ids.add(uid)
                    batch_counter += 1
                    
                    with log_area:
                        st.toast(f"✅ Sent: {email}")
                    
                    # 5. Auto-Save State
                    save_state(
                        {"sub": subject_tpl, "body": body_tpl}, 
                        mapping, 
                        df, 
                        st.session_state.sent_ids
                    )
                else:
                    st.error(f"❌ Failed: {email} - {msg}")
                
                # 6. Random Delay between emails
                time.sleep(random.randint(min_delay, max_delay))
                
            except Exception as e:
                st.error(f"Error on row {idx}: {e}")
        
        status_box.update(label="Campaign Complete!", state="complete", expanded=False)
        st.success("All emails in the list have been processed.")