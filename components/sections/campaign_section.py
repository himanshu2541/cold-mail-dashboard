import os
import random
import re
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from components.state import trigger_save
from components.ui.icons import icon
from utils.sender import EmailSender
from utils.session import update_tracking_entry


def _ensure_console():
    if "console_logs" not in st.session_state:
        st.session_state.console_logs = []


def _get_email_column(columns):
    return next((col for col in columns if "email" in col.lower()), columns[0])


def _get_tracking_entry(row_id, email_addr):
    entry = st.session_state.tracking_state.get(row_id, {})
    if not entry:
        entry = {
            "id": row_id,
            "email": email_addr,
            "delivery_status": "pending",
            "manual_status": "active",
            "follow_up_stage": st.session_state.get("campaign_stage", 0),
            "selected_for_follow_up": True,
            "thread_root_message_id": None,
            "last_message_id": None,
            "references": None,
            "last_sent_at": None,
            "last_error": "",
        }
        st.session_state.tracking_state[row_id] = entry
    return entry


def _render_console(console_placeholder):
    if not st.session_state.console_logs:
        with console_placeholder.container(height=320, border=True):
            st.markdown("<i style='color:gray'>Ready to launch...</i>", unsafe_allow_html=True)
        return

    log_html = "".join(
        f"<div style='margin-bottom:4px;'>{entry}</div>" for entry in st.session_state.console_logs
    )
    with console_placeholder.container(height=320, border=True):
        st.markdown(log_html, unsafe_allow_html=True)


def _add_log(console_placeholder, message, level="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color_map = {
        "info": "#425466",
        "success": "#1e8e3e",
        "warning": "#d98324",
        "error": "#d93025",
        "system": "#0b6bcb",
    }
    icon_map = {
        "info": icon(":sparkles:", "✨"),
        "success": icon(":white_check_mark:", "✅"),
        "warning": icon(":warning:", "⚠️"),
        "error": icon(":x:", "❌"),
        "system": icon(":rocket:", "🚀"),
    }
    entry = (
        f"<span style='color:#718096; font-size:0.9em;'>[{timestamp}]</span> "
        f"<span style='color:{color_map[level]}; font-weight:600;'>{icon_map[level]} {message}</span>"
    )
    st.session_state.console_logs.insert(0, entry)
    if len(st.session_state.console_logs) > 100:
        st.session_state.console_logs.pop()
    _render_console(console_placeholder)


def _render_preview():
    if st.session_state.df_processed is None or len(st.session_state.df_processed) == 0:
        st.info("Upload recipient data to preview your email.")
        return

    if "p_idx" not in st.session_state:
        st.session_state.p_idx = 0

    max_preview = min(len(st.session_state.df_processed) - 1, 9)
    c1, c2, c3 = st.columns([1, 1, 4])
    if c1.button("Previous Preview"):
        st.session_state.p_idx = max(0, st.session_state.p_idx - 1)
    if c2.button("Next Preview"):
        st.session_state.p_idx = min(max_preview, st.session_state.p_idx + 1)
    with c3:
        st.caption(f"Showing preview {st.session_state.p_idx + 1} of {max_preview + 1}")

    row = st.session_state.df_processed.iloc[st.session_state.p_idx]
    subject = st.session_state.input_subject
    body = st.session_state.input_body
    is_html = st.session_state.input_is_html

    vars_in = set(re.findall(r"\{([^}]+)\}", subject + body))
    context = {var: str(row[st.session_state.mapping.get(var, var)]) for var in vars_in}
    preview_subject = subject.format(**context)
    preview_body = body.format(**context)
    preview_email = row.get(_get_email_column(st.session_state.df_processed.columns.tolist()), "Unknown")

    st.markdown(f"#### Preview for {preview_email}")
    st.caption("Use this to check merge fields before launching the batch.")
    st.markdown(f"**Subject:** {preview_subject}")
    if st.session_state.attachment_name:
        st.markdown(f"**Attachment:** {st.session_state.attachment_name}")

    if is_html:
        components.html(
            f"<div style='background:white; color:black; padding:15px; border:1px solid #ddd'>{preview_body}</div>",
            height=420,
            scrolling=True,
        )
    else:
        st.text(preview_body)


def _render_metrics(batch_sz, daily_limit):
    today_str = datetime.now().strftime("%Y-%m-%d")
    sent_today = sum(1 for item in st.session_state.sent_history if item.get("timestamp", "").startswith(today_str))
    total_emails = len(st.session_state.df_processed)
    sent_count = len(st.session_state.sent_ids)
    remaining = total_emails - sent_count
    current_batch_num = (sent_count // batch_sz) + 1
    total_batches = (total_emails + batch_sz - 1) // batch_sz
    emails_in_current_batch = sent_count % batch_sz

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Progress", f"{sent_count} / {total_emails}")
    m2.metric("Remaining", remaining)
    m3.metric("Batch", f"{current_batch_num} / {total_batches}")
    m4.metric("Current Batch", f"{emails_in_current_batch} / {batch_sz}")
    m5.metric("Today", f"{sent_today} / {daily_limit}")


def _send_next_email(console_placeholder, min_d, max_d, batch_sz, batch_dl, daily_limit, target_col):
    today_str = datetime.now().strftime("%Y-%m-%d")
    unsent_rows = [
        row for _, row in st.session_state.df_processed.iterrows() if row["_id"] not in st.session_state.sent_ids
    ]
    sent_count = len(st.session_state.sent_ids)
    current_batch_num = (sent_count // batch_sz) + 1

    current_sent_today = sum(
        1 for item in st.session_state.sent_history if item.get("timestamp", "").startswith(today_str)
    )
    if current_sent_today >= daily_limit:
        st.session_state.is_running = False
        _add_log(console_placeholder, f"Daily limit ({daily_limit}) reached.", "warning")
        st.rerun()

    if not unsent_rows:
        st.session_state.is_running = False
        _add_log(console_placeholder, "Campaign completed successfully.", "success")
        st.balloons()
        st.rerun()

    current_row = unsent_rows[0]
    uid = current_row["_id"]
    email_addr = current_row[target_col]
    tracking = _get_tracking_entry(uid, email_addr)

    if sent_count > 0 and sent_count % batch_sz == 0:
        _add_log(
            console_placeholder,
            f"Batch {current_batch_num - 1} complete. Pausing for {batch_dl}s...",
            "warning",
        )
        countdown = st.empty()
        for remaining_seconds in range(batch_dl, 0, -1):
            countdown.caption(f"Resuming in {remaining_seconds} seconds...")
            time.sleep(1)
        countdown.empty()
        _add_log(console_placeholder, f"Resuming batch {current_batch_num}.", "system")

    sender = EmailSender()
    attachment_handle = None
    if st.session_state.attachment_path and os.path.exists(st.session_state.attachment_path):
        attachment_handle = open(st.session_state.attachment_path, "rb")

    try:
        delay = random.randint(min_d, max_d)
        _add_log(console_placeholder, f"Sending to {email_addr}...", "info")

        subject = st.session_state.input_subject
        body = st.session_state.input_body
        vars_in = set(re.findall(r"\{([^}]+)\}", subject + body))
        context = {var: str(current_row[st.session_state.mapping.get(var, var)]) for var in vars_in}

        if attachment_handle:
            attachment_handle.seek(0)

        ok, message, message_id = sender.send_email(
            email_addr,
            subject.format(**context),
            body.format(**context),
            attachment_file=attachment_handle,
            attachment_name=st.session_state.attachment_name,
            is_html=st.session_state.input_is_html,
            thread_message_id=tracking.get("last_message_id"),
            references=tracking.get("references"),
        )

        timestamp = datetime.now().isoformat()
        thread_root = tracking.get("thread_root_message_id") or message_id
        references = tracking.get("references")
        if tracking.get("last_message_id"):
            previous_refs = references or thread_root or ""
            references = f"{previous_refs} {tracking['last_message_id']}".strip()
        else:
            references = message_id

        history_item = {
            "id": uid,
            "email": email_addr,
            "timestamp": timestamp,
            "status": "success" if ok else f"failed: {message}",
            "delivery_status": "success" if ok else "failed",
            "manual_status": "active" if ok else "failed",
            "follow_up_stage": tracking.get("follow_up_stage", st.session_state.get("campaign_stage", 0)),
            "selected_for_follow_up": True if ok else False,
            "message_id": message_id,
            "thread_root_message_id": thread_root if ok else tracking.get("thread_root_message_id"),
            "last_message_id": message_id if ok else tracking.get("last_message_id"),
            "references": references if ok else tracking.get("references"),
            "last_error": "" if ok else message,
        }

        st.session_state.sent_ids.add(uid)
        st.session_state.sent_history.append(history_item)
        update_tracking_entry(st.session_state.tracking_state, history_item)
        trigger_save()

        if ok:
            _add_log(console_placeholder, f"Sent to {email_addr} in tracked thread.", "success")
        else:
            _add_log(console_placeholder, f"Failed for {email_addr}: {message}", "error")

        if attachment_handle:
            attachment_handle.close()

        if len(unsent_rows) > 1:
            countdown = st.empty()
            for remaining_seconds in range(delay, 0, -1):
                countdown.markdown(f"**Next email in {remaining_seconds}s...**")
                time.sleep(1)
            countdown.empty()

        st.rerun()
    except Exception as exc:
        _add_log(console_placeholder, f"Critical error: {exc}", "error")
        st.session_state.is_running = False
        if attachment_handle:
            attachment_handle.close()
        st.rerun()


def render_launcher(min_d, max_d, batch_sz, batch_dl, daily_limit):
    _ensure_console()
    st.subheader(f"{icon(':satellite_antenna:', '📡')} Preview and Launch")
    st.caption("Preview merged emails, launch the campaign in batches, and monitor a live activity stream.")
    st.write("")

    preview_col, launch_col = st.columns([1.15, 1], gap="large")

    with preview_col:
        _render_preview()

    with launch_col:
        if st.session_state.df_processed is None:
            st.info("Upload recipient data before launching a campaign.")
            return

        cols = st.session_state.df_processed.columns.tolist()
        target_col = st.selectbox(
            "Target Email Column",
            cols,
            index=cols.index(_get_email_column(cols)),
        )
        _render_metrics(batch_sz, daily_limit)

        controls = st.columns([1, 1, 1])
        console_placeholder = st.empty()
        _render_console(console_placeholder)

        with controls[0]:
            if st.button("Start Campaign", type="primary", use_container_width=True, disabled=st.session_state.is_running):
                if not os.getenv("SENDER_EMAIL"):
                    st.error("Missing .env credentials")
                    st.stop()
                st.session_state.is_running = True
                _add_log(console_placeholder, "Campaign started.", "system")
                st.rerun()
        with controls[1]:
            if st.button("Stop Gracefully", use_container_width=True, disabled=not st.session_state.is_running):
                st.session_state.is_running = False
                _add_log(console_placeholder, "Stop signal received. Finishing current send...", "warning")
        with controls[2]:
            if st.button("Clear Logs", use_container_width=True):
                st.session_state.console_logs = []
                st.rerun()

        if not st.session_state.is_running:
            return

        _send_next_email(console_placeholder, min_d, max_d, batch_sz, batch_dl, daily_limit, target_col)
