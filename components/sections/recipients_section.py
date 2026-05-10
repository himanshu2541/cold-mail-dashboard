import pandas as pd
import streamlit as st

from components.state import trigger_save
from components.ui.icons import icon
from utils.processor import process_data
from utils.session import build_tracking_state


def _render_header():
    st.subheader(f"{icon(':file_folder:', '🗂️')} Recipient Data")
    st.caption("Import your sheet, choose the email column, and review the processed recipient list before sending.")


def _render_loaded_dataset():
    df = st.session_state.df_processed
    total_recipients = len(df)
    total_columns = len(df.columns) - (1 if "_id" in df.columns else 0)

    c1, c2 = st.columns(2)
    c1.metric("Recipients Ready", total_recipients)
    c2.metric("Available Fields", total_columns)

    with st.expander("Preview Processed Data", expanded=True):
        st.dataframe(df.head(300), width="stretch", hide_index=True)

    if st.button("Clear Data (Keep Template)"):
        st.session_state.df_processed = None
        st.session_state.sent_ids = set()
        st.session_state.sent_history = []
        st.session_state.tracking_state = {}
        trigger_save()
        st.rerun()


def render_data_view():
    _render_header()
    st.write("")

    if st.session_state.df_processed is not None:
        _render_loaded_dataset()
        return

    uploaded_file = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])
    if not uploaded_file:
        st.info("Add a file to begin building the recipient list.")
        return

    if uploaded_file.name.endswith(".csv"):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)

    cols = df_raw.columns.tolist()
    default_email_idx = next((i for i, c in enumerate(cols) if "email" in c.lower()), 0)
    email_col = st.selectbox("Recipient Email Column", cols, index=default_email_idx)

    preview_col, action_col = st.columns([4, 1])
    with preview_col:
        st.dataframe(df_raw.head(20), width="stretch", hide_index=True)
    with action_col:
        st.caption(f"{icon(':sparkles:', '✨')} {len(df_raw)} raw rows detected")
        if st.button("Process Data", type="primary", use_container_width=True):
            st.session_state.df_processed = process_data(df_raw, email_col)
            st.session_state.tracking_state = build_tracking_state(
                st.session_state.df_processed,
                st.session_state.get("sent_history", []),
                st.session_state.get("tracking_state", {}),
            )
            trigger_save()
            st.rerun()
