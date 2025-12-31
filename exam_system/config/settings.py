import streamlit as st
import os

# === 系統基本設定 ===
APP_TITLE = "錠嵂保經 AI 模擬考系統"
APP_ICON = "🛡️"

# === 路徑設定 ===
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # exam_system
BANK_DIR = BASE_DIR / "bank"

# === AI 設定 ===
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
GEMINI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-1.5-flash")

# === 題庫分類 (可依照 bank 資料夾結構動態調整，這裡保留預設值) ===
DEFAULT_CATEGORIES = ["人身", "外幣", "投資型", "產險"]

def init_page_config():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
