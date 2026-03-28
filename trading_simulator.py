import streamlit as st

st.set_page_config(
    page_title="Rentwise Quant Lab",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.main import main  # noqa: E402 — must come after set_page_config

main()
