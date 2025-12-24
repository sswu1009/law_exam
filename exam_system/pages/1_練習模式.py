# pages/1_練習模式.py
import streamlit as st
import pandas as pd

from services.db_client import (
    list_categories,
    list_chapters,
    pick_questions,
)
from ui.components import (
    render_category_selector,
    render_chapter_selector,
    render_question_card,
    render_question_summary,
)

from ui.layout import (
    render_header,
    render_sidebar_info,
    render_footer,
)


# === 頁面初始設定 ===
st.set_page_config(page_title="練習模式", layout="wide")
render_header("🧠 練習模式", "單題作答、即時回饋與 AI 助教提示")
render_sidebar_info()


# === 狀態初始化 ===
if "practice_initialized" not in st.session_state:
    st.session_state.practice_initialized = False
    st.session_state.questions_df = pd.DataFrame()
    st.session_state.current_index = 0
    st.session_state.correct_count = 0


# === 題庫選擇 ===
categories = list_categories()
selected_category = render_category_selector(categories)

if selected_category:
    chapters = list_chapters(selected_category)
    selected_chapter = render_chapter_selector(chapters)
else:
    st.stop()


# === 題庫載入與出題 ===
col1, col2 = st.columns([3, 1])
with col1:
    if st.button("🎯 開始練習", use_container_width=True):
        df = pick_questions(selected_category, chapter=selected_chapter, limit=10)
        if df.empty:
            st.warning("此章節暫無題目。")
            st.stop()

        st.session_state.questions_df = df
        st.session_state.current_index = 0
        st.session_state.correct_count = 0
        st.session_state.practice_initialized = True


# === 若尚未按下開始練習則停止 ===
if not st.session_state.practice_initialized or st.session_state.questions_df.empty:
    st.info("請選擇題庫與章節後按下『開始練習』。")
    render_footer()
    st.stop()


# === 顯示題目 ===
df = st.session_state.questions_df
idx = st.session_state.current_index

if idx < len(df):
    q = df.iloc[idx]
    options = {
        "A": q.get("選項A", ""),
        "B": q.get("選項B", ""),
        "C": q.get("選項C", ""),
        "D": q.get("選項D", ""),
    }
    correct = str(q.get("答案", "")).strip().upper()[:1]

    # 顯示題目卡
    render_question_card(
        q_index=idx,
        question_text=q.get("題目", ""),
        options=options,
        correct_answer=correct,
        show_ai_hint=True,
    )

    # 下一題按鈕
    st.divider()
    if st.button("➡️ 下一題", use_container_width=True):
        # 若上題答對則計數
        last_key = f"q{idx}_ans"
        if st.session_state.get(last_key) == correct:
            st.session_state.correct_count += 1

        st.session_state.current_index += 1
        st.rerun()

else:
    # === 全部答完 ===
    render_question_summary(
        total=len(df),
        correct=st.session_state.correct_count,
    )
    if st.button("🔁 重新開始", use_container_width=True):
        st.session_state.practice_initialized = False
        st.session_state.questions_df = pd.DataFrame()
        st.session_state.current_index = 0
        st.session_state.correct_count = 0
        st.rerun()

render_footer()
