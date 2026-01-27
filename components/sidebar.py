import streamlit as st
import re
import os
from utils.session import (
    load_session, list_sessions, list_templates, 
    load_template_file, save_template_file, delete_session, delete_template_file
)
from components.state import trigger_save

def render_sidebar():
    with st.sidebar:
        st.header("📂 Session Manager")
        
        # --- SESSION MANAGEMENT ---
        with st.expander("Create / Switch Session", expanded=True):
            # Create
            new_sess = st.text_input("New Session Name", placeholder="e.g. Batch_2")
            if st.button("➕ Create Session"):
                if new_sess:
                    clean = re.sub(r'[^a-zA-Z0-9_]', '_', new_sess)
                    st.session_state.current_session = clean
                    st.session_state.df_processed = None
                    st.session_state.sent_ids = set()
                    st.session_state.mapping = {}
                    st.session_state.attachment_path = None
                    st.session_state.attachment_name = ""
                    trigger_save()
                    st.rerun()
            
            # Select
            sessions = list_sessions()
            idx = 0
            if st.session_state.current_session in sessions:
                idx = sessions.index(st.session_state.current_session)
            
            # Layout for Select + Delete
            col_sel, col_del = st.columns([5, 1])
            with col_sel:
                sel_sess = st.selectbox(
                    "Active Session", 
                    ["-- Select --"] + sessions, 
                    index=idx + 1 if st.session_state.current_session else 0,
                    label_visibility="collapsed"
                )
            
            # Delete Session Logic
            if st.session_state.current_session:
                with col_del:
                    if st.button("🗑️", help="Delete Session"):
                        st.session_state.delete_confirm_sess = st.session_state.current_session
            
            # Confirm Dialog for Session
            if st.session_state.get('delete_confirm_sess'):
                st.warning(f"Delete '{st.session_state.delete_confirm_sess}'?")
                c1, c2 = st.columns(2)
                if c1.button("Yes, Delete"):
                    delete_session(st.session_state.delete_confirm_sess)
                    st.session_state.current_session = None
                    st.session_state.delete_confirm_sess = None
                    st.rerun()
                if c2.button("Cancel"):
                    st.session_state.delete_confirm_sess = None
                    st.rerun()

            # Load Session Logic
            if sel_sess != "-- Select --" and sel_sess != st.session_state.current_session:
                state = load_session(sel_sess)
                if state:
                    st.session_state.current_session = sel_sess
                    st.session_state.df_processed = state['data']
                    st.session_state.sent_ids = state['sent_ids']
                    st.session_state.mapping = state['mapping']
                    
                    # Load Inputs
                    st.session_state.input_subject = state['template'].get('subject', '')
                    st.session_state.input_body = state['template'].get('body', '')
                    st.session_state.input_is_html = state['template'].get('is_html', False)
                    st.session_state.attachment_path = state['template'].get('attachment_path')
                    st.session_state.attachment_name = state['template'].get('attachment_name')
                    st.rerun()

        if not st.session_state.current_session:
            st.warning("Please create or select a session.")
            st.stop()

        st.success(f"🔵 Active: {st.session_state.current_session}")
        st.divider()

        # --- TEMPLATE LIBRARY ---
        st.header("📝 Template Library")
        with st.expander("Save / Load Templates"):
            tpl_name = st.text_input("Save Current as...", placeholder="e.g. Followup")
            if st.button("💾 Save to Library"):
                if tpl_name:
                    save_template_file(
                        tpl_name, 
                        st.session_state.input_subject,
                        st.session_state.input_body,
                        st.session_state.input_is_html,
                        st.session_state.attachment_path,
                        st.session_state.attachment_name
                    )
                    st.toast(f"Saved: {tpl_name}")

            st.markdown("---")
            
            templates = list_templates()
            
            # Layout for Load + Delete
            t_col_sel, t_col_del = st.columns([5, 1])
            with t_col_sel:
                sel_tpl = st.selectbox("Load Template", ["-- Select --"] + templates)
            
            with t_col_del:
                # We need a key to identify which template is selected for deletion
                # Using session state to track potential deletion target
                if sel_tpl != "-- Select --":
                    if st.button("🗑️", key="del_tpl_btn", help="Delete Template"):
                        st.session_state.delete_confirm_tpl = sel_tpl

            # Confirm Dialog for Template
            if st.session_state.get('delete_confirm_tpl'):
                st.warning(f"Delete template '{st.session_state.delete_confirm_tpl}'?")
                tc1, tc2 = st.columns(2)
                if tc1.button("Yes", key="conf_del_tpl"):
                    delete_template_file(st.session_state.delete_confirm_tpl)
                    st.session_state.delete_confirm_tpl = None
                    st.rerun()
                if tc2.button("No", key="canc_del_tpl"):
                    st.session_state.delete_confirm_tpl = None
                    st.rerun()

            if st.button("📂 Load Template"):
                if sel_tpl != "-- Select --":
                    tpl = load_template_file(sel_tpl)
                    if tpl:
                        st.session_state.input_subject = tpl.get('subject', '')
                        st.session_state.input_body = tpl.get('body', '')
                        st.session_state.input_is_html = tpl.get('is_html', False)
                        
                        # Handle Attachment Loading
                        # If template has attachment, we use that path.
                        # Note: This path points to templates/attachments/
                        st.session_state.attachment_path = tpl.get('attachment_path')
                        st.session_state.attachment_name = tpl.get('attachment_name')
                        
                        trigger_save()
                        st.rerun()
        
        st.divider()
        
        # --- SETTINGS ---
        st.subheader("⚙️ Settings")
        min_d = st.number_input("Min Delay", 20)
        max_d = st.number_input("Max Delay", 50)
        batch_sz = st.number_input("Batch Size", 20)
        batch_dl = st.number_input("Batch Pause", 300)
        
        return min_d, max_d, batch_sz, batch_dl