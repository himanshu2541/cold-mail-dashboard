import streamlit as st
import pandas as pd
from utils.processor import process_data
from components.state import trigger_save

def render_data_view():
    st.header("2. Data & Recipients")
    
    if st.session_state.df_processed is None:
        up_file = st.file_uploader("Upload Excel/CSV", type=['xlsx', 'csv'])
        if up_file:
            if up_file.name.endswith('.csv'): 
                df_raw = pd.read_csv(up_file)
            else: 
                df_raw = pd.read_excel(up_file)
            
            cols = df_raw.columns.tolist()
            em_idx = next((i for i, c in enumerate(cols) if 'email' in c.lower()), 0)
            email_col = st.selectbox("Select Email Column", cols, index=em_idx)
            
            if st.button("⚡ Process Data"):
                st.session_state.df_processed = process_data(df_raw, email_col)
                trigger_save()
                st.rerun()
    else:
        st.success(f"✅ Loaded {len(st.session_state.df_processed)} recipients")
        with st.expander("View Data"):
            st.dataframe(st.session_state.df_processed.head(300))
        
        if st.button("🗑️ Clear Data (Keep Template)"):
            st.session_state.df_processed = None
            st.session_state.sent_ids = set()
            trigger_save()
            st.rerun()