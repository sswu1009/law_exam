# exam_system/ui/theme.py
import streamlit as st

def apply_custom_css():
    css = """
    <style>
    html, body, [class*="css"]  {
        font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif;
        background-color: #f9fbff;
        color: #222;
    }
    h1, h2, h3 { color: #0072E3; font-weight: 700; }
    div.stButton > button {
        background-color: #0072E3; color: white; border: none;
        border-radius: 8px; padding: 0.5em 1.2em;
        font-size: 1rem; font-weight: 600; transition: 0.2s;
    }
    div.stButton > button:hover { background-color: #005bb5; transform: translateY(-1px); }
    section[data-testid="stSidebar"] { background-color: #f3f7fb; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
