"""
集中管理所有設定與常數
"""
import streamlit as st

# GitHub 設定
GH_OWNER = st.secrets.get("REPO_OWNER")
GH_REPO = st.secrets.get("REPO_NAME")
GH_BRANCH = st.secrets.get("REPO_BRANCH", "main")
GH_TOKEN = st.secrets.get("GH_TOKEN")

# 題庫設定
BANKS_DIR = st.secrets.get("BANKS_DIR", "bank")
POINTER_FILE = st.secrets.get("POINTER_FILE", "bank_pointer.json")
DEFAULT_BANK_FILE = st.secrets.get("BANK_FILE", f"{BANKS_DIR}/exam_bank.xlsx")

# 題庫類型
BANK_TYPES = ["人身", "投資型", "外幣"]

# Gemini 設定
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
GEMINI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-1.5-flash")

# 管理者設定
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")

# 應用設定
APP_TITLE = "錠嵂AI考照機器人"
PAGE_ICON = "📚"

def get_type_dir(bank_type: str) -> str:
    """取得特定類型的題庫資料夾路徑"""
    return f"{BANKS_DIR}/{bank_type}"

def validate_github_config() -> tuple[bool, str]:
    """驗證 GitHub 設定是否完整"""
    missing = []
    if not GH_OWNER:
        missing.append("REPO_OWNER")
    if not GH_REPO:
        missing.append("REPO_NAME")
    if not GH_BRANCH:
        missing.append("REPO_BRANCH")
    
    if missing:
        return False, f"缺少必要設定：{', '.join(missing)}"
    return True, ""

def validate_github_write_config() -> tuple[bool, str]:
    """驗證 GitHub 寫入權限設定"""
    ok, msg = validate_github_config()
    if not ok:
        return False, msg
    
    if not GH_TOKEN:
        return False, "缺少 GH_TOKEN（需要寫入權限）"
    return True, ""

def gemini_ready() -> bool:
    """檢查 Gemini 是否已設定"""
    return bool(GEMINI_API_KEY)
