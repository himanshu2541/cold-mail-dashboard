import streamlit as st
import re
from utils.session import load_session, list_sessions, list_templates, load_template_file, save_template_file
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
            
            sel_sess = st.selectbox("Active Session", ["-- Select --"] + sessions, index=idx + 1 if st.session_state.current_session else 0)
            
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
                        st.session_state.input_is_html
                    )
                    st.toast(f"Saved: {tpl_name}")

            st.markdown("---")
            
            templates = list_templates()
            sel_tpl = st.selectbox("Load Template", ["-- Select --"] + templates)
            if st.button("📂 Load Template"):
                if sel_tpl != "-- Select --":
                    tpl = load_template_file(sel_tpl)
                    if tpl:
                        st.session_state.input_subject = tpl['subject']
                        st.session_state.input_body = tpl['body']
                        st.session_state.input_is_html = tpl['is_html']
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