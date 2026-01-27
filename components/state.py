import streamlit as st
from utils.session import save_session

def trigger_save():
    """Saves the current session state to the JSON file."""
    if st.session_state.get('current_session'):
        # Gather Template Data
        tpl_data = {
            "subject": st.session_state.get('input_subject', ''),
            "body": st.session_state.get('input_body', ''),
            "is_html": st.session_state.get('input_is_html', False),
            "attachment_path": st.session_state.get('attachment_path'),
            "attachment_name": st.session_state.get('attachment_name')
        }
        
        save_session(
            st.session_state.current_session,
            tpl_data,
            st.session_state.get('mapping', {}),
            st.session_state.get('df_processed'),
            st.session_state.get('sent_ids', set())
        )

def init_state():
    """Initializes session state variables."""
    defaults = {
        'df_processed': None,
        'sent_ids': set(),
        'current_session': None,
        'mapping': {},
        'attachment_path': None,
        'attachment_name': "",
        'input_subject': "",
        'input_body': "",
        'input_is_html': False,
        'is_running': False,
        'delete_confirm_sess': None,
        'delete_confirm_tpl': None,
        'uploader_key': 0 
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val