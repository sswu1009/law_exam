# exam_system/config/settings.py
import streamlit as st

# GitHub Config
GH_OWNER = st.secrets.get("REPO_OWNER")
GH_REPO = st.secrets.get("REPO_NAME")
GH_BRANCH = st.secrets.get("REPO_BRANCH", "main")
GH_TOKEN = st.secrets.get("GH_TOKEN")

# Paths
BANKS_DIR = st.secrets.get("BANKS_DIR", "bank")
POINTER_FILE = st.secrets.get("POINTER_FILE", "bank_pointer.json")

# Constants
BANK_TYPES = ["人身", "投資型", "外幣"]
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")

# Gemini Config
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
GEMINI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-1.5-flash")

def get_type_dir(t: str) -> str:
    return f"{BANKS_DIR}/{t}"
