import os
import streamlit as st

# ========================
# 📘 基本設定
# ========================
APP_TITLE = "錠嵂保經 AI 模擬考系統"
APP_ICON = "📘"

def init_page_config():
    st.set_page_config(page_title=APP_TITLE, layout="wide", page_icon=APP_ICON)

# ------------------------
# 模型設定
# ------------------------
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
GEMINI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-1.5-flash")

OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_0")

# ------------------------
# 題庫設定
# ------------------------
QUESTION_PATH = "data/question_bank.xlsx"
SHEET_NAMES = ["人身", "外幣", "投資型"]

# ------------------------
# 系統常數
# ------------------------
LETTERS = ["A", "B", "C", "D"]
AI_HINT_BUTTON = "🤖 題目解釋"
OPENBOOK_BUTTON = "📖 開啟章節解釋"
FEEDBACK_GOOD = "👍"
FEEDBACK_BAD = "👎"

# ✅ 改名為公開變數
DOMAIN_OPTIONS = ["人身", "外幣", "投資型"]
