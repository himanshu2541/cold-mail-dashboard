import streamlit as st
import streamlit.components.v1 as components
import time
import random
import re
import os
from datetime import datetime
from utils.sender import EmailSender
from components.state import trigger_save

def render_launcher(min_d, max_d, batch_sz, batch_dl, daily_limit):
    st.header("3. Preview & Launch")
    
    # --- INIT CONSOLE LOGS ---
    if 'console_logs' not in st.session_state:
        st.session_state.console_logs = []

    # Placeholder for the console to allow real-time updates
    # We define it here but populate it later in the layout
    console_placeholder = st.empty()

    def render_console():
        """Helper to render the logs immediately to the screen."""
        if not st.session_state.console_logs:
            # Empty state
            with console_placeholder.container(height=300, border=True):
                st.markdown("<i style='color:gray'>Ready to launch...</i>", unsafe_allow_html=True)
        else:
            # Render logs
            log_html = ""
            for log_entry in st.session_state.console_logs:
                log_html += f"<div style='margin-bottom:2px;'>{log_entry}</div>"
            
            with console_placeholder.container(height=300, border=True):
                st.markdown(log_html, unsafe_allow_html=True)

    def add_log(message, level="info"):
        """Adds a timestamped message and updates the UI immediately."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Better Colors (Hex codes for consistency)
        color = "#444" # Default Gray/Black
        icon = "🔹"
        
        if level == "success": 
            color = "#0f9d58" # Google Green
            icon = "✅"
        elif level == "error": 
            color = "#d93025" # Google Red
            icon = "❌"
        elif level == "warning": 
            color = "#f4b400" # Google Yellow/Orange
            icon = "⚠️"
        elif level == "system": 
            color = "#4285f4" # Google Blue
            icon = "🛠️"
        
        # Format: [Time] Icon Message
        entry = f"<span style='color:#888; font-size:0.9em;'>[{timestamp}]</span> <span style='color:{color}; font-weight:600;'>{icon} {message}</span>"
        
        st.session_state.console_logs.insert(0, entry)
        if len(st.session_state.console_logs) > 100:
            st.session_state.console_logs.pop()
            
        render_console()

    tab_preview, tab_launch = st.tabs(["👁️ Preview", "🚀 Launch"])
    
    # --- PREVIEW TAB ---
    with tab_preview:
        if st.session_state.df_processed is not None and len(st.session_state.df_processed) > 0:
            if 'p_idx' not in st.session_state: st.session_state.p_idx = 0
            
            max_preview = min(len(st.session_state.df_processed)-1, 9)

            c1, c2, _ = st.columns([1,1,4])
            if c1.button("⬅️"): st.session_state.p_idx = max(0, st.session_state.p_idx - 1)
            if c2.button("➡️"): st.session_state.p_idx = min(max_preview, st.session_state.p_idx + 1)
            
            st.caption(f"Previewing {st.session_state.p_idx + 1} of {max_preview + 1} (Limited to first 10)")

            row = st.session_state.df_processed.iloc[st.session_state.p_idx]
            subject = st.session_state.input_subject
            body = st.session_state.input_body
            is_html = st.session_state.input_is_html
            
            try:
                vars_in = set(re.findall(r'\{([^}]+)\}', subject + body))
                ctx = {v: str(row[st.session_state.mapping.get(v, v)]) for v in vars_in}
                
                p_sub = subject.format(**ctx)
                p_bod = body.format(**ctx)
                
                st.markdown(f"**To:** {row.get('Email', 'Unknown')}")
                st.markdown(f"**Subject:** {p_sub}")
                if st.session_state.attachment_path:
                    st.markdown(f"**📎 Attachment:** {st.session_state.attachment_name}")
                st.divider()
                
                if is_html:
                    html_wrap = f"<div style='background:white; color:black; padding:15px; border:1px solid #ddd'>{p_bod}</div>"
                    components.html(html_wrap, height=400, scrolling=True)
                else:
                    st.text(p_bod)
            except Exception as e:
                st.error(f"Preview Error: {e}")
        else:
            st.info("Upload data to see preview.")

    # --- LAUNCH TAB ---
    with tab_launch:
        if st.session_state.df_processed is not None:
            cols = st.session_state.df_processed.columns.tolist()
            em_idx = next((i for i, c in enumerate(cols) if 'email' in c.lower()), 0)
            target_col = st.selectbox("Confirm Target Email Column", cols, index=em_idx)
            
            st.divider()

            today_str = datetime.now().strftime("%Y-%m-%d")
            sent_today = sum(1 for x in st.session_state.sent_history if x.get('timestamp', '').startswith(today_str))

            # --- METRICS ---
            total_emails = len(st.session_state.df_processed)
            sent_count = len(st.session_state.sent_ids)
            remaining = total_emails - sent_count
            
            current_batch_num = (sent_count // batch_sz) + 1
            total_batches = (total_emails + batch_sz - 1) // batch_sz
            emails_in_current_batch = sent_count % batch_sz
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Progress", f"{sent_count} / {total_emails}")
            m2.metric("Remaining", remaining)
            m3.metric("Batch Status", f"{current_batch_num} / {total_batches}")
            m4.metric("In Batch", f"{emails_in_current_batch} / {batch_sz}")

            # --- CONTROLS ---
            # We wrap controls in a container to update them if campaign finishes
            control_container = st.container()
            
            # --- CONSOLE WINDOW ---
            st.write("###### 📟 Live Log")
            # We re-assign the global placeholder to this location in the layout
            console_placeholder = st.empty()
            # Initial Render
            render_console()

            # --- LOGIC TO SHOW/HIDE BUTTONS ---
            with control_container:
                if total_emails > 0 and remaining == 0:
                    st.success("🎉 Campaign Complete! All emails have been sent.")
                    if st.button("🧹 Clear Console Logs"):
                        st.session_state.console_logs = []
                        st.rerun()
                else:
                    c_start, c_stop, c_clear, _ = st.columns([1, 1, 1, 3])
                    
                    with c_start:
                        if st.button("🚀 Start Campaign", type="primary", disabled=st.session_state.is_running):
                            if not os.getenv("SENDER_EMAIL"):
                                st.error("Missing .env credentials")
                                st.stop()
                            st.session_state.is_running = True
                            add_log("--- Campaign Started ---", "system")
                            st.rerun()

                    with c_stop:
                        if st.button("🛑 Stop Gracefully", disabled=not st.session_state.is_running):
                            st.session_state.is_running = False
                            add_log("Stop signal received. Finishing current task...", "warning")
                    
                    with c_clear:
                        if st.button("🧹 Clear Logs"):
                            st.session_state.console_logs = []
                            st.rerun()

            # --- RUNNING LOOP ---
            if st.session_state.is_running:
                
                unsent_rows = [r for _, r in st.session_state.df_processed.iterrows() if r['_id'] not in st.session_state.sent_ids]
                
                current_sent_today = sum(1 for x in st.session_state.sent_history if x.get('timestamp', '').startswith(today_str))
                if current_sent_today >= daily_limit:
                    st.session_state.is_running = False
                    add_log(f"Daily limit ({daily_limit}) reached!", "warning")
                    st.rerun()
                
                if not unsent_rows:
                    st.session_state.is_running = False
                    add_log("Campaign Completed Successfully!", "success")
                    st.balloons()
                    # Do NOT rerun here, just let the UI update naturally on next interaction
                    # or force a UI update of the buttons section only if possible (hard in streamlit)
                    # We will rerun one last time to update the buttons to "Complete" state
                    st.rerun()

                current_row = unsent_rows[0]
                uid = current_row['_id']
                email_addr = current_row[target_col]

                # Check Batch Pause
                if sent_count > 0 and sent_count % batch_sz == 0:
                    add_log(f"Batch {current_batch_num-1} complete. Pausing for {batch_dl}s...", "warning")
                    
                    # Live Countdown in Console
                    time_placeholder = st.empty()
                    for i in range(batch_dl, 0, -1):
                        time_placeholder.caption(f"⏳ Resuming in {i} seconds...")
                        time.sleep(1)
                    time_placeholder.empty()
                    add_log(f"Resuming Batch {current_batch_num}...", "system")

                sender = EmailSender()
                att_obj = None
                if st.session_state.attachment_path and os.path.exists(st.session_state.attachment_path):
                    att_obj = open(st.session_state.attachment_path, 'rb')

                try:
                    delay = random.randint(min_d, max_d)
                    
                    # 1. Update Log BEFORE sending
                    add_log(f"Sending to: {email_addr}...", "info")
                    
                    subject = st.session_state.input_subject
                    body = st.session_state.input_body
                    is_html = st.session_state.input_is_html
                    vars_in = set(re.findall(r'\{([^}]+)\}', subject + body))
                    ctx = {v: str(current_row[st.session_state.mapping.get(v, v)]) for v in vars_in}

                    if att_obj: att_obj.seek(0)

                    # 2. Send
                    ok, msg = sender.send_email(
                        email_addr,
                        subject.format(**ctx),
                        body.format(**ctx),
                        attachment_file=att_obj,
                        attachment_name=st.session_state.attachment_name,
                        is_html=is_html
                    )

                    # 3. Update Log AFTER sending
                    if ok:
                        st.session_state.sent_ids.add(uid)
                        st.session_state.sent_history.append({
                            "id": uid,
                            "email": email_addr,
                            "timestamp": datetime.now().isoformat(),
                            "status": "success"
                        })
                        trigger_save()
                        add_log(f"Sent: {email_addr}", "success")
                    else:
                        st.session_state.sent_ids.add(uid)
                        st.session_state.sent_history.append({
                            "id": uid,
                            "email": email_addr,
                            "timestamp": datetime.now().isoformat(),
                            "status": f"failed: {msg}"
                        })
                        add_log(f"Failed: {email_addr} - {msg}", "error")

                    if att_obj: att_obj.close()
                    
                    # 4. Wait (Countdown)
                    if len(unsent_rows) > 1:
                        time_placeholder = st.empty()
                        for i in range(delay, 0, -1):
                            time_placeholder.markdown(f"**⏱️ Next email in {i}s...**")
                            time.sleep(1)
                        time_placeholder.empty()

                    # 5. Rerun
                    st.rerun()

                except Exception as e:
                    add_log(f"Critical Error: {e}", "error")
                    st.session_state.is_running = False
                    if att_obj: att_obj.close()
                    st.rerun()