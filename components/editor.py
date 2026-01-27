import streamlit as st
import os
import re
import uuid
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
        
        # --- ATTACHMENT MANAGER ---
        st.subheader("📎 Attachments")
        
        # 1. Upload Logic
        # Resets uploader when key increments
        new_att = st.file_uploader(
            "Upload File", 
            label_visibility="collapsed",
            key=f"uploader_{st.session_state.uploader_key}" 
        )
        
        if new_att:
            # Ensure Shared Directory Exists
            if not os.path.exists(ATTACHMENTS_DIR): os.makedirs(ATTACHMENTS_DIR)
            
            # Generate Unique Filename to prevent collisions in shared pool
            # e.g. "a1b2c3d4_Resumefinal.pdf"
            unique_id = uuid.uuid4().hex[:8]
            safe_filename = f"{unique_id}_{new_att.name}"
            save_path = os.path.join(ATTACHMENTS_DIR, safe_filename)
            
            with open(save_path, "wb") as f:
                f.write(new_att.getbuffer())
            
            st.session_state.attachment_path = save_path
            # Default name is original filename
            st.session_state.attachment_name = new_att.name
            
            # Reset uploader
            st.session_state.uploader_key += 1
            
            trigger_save()
            st.rerun()

        # 2. Rename & Remove Logic
        if st.session_state.attachment_path and os.path.exists(st.session_state.attachment_path):
            st.success(f"File Uploaded: {st.session_state.attachment_name}")
            
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
                # Note: We just remove the reference from the session here.
                # Actual file deletion happens via 'Smart Delete' when session/template is deleted
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
                if v in curr_map and curr_map[v] in cols: 
                    def_idx = cols.index(curr_map[v])
                else: 
                    def_idx = next((i for i, c in enumerate(cols) if v.lower() in c.lower()), 0)
                
                new_map[v] = st.selectbox(f"{{{v}}}", cols, index=def_idx, key=f"map_{v}")
            
            st.session_state.mapping = new_map