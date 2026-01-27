import streamlit as st
import streamlit.components.v1 as components
import time
import random
import re
import os
from utils.sender import EmailSender
from components.state import trigger_save

def render_launcher(min_d, max_d, batch_sz, batch_dl):
    st.header("3. Preview & Launch")
    
    tab_preview, tab_launch = st.tabs(["👁️ Preview", "🚀 Launch"])
    
    # --- PREVIEW TAB ---
    with tab_preview:
        if st.session_state.df_processed is not None and len(st.session_state.df_processed) > 0:
            if 'p_idx' not in st.session_state: st.session_state.p_idx = 0
            
            c1, c2, _ = st.columns([1,1,4])
            if c1.button("⬅️"): st.session_state.p_idx = max(0, st.session_state.p_idx - 1)
            if c2.button("➡️"): st.session_state.p_idx = min(len(st.session_state.df_processed)-1, st.session_state.p_idx + 1)
            
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
            target_col = st.selectbox("Confirm Target Email Column", cols, index=next((i for i, c in enumerate(cols) if 'email' in c.lower()), 0))
            
            if st.button("🚀 Start Campaign", type="primary"):
                if not os.getenv("SENDER_EMAIL"):
                    st.error("No credentials in .env")
                    st.stop()
                
                sender = EmailSender()
                status = st.empty()
                bar = st.progress(0)
                log = st.container()
                
                # File Handle
                att_obj = None
                if st.session_state.attachment_path and os.path.exists(st.session_state.attachment_path):
                    att_obj = open(st.session_state.attachment_path, 'rb')
                
                df = st.session_state.df_processed
                sent_ct = 0
                
                for i, row in df.iterrows():
                    if row['_id'] in st.session_state.sent_ids: continue
                    
                    if sent_ct > 0 and sent_ct % batch_sz == 0:
                        status.warning(f"Batch pause... {batch_dl}s")
                        time.sleep(batch_dl)
                    
                    try:
                        subject = st.session_state.input_subject
                        body = st.session_state.input_body
                        is_html = st.session_state.input_is_html
                        
                        vars_in = set(re.findall(r'\{([^}]+)\}', subject + body))
                        ctx = {v: str(row[st.session_state.mapping.get(v, v)]) for v in vars_in}
                        
                        if att_obj: att_obj.seek(0)
                        
                        ok, msg = sender.send_email(
                            row[target_col],
                            subject.format(**ctx),
                            body.format(**ctx),
                            attachment_file=att_obj,
                            attachment_name=st.session_state.attachment_name,
                            is_html=is_html
                        )
                        
                        if ok:
                            st.session_state.sent_ids.add(row['_id'])
                            sent_ct += 1
                            trigger_save()
                            with log: st.toast(f"Sent: {row[target_col]}")
                        else:
                            with log: st.error(f"Failed: {row[target_col]} - {msg}")
                        
                        time.sleep(random.randint(min_d, max_d))
                        bar.progress((i+1)/len(df))
                        
                    except Exception as e:
                        st.error(f"Row Error: {e}")
                
                if att_obj: att_obj.close()
                st.success("Campaign Complete!")