# exam_system/ui/layout.py
import streamlit as st
from ui.theme import apply_custom_css

def render_header(title: str, subtitle: str = ""):
    if "css_applied" not in st.session_state:
        apply_custom_css()
        st.session_state["css_applied"] = True

    st.markdown(
        f"""
        <div style='text-align:center; margin-top:1em; margin-bottom:1.5em;'>
            <h1 style='color:#0072E3;'>{title}</h1>
            {f"<h4 style='color:#555;'>{subtitle}</h4>" if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

def render_sidebar_info():
    st.sidebar.markdown("### 📖 系統資訊")
    st.sidebar.info(
        "**錠嵂保經 AI 模擬考系統**\n"
        "- 題庫動態讀取 bank/\n"
        "- 練習：即時回饋 + AI 解釋\n"
        "- 模擬考：成績統計\n"
    )

def render_footer():
    st.markdown("---")
    st.caption("錠嵂保經 AI 模擬考系統 © 2025")
