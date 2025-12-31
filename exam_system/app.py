from pathlib import Path
import sys
import streamlit as st

# ✅ 確保 exam_system/ 目錄在 sys.path，避免 import 找不到
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main():
    st.set_page_config(page_title="錠嵂保經 AI 模擬考系統", layout="wide")

    st.sidebar.page_link("pages/1_練習模式.py", label="🧠 練習模式")
    st.sidebar.page_link("pages/2_模擬考模式.py", label="📝 模擬考模式")
    # 若尚未建立 3_AI解釋區.py，先不要加 page_link，避免 PageNotFound


if __name__ == "__main__":
    main()
