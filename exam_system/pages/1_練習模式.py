import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]  # exam_system
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st

from config.settings import BANK_DIR
from services.db_client import load_all_banks

st.write("BANK_DIR =", BANK_DIR)
st.write("題庫分類 =", list(load_all_banks().keys()))



# pages/1_練習模式.py
import streamlit as st
import pandas as pd

from services.db_client import list_categories, list_chapters, pick_questions
from ui.components import render_question_card, render_question_summary, render_category_selector, render_chapter_selector
from ui.layout import render_header, render_sidebar_info, render_footer

st.set_page_config(page_title="練習模式", layout="wide")
render_header("🧠 練習模式", "單題作答、即時回饋與 AI 助教提示")
render_sidebar_info()

if "practice_initialized" not in st.session_state:
    st.session_state.practice_initialized = False
    st.session_state.questions_df = pd.DataFrame()
    st.session_state.current_index = 0
    st.session_state.correct_count = 0

categories = list_categories()
selected_category = render_category_selector(categories)
if not selected_category:
    st.stop()

chapters = list_chapters(selected_category)
selected_chapter = render_chapter_selector(chapters)

if st.button("🎯 開始練習", use_container_width=True):
    df = pick_questions(selected_category, chapter=selected_chapter, limit=10)
    if df.empty:
        st.warning("此章節暫無題目。")
        st.stop()

    st.session_state.questions_df = df
    st.session_state.current_index = 0
    st.session_state.correct_count = 0
    st.session_state.practice_initialized = True

if not st.session_state.practice_initialized or st.session_state.questions_df.empty:
    st.info("請選擇題庫與章節後按下『開始練習』。")
    render_footer()
    st.stop()

df = st.session_state.questions_df
idx = st.session_state.current_index

if idx < len(df):
    q = df.iloc[idx]

    # 先用最常見欄位名（你之後若要做更強的動態欄位偵測，再加）
    options = {
        "A": str(q.get("選項A", "")).strip(),
        "B": str(q.get("選項B", "")).strip(),
        "C": str(q.get("選項C", "")).strip(),
        "D": str(q.get("選項D", "")).strip(),
    }

    correct = str(q.get("答案", "")).strip().upper()[:1]
    question_text = str(q.get("題目", "")).strip()

    render_question_card(idx, question_text, options, correct, show_ai_hint=True)

    st.divider()
    if st.button("➡️ 下一題", use_container_width=True):
        last_key = f"q{idx}_ans"
        if st.session_state.get(last_key) == correct:
            st.session_state.correct_count += 1
        st.session_state.current_index += 1
        st.rerun()
else:
    render_question_summary(total=len(df), correct=st.session_state.correct_count)
    if st.button("🔁 重新開始", use_container_width=True):
        st.session_state.practice_initialized = False
        st.session_state.questions_df = pd.DataFrame()
        st.session_state.current_index = 0
        st.session_state.correct_count = 0
        st.rerun()

render_footer()
