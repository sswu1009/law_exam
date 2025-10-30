# ui/theme.py
import streamlit as st

def apply_custom_css():
    """
    套用全域自訂 CSS：
    - 主色 (#0072E3)
    - 按鈕與 radio 樣式
    - 背景與字型
    """
    css = """
    <style>
    /* === 全域背景與字型設定 === */
    html, body, [class*="css"]  {
        font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif;
        background-color: #f9fbff;
        color: #222;
    }

    /* === 標題樣式 === */
    h1, h2, h3 {
        color: #0072E3;
        font-weight: 700;
    }

    /* === Streamlit 按鈕樣式 === */
    div.stButton > button {
        background-color: #0072E3;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5em 1.2em;
        font-size: 1rem;
        font-weight: 600;
        transition: 0.2s;
    }
    div.stButton > button:hover {
        background-color: #005bb5;
        transform: translateY(-1px);
    }

    /* === Radio / Selectbox === */
    div[role="radiogroup"] label, .stSelectbox label {
        color: #333 !important;
        font-weight: 500;
    }

    /* === Expander 樣式 === */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #0072E3 !important;
    }

    /* === 成功與錯誤區塊 === */
    .stSuccess {
        background-color: #e6f4ff;
        border-left: 5px solid #0072E3;
    }
    .stError {
        background-color: #fff0f0;
        border-left: 5px solid #ff4d4f;
    }

    /* === Sidebar === */
    section[data-testid="stSidebar"] {
        background-color: #f3f7fb;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
