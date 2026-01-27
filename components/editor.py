import streamlit as st
import os
import re
from utils.session import ATTACHMENTS_DIR
from components.state import trigger_save

def render_editor():
    st.header("1. Compose Email")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.text_input("Subject", key="input_subject", on_change=trigger_save)
        st.text_area("Body", height=300, key="input_body", on_change=trigger_save)
        st.checkbox("Send as HTML", key="input_is_html", on_change=trigger_save)

        st.divider()
        
        # --- ATTACHMENT MANAGER (RESTORED!) ---
        st.subheader("📎 Attachments")
        
        # 1. Upload Logic
        new_att = st.file_uploader("Upload File", label_visibility="collapsed")
        if new_att:
            sess_dir = os.path.join(ATTACHMENTS_DIR, st.session_state.current_session)
            if not os.path.exists(sess_dir): os.makedirs(sess_dir)
            
            save_path = os.path.join(sess_dir, new_att.name)
            with open(save_path, "wb") as f:
                f.write(new_att.getbuffer())
            
            st.session_state.attachment_path = save_path
            # Default name is filename
            st.session_state.attachment_name = new_att.name
            trigger_save()
            st.rerun()

        # 2. Rename & Remove Logic
        if st.session_state.attachment_path:
            st.success(f"File Uploaded: {os.path.basename(st.session_state.attachment_path)}")
            
            # THE RENAME FEATURE
            c_a, c_b = st.columns([3, 1])
            with c_a:
                new_name = st.text_input(
                    "Attachment Name (as seen by recipient)", 
                    value=st.session_state.attachment_name
                )
                if new_name != st.session_state.attachment_name:
                    st.session_state.attachment_name = new_name
                    trigger_save()
            
            with c_b:
                st.write("") # Spacer
                st.write("")
                if st.button("❌ Remove"):
                    st.session_state.attachment_path = None
                    st.session_state.attachment_name = ""
                    trigger_save()
                    st.rerun()

    # --- VARIABLE MAPPING ---
    with col2:
        st.markdown("### 🗺️ Variables")
        if st.session_state.df_processed is None:
            st.info("Upload data to map variables.")
        else:
            subject = st.session_state.input_subject
            body = st.session_state.input_body
            vars_needed = set(re.findall(r'\{([^}]+)\}', subject + body))
            cols = [c for c in st.session_state.df_processed.columns if c != '_id']
            
            curr_map = st.session_state.mapping
            new_map = {}
            for v in vars_needed:
                def_idx = 0
                # Try to preserve existing map or guess
                if v in curr_map and curr_map[v] in cols: 
                    def_idx = cols.index(curr_map[v])
                else: 
                    def_idx = next((i for i, c in enumerate(cols) if v.lower() in c.lower()), 0)
                
                new_map[v] = st.selectbox(f"{{{v}}}", cols, index=def_idx, key=f"map_{v}")
            
            st.session_state.mapping = new_map