import pandas as pd
import streamlit as st

from components.state import trigger_save
from components.ui.icons import icon
from utils.session import set_tracking_manual_updates

MANUAL_STATUS_OPTIONS = [
    "active",
    "replied",
    "unreachable",
    "not_interested",
    "do_not_follow_up",
    "failed",
]


def _tracking_dataframe():
    rows = []
    for uid, item in st.session_state.get("tracking_state", {}).items():
        rows.append(
            {
                "id": uid,
                "email": item.get("email", ""),
                "delivery_status": item.get("delivery_status", "pending"),
                "manual_status": item.get("manual_status", "active"),
                "follow_up_stage": item.get("follow_up_stage", 0),
                "selected_for_follow_up": bool(item.get("selected_for_follow_up", False)),
                "last_sent_at": item.get("last_sent_at"),
                "last_error": item.get("last_error", ""),
            }
        )
    return pd.DataFrame(rows)


def _render_summary(df_tracking):
    last_sent = pd.to_datetime(df_tracking["last_sent_at"], errors="coerce")
    df_tracking["last_sent_display"] = last_sent.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("-")

    delivered = int((df_tracking["delivery_status"] == "success").sum())
    failed = int((df_tracking["delivery_status"] == "failed").sum())
    replied = int((df_tracking["manual_status"] == "replied").sum())
    follow_up = int(df_tracking["selected_for_follow_up"].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Delivered", delivered)
    c2.metric("Failed", failed)
    c3.metric("Replied", replied)
    c4.metric("Marked for Follow-up", follow_up)

    st.caption(
        "Update manual statuses here after you check your inbox. Only rows left as 'active' should be selected for future follow-up."
    )


def render_history():
    st.subheader(f"{icon(':bar_chart:', '📊')} Tracking and Manual Decisions")
    st.caption("Review delivery outcomes, mark replies or bad addresses, and decide exactly who should enter the next follow-up batch.")
    st.write("")

    df_tracking = _tracking_dataframe()
    if df_tracking.empty:
        st.info("No tracked recipients in this session yet.")
        return

    _render_summary(df_tracking)

    editor_df = df_tracking[
        [
            "id",
            "email",
            "delivery_status",
            "manual_status",
            "selected_for_follow_up",
            "follow_up_stage",
            "last_sent_display",
            "last_error",
        ]
    ].sort_values(by=["follow_up_stage", "email"], ascending=[True, True])

    edited = st.data_editor(
        editor_df,
        width="stretch",
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID", disabled=True),
            "email": st.column_config.TextColumn("Email", disabled=True),
            "delivery_status": st.column_config.TextColumn("Delivery", disabled=True),
            "manual_status": st.column_config.SelectboxColumn("Manual Status", options=MANUAL_STATUS_OPTIONS),
            "selected_for_follow_up": st.column_config.CheckboxColumn("Next Follow-up"),
            "follow_up_stage": st.column_config.NumberColumn("Round", disabled=True),
            "last_sent_display": st.column_config.TextColumn("Last Sent", disabled=True),
            "last_error": st.column_config.TextColumn("Last Error", disabled=True),
        },
        disabled=["id", "email", "delivery_status", "follow_up_stage", "last_sent_display", "last_error"],
        key="tracking_editor",
    )

    if st.button("Save Tracking Decisions", type="primary"):
        updates = edited[["id", "manual_status", "selected_for_follow_up"]].to_dict(orient="records")
        set_tracking_manual_updates(st.session_state.tracking_state, updates)
        trigger_save()
        st.toast("Tracking decisions saved.")
        st.rerun()

    if st.session_state.sent_history:
        st.subheader("Send Attempt History")
        df_hist = pd.DataFrame(st.session_state.sent_history).copy()
        df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"], errors="coerce")
        df_hist["timestamp"] = df_hist["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df_hist = df_hist.sort_values(by="timestamp", ascending=False)
        st.dataframe(
            df_hist[
                [
                    "timestamp",
                    "email",
                    "delivery_status",
                    "manual_status",
                    "follow_up_stage",
                    "status",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
