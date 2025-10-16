import streamlit as st
from ui.theme import apply_custom_css

def render_header(title: str):
    """頁面頂部標題區"""
    apply_custom_css()
    st.markdown(f"""
    <div style='text-align:center; margin-top:1em; margin-bottom:1.5em;'>
        <h1 style='color:#0072E3;'>{title}</h1>
    </div>
    """, unsafe_allow_html=True)
