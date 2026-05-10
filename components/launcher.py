import os
import random
import re
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from components.state import trigger_save
from utils.sender import EmailSender
from utils.session import update_tracking_entry


def render_launcher(min_d, max_d, batch_sz, batch_dl, daily_limit):
    st.header("3. Preview & Launch")

    if "console_logs" not in st.session_state:
        st.session_state.console_logs = []

    console_placeholder = st.empty()

    def render_console():
        if not st.session_state.console_logs:
            with console_placeholder.container(height=300, border=True):
                st.markdown("<i style='color:gray'>Ready to launch...</i>", unsafe_allow_html=True)
        else:
            log_html = "".join(
                f"<div style='margin-bottom:2px;'>{entry}</div>"
                for entry in st.session_state.console_logs
            )
            with console_placeholder.container(height=300, border=True):
                st.markdown(log_html, unsafe_allow_html=True)

    def add_log(message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = "#444"
        icon = "•"

        if level == "success":
            color = "#0f9d58"
            icon = "OK"
        elif level == "error":
            color = "#d93025"
            icon = "ERR"
        elif level == "warning":
            color = "#f4b400"
            icon = "WARN"
        elif level == "system":
            color = "#4285f4"
            icon = "SYS"

        entry = (
            f"<span style='color:#888; font-size:0.9em;'>[{timestamp}]</span> "
            f"<span style='color:{color}; font-weight:600;'>{icon} {message}</span>"
        )
        st.session_state.console_logs.insert(0, entry)
        if len(st.session_state.console_logs) > 100:
            st.session_state.console_logs.pop()
        render_console()

    def get_email_column(columns):
        return next((col for col in columns if "email" in col.lower()), columns[0])

    def get_tracking_entry(row_id, email_addr):
        entry = st.session_state.tracking_state.get(row_id, {})
        if not entry:
            entry = {
                "id": row_id,
                "email": email_addr,
                "delivery_status": "pending",
                "manual_status": "active",
                "follow_up_stage": st.session_state.get("campaign_stage", 0),
                "selected_for_follow_up": False,
                "thread_root_message_id": None,
                "last_message_id": None,
                "references": None,
                "last_sent_at": None,
                "last_error": "",
            }
            st.session_state.tracking_state[row_id] = entry
        return entry

    tab_preview, tab_launch = st.tabs(["Preview", "Launch"])

    with tab_preview:
        if st.session_state.df_processed is not None and len(st.session_state.df_processed) > 0:
            if "p_idx" not in st.session_state:
                st.session_state.p_idx = 0

            max_preview = min(len(st.session_state.df_processed) - 1, 9)
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("Previous"):
                st.session_state.p_idx = max(0, st.session_state.p_idx - 1)
            if c2.button("Next"):
                st.session_state.p_idx = min(max_preview, st.session_state.p_idx + 1)

            st.caption(f"Previewing {st.session_state.p_idx + 1} of {max_preview + 1} (limited to first 10)")

            row = st.session_state.df_processed.iloc[st.session_state.p_idx]
            subject = st.session_state.input_subject
            body = st.session_state.input_body
            is_html = st.session_state.input_is_html

            try:
                vars_in = set(re.findall(r"\{([^}]+)\}", subject + body))
                ctx = {v: str(row[st.session_state.mapping.get(v, v)]) for v in vars_in}
                p_sub = subject.format(**ctx)
                p_bod = body.format(**ctx)

                st.markdown(f"**To:** {row.get('Email', 'Unknown')}")
                st.markdown(f"**Subject:** {p_sub}")
                if st.session_state.attachment_path:
                    st.markdown(f"**Attachment:** {st.session_state.attachment_name}")
                st.divider()

                if is_html:
                    html_wrap = (
                        "<div style='background:white; color:black; padding:15px; border:1px solid #ddd'>"
                        f"{p_bod}</div>"
                    )
                    components.html(html_wrap, height=400, scrolling=True)
                else:
                    st.text(p_bod)
            except Exception as exc:
                st.error(f"Preview Error: {exc}")
        else:
            st.info("Upload data to see preview.")

    with tab_launch:
        if st.session_state.df_processed is None:
            return

        cols = st.session_state.df_processed.columns.tolist()
        target_col = st.selectbox(
            "Confirm Target Email Column",
            cols,
            index=cols.index(get_email_column(cols)),
        )

        st.divider()

        today_str = datetime.now().strftime("%Y-%m-%d")
        sent_today = sum(1 for x in st.session_state.sent_history if x.get("timestamp", "").startswith(today_str))

        total_emails = len(st.session_state.df_processed)
        sent_count = len(st.session_state.sent_ids)
        remaining = total_emails - sent_count
        current_batch_num = (sent_count // batch_sz) + 1
        total_batches = (total_emails + batch_sz - 1) // batch_sz
        emails_in_current_batch = sent_count % batch_sz

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Progress", f"{sent_count} / {total_emails}")
        m2.metric("Remaining", remaining)
        m3.metric("Batch Status", f"{current_batch_num} / {total_batches}")
        m4.metric("In Batch", f"{emails_in_current_batch} / {batch_sz}")
        m5.metric("Sent Today", f"{sent_today} / {daily_limit}")

        control_container = st.container()
        st.write("###### Live Log")
        console_placeholder = st.empty()
        render_console()

        with control_container:
            if total_emails > 0 and remaining == 0:
                st.success("Campaign complete. All emails in this session have been attempted.")
                if st.button("Clear Console Logs"):
                    st.session_state.console_logs = []
                    st.rerun()
            else:
                c_start, c_stop, c_clear, _ = st.columns([1, 1, 1, 3])
                with c_start:
                    if st.button("Start Campaign", type="primary", disabled=st.session_state.is_running):
                        if not os.getenv("SENDER_EMAIL"):
                            st.error("Missing .env credentials")
                            st.stop()
                        st.session_state.is_running = True
                        add_log("Campaign started.", "system")
                        st.rerun()

                with c_stop:
                    if st.button("Stop Gracefully", disabled=not st.session_state.is_running):
                        st.session_state.is_running = False
                        add_log("Stop signal received. Finishing current send...", "warning")

                with c_clear:
                    if st.button("Clear Logs"):
                        st.session_state.console_logs = []
                        st.rerun()

        if not st.session_state.is_running:
            return

        unsent_rows = [
            row
            for _, row in st.session_state.df_processed.iterrows()
            if row["_id"] not in st.session_state.sent_ids
        ]

        current_sent_today = sum(
            1 for x in st.session_state.sent_history if x.get("timestamp", "").startswith(today_str)
        )
        if current_sent_today >= daily_limit:
            st.session_state.is_running = False
            add_log(f"Daily limit ({daily_limit}) reached.", "warning")
            st.rerun()

        if not unsent_rows:
            st.session_state.is_running = False
            add_log("Campaign completed successfully.", "success")
            st.balloons()
            st.rerun()

        current_row = unsent_rows[0]
        uid = current_row["_id"]
        email_addr = current_row[target_col]
        tracking = get_tracking_entry(uid, email_addr)

        if sent_count > 0 and sent_count % batch_sz == 0:
            add_log(f"Batch {current_batch_num - 1} complete. Pausing for {batch_dl}s...", "warning")
            time_placeholder = st.empty()
            for remaining_seconds in range(batch_dl, 0, -1):
                time_placeholder.caption(f"Resuming in {remaining_seconds} seconds...")
                time.sleep(1)
            time_placeholder.empty()
            add_log(f"Resuming batch {current_batch_num}.", "system")

        sender = EmailSender()
        att_obj = None
        if st.session_state.attachment_path and os.path.exists(st.session_state.attachment_path):
            att_obj = open(st.session_state.attachment_path, "rb")

        try:
            delay = random.randint(min_d, max_d)
            add_log(f"Sending to {email_addr}...", "info")

            subject = st.session_state.input_subject
            body = st.session_state.input_body
            is_html = st.session_state.input_is_html
            vars_in = set(re.findall(r"\{([^}]+)\}", subject + body))
            ctx = {v: str(current_row[st.session_state.mapping.get(v, v)]) for v in vars_in}

            if att_obj:
                att_obj.seek(0)

            ok, msg, message_id = sender.send_email(
                email_addr,
                subject.format(**ctx),
                body.format(**ctx),
                attachment_file=att_obj,
                attachment_name=st.session_state.attachment_name,
                is_html=is_html,
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
                "status": "success" if ok else f"failed: {msg}",
                "delivery_status": "success" if ok else "failed",
                "manual_status": "active" if ok else "failed",
                "follow_up_stage": tracking.get("follow_up_stage", st.session_state.get("campaign_stage", 0)),
                "selected_for_follow_up": False,
                "message_id": message_id,
                "thread_root_message_id": thread_root if ok else tracking.get("thread_root_message_id"),
                "last_message_id": message_id if ok else tracking.get("last_message_id"),
                "references": references if ok else tracking.get("references"),
                "last_error": "" if ok else msg,
            }

            st.session_state.sent_ids.add(uid)
            st.session_state.sent_history.append(history_item)
            update_tracking_entry(st.session_state.tracking_state, history_item)
            trigger_save()

            if ok:
                add_log(f"Sent to {email_addr} in tracked thread.", "success")
            else:
                add_log(f"Failed for {email_addr}: {msg}", "error")

            if att_obj:
                att_obj.close()

            if len(unsent_rows) > 1:
                time_placeholder = st.empty()
                for remaining_seconds in range(delay, 0, -1):
                    time_placeholder.markdown(f"**Next email in {remaining_seconds}s...**")
                    time.sleep(1)
                time_placeholder.empty()

            st.rerun()

        except Exception as exc:
            add_log(f"Critical Error: {exc}", "error")
            st.session_state.is_running = False
            if att_obj:
                att_obj.close()
            st.rerun()
