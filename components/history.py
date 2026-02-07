import streamlit as st
import pandas as pd

def render_history():
    st.header("4. History & Analytics")
    
    if not st.session_state.sent_history:
        st.info("No history available for this session yet.")
        return

    # Convert list of dicts to DataFrame
    df_hist = pd.DataFrame(st.session_state.sent_history)
    
    if df_hist.empty:
        st.info("No emails sent yet.")
        return

    # Process Timestamp
    try:
        df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'])
        df_hist['Date'] = df_hist['timestamp'].dt.date
        df_hist['Time'] = df_hist['timestamp'].dt.strftime('%H:%M:%S')
    except Exception:
        pass
        
    # Stats
    total_sent = len(df_hist[df_hist['status'] == 'success'])
    total_fail = len(df_hist) - total_sent
    
    c1, c2 = st.columns(2)
    c1.metric("Total Success", total_sent)
    c2.metric("Total Failed", total_fail)
    
    st.subheader("📋 Detailed Log")
    
    # Sort by time desc
    df_hist = df_hist.sort_values(by='timestamp', ascending=False)
    
    # Simple table view
    st.dataframe(
        df_hist[['Date', 'Time', 'email', 'status']], 
        width='stretch',
        hide_index=True
    )