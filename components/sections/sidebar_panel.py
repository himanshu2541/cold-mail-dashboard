import re

import streamlit as st

from components.state import trigger_save
from components.ui.icons import icon
from utils.session import (
    create_follow_up_session,
    delete_session,
    delete_template_file,
    list_sessions,
    list_templates,
    load_session,
    load_template_file,
    save_template_file,
)


def _reset_for_new_session(session_name):
    st.session_state.current_session = session_name
    st.session_state.df_processed = None
    st.session_state.sent_ids = set()
    st.session_state.sent_history = []
    st.session_state.tracking_state = {}
    st.session_state.mapping = {}
    st.session_state.attachment_path = None
    st.session_state.attachment_name = ""
    st.session_state.campaign_stage = 0
    st.session_state.parent_session = None


def _load_selected_session(session_name):
    state = load_session(session_name)
    if not state:
        return

    st.session_state.current_session = session_name
    st.session_state.df_processed = state["data"]
    st.session_state.sent_ids = state["sent_ids"]
    st.session_state.sent_history = state["sent_history"]
    st.session_state.tracking_state = state["tracking_state"]
    st.session_state.mapping = state["mapping"]
    st.session_state.campaign_stage = state["campaign_stage"]
    st.session_state.parent_session = state["parent_session"]
    st.session_state.input_subject = state["template"].get("subject", "")
    st.session_state.input_body = state["template"].get("body", "")
    st.session_state.input_is_html = state["template"].get("is_html", False)
    st.session_state.attachment_path = state["template"].get("attachment_path")
    st.session_state.attachment_name = state["template"].get("attachment_name")


def _render_session_manager():
    st.markdown(f"### {icon(':file_folder:', '🗂️')} Sessions")
    new_session_name = st.text_input("New Session Name", placeholder="e.g. May_Followup_1")
    if st.button("Create Session", use_container_width=True):
        if new_session_name:
            clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", new_session_name)
            _reset_for_new_session(clean_name)
            trigger_save()
            st.rerun()

    sessions = list_sessions()
    idx = sessions.index(st.session_state.current_session) if st.session_state.current_session in sessions else -1

    selected = st.selectbox(
        "Active Session",
        ["-- Select --"] + sessions,
        index=idx + 1 if idx >= 0 else 0,
    )

    if selected != "-- Select --" and selected != st.session_state.current_session:
        _load_selected_session(selected)
        st.rerun()

    if st.session_state.current_session:
        st.success(f"{icon(':white_check_mark:', '✅')} Active: {st.session_state.current_session}")
        if st.button("Delete Current Session", use_container_width=True):
            st.session_state.delete_confirm_sess = st.session_state.current_session

    if st.session_state.get("delete_confirm_sess"):
        st.warning(f"Delete '{st.session_state.delete_confirm_sess}'?")
        c1, c2 = st.columns(2)
        if c1.button("Yes, Delete", use_container_width=True):
            delete_session(st.session_state.delete_confirm_sess)
            st.session_state.current_session = None
            st.session_state.delete_confirm_sess = None
            st.rerun()
        if c2.button("Cancel", use_container_width=True):
            st.session_state.delete_confirm_sess = None
            st.rerun()


def _render_follow_up_builder():
    st.markdown(f"### {icon(':link:', '🧵')} Follow-up Builder")
    if not st.session_state.current_session:
        st.info("Create a session first.")
        return

    suggested_name = f"{st.session_state.current_session}_fu_{st.session_state.campaign_stage + 1}"
    next_session_name = st.text_input(
        "Next Follow-up Session Name",
        value=suggested_name,
        key="next_followup_session_name",
    )

    if st.button("Create Follow-up Session", use_container_width=True):
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", next_session_name)
        state_snapshot = {
            "template": {
                "subject": st.session_state.input_subject,
                "body": st.session_state.input_body,
                "is_html": st.session_state.input_is_html,
                "attachment_path": st.session_state.attachment_path,
                "attachment_name": st.session_state.attachment_name,
            },
            "mapping": st.session_state.mapping,
            "data": st.session_state.df_processed,
            "tracking_state": st.session_state.tracking_state,
        }
        ok, message = create_follow_up_session(
            st.session_state.current_session,
            clean_name,
            state_snapshot,
        )
        if ok:
            trigger_save()
            st.toast(message)
        else:
            st.error(message)


def _render_template_library():
    st.markdown(f"### {icon(':memo:', '📝')} Template Library")
    template_name = st.text_input("Save Current Template As", placeholder="e.g. warm_followup")
    if st.button("Save to Library", use_container_width=True):
        if template_name:
            save_template_file(
                template_name,
                st.session_state.input_subject,
                st.session_state.input_body,
                st.session_state.input_is_html,
                st.session_state.attachment_path,
                st.session_state.attachment_name,
            )
            st.toast(f"Saved: {template_name}")

    templates = list_templates()
    selected_template = st.selectbox("Stored Templates", ["-- Select --"] + templates)

    load_col, delete_col = st.columns(2)
    with load_col:
        if st.button("Load Template", use_container_width=True):
            if selected_template != "-- Select --":
                template = load_template_file(selected_template)
                if template:
                    st.session_state.input_subject = template.get("subject", "")
                    st.session_state.input_body = template.get("body", "")
                    st.session_state.input_is_html = template.get("is_html", False)
                    st.session_state.attachment_path = template.get("attachment_path")
                    st.session_state.attachment_name = template.get("attachment_name")
                    trigger_save()
                    st.rerun()
    with delete_col:
        if st.button("Delete Template", use_container_width=True):
            if selected_template != "-- Select --":
                st.session_state.delete_confirm_tpl = selected_template

    if st.session_state.get("delete_confirm_tpl"):
        st.warning(f"Delete template '{st.session_state.delete_confirm_tpl}'?")
        c1, c2 = st.columns(2)
        if c1.button("Yes", key="confirm_delete_template", use_container_width=True):
            delete_template_file(st.session_state.delete_confirm_tpl)
            st.session_state.delete_confirm_tpl = None
            st.rerun()
        if c2.button("No", key="cancel_delete_template", use_container_width=True):
            st.session_state.delete_confirm_tpl = None
            st.rerun()


def _render_settings():
    st.markdown(f"### {icon(':satellite_antenna:', '📡')} Sending Rules")
    min_d = st.number_input("Min Delay (seconds)", min_value=1, value=20, step=1)
    max_d = st.number_input("Max Delay (seconds)", min_value=min_d, value=50, step=1)
    batch_sz = st.number_input("Batch Size", min_value=1, value=20, step=1)
    batch_dl = st.number_input("Batch Pause (seconds)", min_value=100, value=300, step=10)
    daily_limit = st.number_input(
        "Max Emails Per Day",
        min_value=10,
        value=200,
        step=10,
        help="Stops sending after reaching this limit for the current day.",
    )
    return min_d, max_d, batch_sz, batch_dl, daily_limit


def render_sidebar():
    with st.sidebar:
        st.markdown(f"## {icon(':sparkles:', '✨')} Workspace Controls")
        st.caption("Manage sessions, templates, follow-up batches, and sending rules from here.")
        st.write("")
        _render_session_manager()
        st.divider()
        _render_follow_up_builder()
        st.divider()
        _render_template_library()
        st.divider()
        settings = _render_settings()
        return settings
