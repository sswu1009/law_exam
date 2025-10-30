# ui/layout.py
import streamlit as st
from ui.theme import apply_custom_css

def render_header(title: str, subtitle: str = ""):
    """
    頁面頂部標題區
    - 保留你的中心對齊樣式
    - 加上可選副標題
    - 確保 CSS 只執行一次（避免重複注入）
    """
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
        unsafe_allow_html=True
    )
