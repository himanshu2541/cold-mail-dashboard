import os
import re
import uuid

import streamlit as st

from components.state import trigger_save
from components.ui.icons import icon
from utils.session import ATTACHMENTS_DIR


def _render_section_intro():
    st.subheader(f"{icon(':memo:', '📝')} Compose Campaign")
    st.caption("Write the email once, attach files, and map placeholders like {name} or {company}.")


def _save_uploaded_attachment(uploaded_file):
    if not os.path.exists(ATTACHMENTS_DIR):
        os.makedirs(ATTACHMENTS_DIR)

    unique_id = uuid.uuid4().hex[:8]
    safe_filename = f"{unique_id}_{uploaded_file.name}"
    save_path = os.path.join(ATTACHMENTS_DIR, safe_filename)

    with open(save_path, "wb") as handle:
        handle.write(uploaded_file.getbuffer())

    st.session_state.attachment_path = save_path
    st.session_state.attachment_name = uploaded_file.name
    st.session_state.uploader_key += 1
    trigger_save()
    st.rerun()


def _render_attachment_panel():
    st.markdown(f"#### {icon(':paperclip:', '📎')} Attachment")
    uploaded = st.file_uploader(
        "Upload File",
        label_visibility="collapsed",
        key=f"uploader_{st.session_state.uploader_key}",
    )
    if uploaded:
        _save_uploaded_attachment(uploaded)

    attachment_path = st.session_state.attachment_path
    if attachment_path and os.path.exists(attachment_path):
        st.success(f"Attached file: {st.session_state.attachment_name}")
        name_col, remove_col = st.columns([3, 1])
        with name_col:
            new_name = st.text_input(
                "Attachment Name Shown to Recipient",
                value=st.session_state.attachment_name,
            )
            if new_name != st.session_state.attachment_name:
                st.session_state.attachment_name = new_name
                trigger_save()
        with remove_col:
            st.write("")
            st.write("")
            if st.button("Remove Attachment"):
                st.session_state.attachment_path = None
                st.session_state.attachment_name = ""
                trigger_save()
                st.rerun()
    else:
        st.caption("No attachment added yet.")


def _render_variable_mapping():
    st.markdown(f"#### {icon(':triangular_ruler:', '📐')} Variable Mapping")

    if st.session_state.df_processed is None:
        st.info("Upload recipient data to start mapping placeholders.")
        return

    subject = st.session_state.input_subject
    body = st.session_state.input_body
    vars_needed = sorted(set(re.findall(r"\{([^}]+)\}", subject + body)))
    cols = [c for c in st.session_state.df_processed.columns if c != "_id"]

    if not vars_needed:
        st.caption("No placeholders detected in the email body yet.")
        return

    current_map = st.session_state.mapping
    new_map = {}
    for variable in vars_needed:
        if variable in current_map and current_map[variable] in cols:
            default_idx = cols.index(current_map[variable])
        else:
            default_idx = next(
                (i for i, col_name in enumerate(cols) if variable.lower() in col_name.lower()),
                0,
            )
        new_map[variable] = st.selectbox(
            f"Placeholder: {{{variable}}}",
            cols,
            index=default_idx,
            key=f"map_{variable}",
        )

    st.session_state.mapping = new_map


def render_editor():
    _render_section_intro()
    st.write("")

    compose_col, mapping_col = st.columns([2.2, 1], gap="large")

    with compose_col:
        st.text_input("Subject", key="input_subject", on_change=trigger_save)
        st.text_area(
            "Body",
            height=340,
            key="input_body",
            on_change=trigger_save,
            placeholder="Write your message here. Use placeholders like {name} or {company}.",
        )
        st.checkbox("Send as HTML", key="input_is_html", on_change=trigger_save)
        st.divider()
        _render_attachment_panel()

    with mapping_col:
        _render_variable_mapping()
