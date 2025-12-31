from __future__ import annotations
import streamlit as st

# -----------------------------
# App
# -----------------------------
APP_TITLE = "錠嵂AI考照機器人"
PAGE_TITLE = "錠嵂AI考照"
LAYOUT = "wide"

# -----------------------------
# Gemini
# -----------------------------
def gemini_ready() -> bool:
    return bool(st.secrets.get("GEMINI_API_KEY"))

GEMINI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-1.5-flash")

# -----------------------------
# GitHub repo settings (Secrets)
# -----------------------------
GH_OWNER  = st.secrets.get("REPO_OWNER")
GH_REPO   = st.secrets.get("REPO_NAME")
GH_BRANCH = st.secrets.get("REPO_BRANCH", "main")
GH_TOKEN  = st.secrets.get("GH_TOKEN")

BANKS_DIR    = st.secrets.get("BANKS_DIR", "bank")
POINTER_FILE = st.secrets.get("POINTER_FILE", "bank_pointer.json")

BANK_TYPES = ["人身", "投資型", "外幣", "產險"]

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")

def type_dir(t: str) -> str:
    return f"{BANKS_DIR}/{t}"

def gh_write_ready() -> tuple[bool, str]:
    missing = []
    if not GH_OWNER:  missing.append("REPO_OWNER")
    if not GH_REPO:   missing.append("REPO_NAME")
    if not GH_BRANCH: missing.append("REPO_BRANCH")
    if not GH_TOKEN:  missing.append("GH_TOKEN (需要寫入權限)")
    if missing:
        return False, "缺少 secrets：" + ", ".join(missing)
    return True, ""
