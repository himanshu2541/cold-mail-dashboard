import streamlit as st

from components.ui.icons import icon


def _count_tracking_status(status_name):
    tracking_state = st.session_state.get("tracking_state", {})
    return sum(1 for item in tracking_state.values() if item.get("manual_status") == status_name)


def render_app_header():
    st.caption(f"{icon(':rocket:', '🚀')} Outreach workspace")
    st.title(f"{icon(':outbox_tray:', '📤')} Cold Mail Dashboard")
    st.write(
        "Compose campaigns, send in controlled batches, track delivery outcomes, "
        "and build follow-up rounds from manual decisions."
    )


def render_session_overview():
    current_session = st.session_state.get("current_session")
    df = st.session_state.get("df_processed")
    tracking_state = st.session_state.get("tracking_state", {})

    total_recipients = len(df) if df is not None else 0
    attempted = len(st.session_state.get("sent_ids", set()))
    selected_follow_up = sum(
        1 for item in tracking_state.values() if item.get("selected_for_follow_up")
    )
    replied = _count_tracking_status("replied")
    blocked = (
        _count_tracking_status("unreachable")
        + _count_tracking_status("do_not_follow_up")
        + _count_tracking_status("not_interested")
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Session", current_session or "None")
    c2.metric("Recipients", total_recipients)
    c3.metric("Attempted", attempted)
    c4.metric("Replied", replied)
    c5.metric("Queued Follow-up", selected_follow_up)

    if blocked:
        st.caption(f"{blocked} recipients are currently excluded from future follow-ups.")


def render_empty_workspace():
    st.info(
        "Create a new session from the left sidebar to begin composing, importing recipients, "
        "and preparing the next outreach batch."
    )
