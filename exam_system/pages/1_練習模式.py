import streamlit as st
import pandas as pd
from ui.layout import render_header
from ui.components import render_practice_question
from services.db_client import get_questions_by_domain
from config.settings import DOMAIN_OPTIONS


def main():
    render_header("🧠 練習模式")

    # 初始化 session 狀態
    if "practice_started" not in st.session_state:
        st.session_state["practice_started"] = False
    if "current_q" not in st.session_state:
        st.session_state["current_q"] = 0
    if "score" not in st.session_state:
        st.session_state["score"] = 0
    if "results" not in st.session_state:
        st.session_state["results"] = []
    if "practice_df" not in st.session_state:
        st.session_state["practice_df"] = pd.DataFrame()

    # --- Step 1️⃣: 選擇題庫與題數 ---
    domain = st.selectbox("請選擇題庫領域：", DOMAIN_OPTIONS)
    num_questions = st.number_input("請選擇要練習的題數：", min_value=1, max_value=50, value=5, step=1)

    df = get_questions_by_domain(domain)
    if df.empty:
        st.warning("⚠️ 尚未載入題庫或該分類無題目。")
        st.stop()

    # --- Step 2️⃣: 開始練習按鈕 ---
    if not st.session_state["practice_started"]:
        if st.button("🚀 開始練習"):
            # 初始化題目
            df = df.sample(n=min(num_questions, len(df))).reset_index(drop=True)
            st.session_state["practice_df"] = df
            st.session_state["practice_started"] = True
            st.session_state["current_q"] = 0
            st.session_state["score"] = 0
            st.session_state["results"] = []
            st.rerun()  # ✅ 新版 Streamlit 正確寫法
        st.stop()  # 尚未開始則不顯示題目

    # --- Step 3️⃣: 出題 ---
    df = st.session_state["practice_df"]
    i = st.session_state["current_q"]

    if i < len(df):
        row = df.iloc[i]
        qid = f"{domain}_{i+1}"
        question = str(row.get("題目", ""))
        options = [str(row.get(f"選項{opt}", "")) for opt in ["A", "B", "C", "D"] if pd.notna(row.get(f"選項{opt}", ""))]
        correct = str(row.get("答案", "")).strip()
        render_practice_question(qid, question, options, correct_answer=correct)
        st.caption(f"📘 題號 {i+1} / 共 {len(df)} 題")
    else:
        st.success(f"🎉 練習完成，共 {i} 題，答對 {st.session_state.get('score', 0)} 題")

        if len(st.session_state["results"]) > 0:
            st.markdown("#### ❌ 錯題分析")
            st.dataframe(st.session_state["results"], use_container_width=True)

        if st.button("🔄 重新開始練習"):
            st.session_state["practice_started"] = False
            st.rerun()  # ✅ 一併更新這裡


if __name__ == "__main__":
    main()
