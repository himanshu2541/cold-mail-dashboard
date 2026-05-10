import streamlit as st
from dotenv import load_dotenv

from components.app_shell import (
    render_app_header,
    render_empty_workspace,
    render_session_overview,
)
from components.data_view import render_data_view
from components.editor import render_editor
from components.history import render_history
from components.launcher import render_launcher
from components.sidebar import render_sidebar
from components.state import init_state
from components.ui.styles import inject_global_styles


load_dotenv()

st.set_page_config(
    page_title="Cold Mail Dashboard",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_styles()
init_state()

render_app_header()
min_d, max_d, batch_sz, batch_dl, daily_limit = render_sidebar()

if not st.session_state.get("current_session"):
    render_empty_workspace()
    st.stop()

render_session_overview()

compose_tab, recipients_tab, launch_tab, tracking_tab = st.tabs(
    ["Compose", "Recipients", "Launch", "Tracking"]
)

with compose_tab:
    render_editor()

with recipients_tab:
    render_data_view()

with launch_tab:
    render_launcher(min_d, max_d, batch_sz, batch_dl, daily_limit)

with tracking_tab:
    render_history()
