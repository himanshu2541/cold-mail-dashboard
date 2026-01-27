import streamlit as st
from dotenv import load_dotenv
from components.state import init_state
from components.sidebar import render_sidebar
from components.editor import render_editor
from components.data_view import render_data_view
from components.launcher import render_launcher

# Load Env
load_dotenv()

st.set_page_config(page_title="Cold Mail Dashboard", layout="wide")
st.title("📨 Project Mail Sender")

# 1. Initialize State
init_state()

# 2. Render Sidebar & Get Settings
min_d, max_d, batch_sz, batch_dl = render_sidebar()

# 3. Render Main Components
render_editor()
render_data_view()
render_launcher(min_d, max_d, batch_sz, batch_dl)