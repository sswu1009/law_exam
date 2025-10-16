import streamlit as st

# ======================
# 🎨 主題設定
# ======================
PRIMARY_COLOR = "#0072E3"
SECONDARY_COLOR = "#4CAF50"
WARNING_COLOR = "#FFB74D"
DANGER_COLOR = "#E57373"
BACKGROUND = "#F7F9FB"

def apply_custom_css():
    """注入全域 CSS，美化版面"""
    st.markdown(f"""
    <style>
        body {{
            background-color: {BACKGROUND};
        }}
        .stButton>button {{
            border-radius: 10px;
            padding: 0.6em 1.2em;
            font-weight: 600;
            color: white;
            background: {PRIMARY_COLOR};
            border: none;
            transition: 0.2s;
        }}
        .stButton>button:hover {{
            background: {SECONDARY_COLOR};
            color: white;
            transform: scale(1.02);
        }}
        .question-card {{
            background-color: white;
            border-radius: 12px;
            padding: 1.2em;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1em;
        }}
        .option-btn {{
            border-radius: 8px;
            padding: 0.6em 1em;
            margin: 0.2em 0;
            border: 1px solid #ddd;
            background: #fff;
            text-align: left;
        }}
        .option-btn:hover {{
            background-color: #E3F2FD;
        }}
        .correct {{
            background-color: #C8E6C9 !important;
            border-color: #2E7D32 !important;
        }}
        .wrong {{
            background-color: #FFCDD2 !important;
            border-color: #C62828 !important;
        }}
    </style>
    """, unsafe_allow_html=True)
