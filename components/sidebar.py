import re

import streamlit as st

from components.state import trigger_save
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


def render_sidebar():
    with st.sidebar:
        st.header("Session Manager")

        with st.expander("Create / Switch Session", expanded=True):
            new_sess = st.text_input("New Session Name", placeholder="e.g. Batch_2")
            if st.button("Create Session"):
                if new_sess:
                    clean = re.sub(r"[^a-zA-Z0-9_]", "_", new_sess)
                    st.session_state.current_session = clean
                    st.session_state.df_processed = None
                    st.session_state.sent_ids = set()
                    st.session_state.sent_history = []
                    st.session_state.tracking_state = {}
                    st.session_state.mapping = {}
                    st.session_state.attachment_path = None
                    st.session_state.attachment_name = ""
                    st.session_state.campaign_stage = 0
                    st.session_state.parent_session = None
                    trigger_save()
                    st.rerun()

            sessions = list_sessions()
            idx = 0
            if st.session_state.current_session in sessions:
                idx = sessions.index(st.session_state.current_session)

            col_sel, col_del = st.columns([5, 1])
            with col_sel:
                sel_sess = st.selectbox(
                    "Active Session",
                    ["-- Select --"] + sessions,
                    index=idx + 1 if st.session_state.current_session else 0,
                    label_visibility="collapsed",
                )

            if st.session_state.current_session:
                with col_del:
                    if st.button("Delete", help="Delete Session"):
                        st.session_state.delete_confirm_sess = st.session_state.current_session

            if st.session_state.get("delete_confirm_sess"):
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

            if sel_sess != "-- Select --" and sel_sess != st.session_state.current_session:
                state = load_session(sel_sess)
                if state:
                    st.session_state.current_session = sel_sess
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
                    st.rerun()

        if not st.session_state.current_session:
            st.warning("Please create or select a session.")
            st.stop()

        st.success(f"Active: {st.session_state.current_session}")
        if st.session_state.campaign_stage > 0:
            origin = st.session_state.parent_session or "base session"
            st.caption(f"Follow-up round {st.session_state.campaign_stage} from {origin}")
        st.divider()

        st.header("Follow-up Flow")
        with st.expander("Create Next Follow-up Session"):
            suggested_name = (
                f"{st.session_state.current_session}_fu_{st.session_state.campaign_stage + 1}"
            )
            next_session_name = st.text_input(
                "New Follow-up Session Name",
                value=suggested_name,
                key="next_followup_session_name",
            )
            if st.button("Create Follow-up Session", type="secondary"):
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
                ok, msg = create_follow_up_session(
                    st.session_state.current_session,
                    clean_name,
                    state_snapshot,
                )
                if ok:
                    trigger_save()
                    st.toast(msg)
                else:
                    st.error(msg)

        st.divider()

        st.header("Template Library")
        with st.expander("Save / Load Templates"):
            tpl_name = st.text_input("Save Current as...", placeholder="e.g. Followup")
            if st.button("Save to Library"):
                if tpl_name:
                    save_template_file(
                        tpl_name,
                        st.session_state.input_subject,
                        st.session_state.input_body,
                        st.session_state.input_is_html,
                        st.session_state.attachment_path,
                        st.session_state.attachment_name,
                    )
                    st.toast(f"Saved: {tpl_name}")

            st.markdown("---")

            templates = list_templates()
            t_col_sel, t_col_del = st.columns([5, 1])
            with t_col_sel:
                sel_tpl = st.selectbox("Load Template", ["-- Select --"] + templates)

            with t_col_del:
                if sel_tpl != "-- Select --":
                    if st.button("Delete", key="del_tpl_btn", help="Delete Template"):
                        st.session_state.delete_confirm_tpl = sel_tpl

            if st.session_state.get("delete_confirm_tpl"):
                st.warning(f"Delete template '{st.session_state.delete_confirm_tpl}'?")
                tc1, tc2 = st.columns(2)
                if tc1.button("Yes", key="conf_del_tpl"):
                    delete_template_file(st.session_state.delete_confirm_tpl)
                    st.session_state.delete_confirm_tpl = None
                    st.rerun()
                if tc2.button("No", key="canc_del_tpl"):
                    st.session_state.delete_confirm_tpl = None
                    st.rerun()

            if st.button("Load Template"):
                if sel_tpl != "-- Select --":
                    tpl = load_template_file(sel_tpl)
                    if tpl:
                        st.session_state.input_subject = tpl.get("subject", "")
                        st.session_state.input_body = tpl.get("body", "")
                        st.session_state.input_is_html = tpl.get("is_html", False)
                        st.session_state.attachment_path = tpl.get("attachment_path")
                        st.session_state.attachment_name = tpl.get("attachment_name")
                        trigger_save()
                        st.rerun()

        st.divider()

        st.subheader("Settings")
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
