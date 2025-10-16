import streamlit as st
import random
import pandas as pd
from ui.layout import render_header
from ui.components import render_question_card
from services.db_client import get_questions_by_domain
from config.settings import _DOMAIN_OPTIONS

def main():
    render_header("📝 模擬考模式")

    domain = st.selectbox("請選擇考試領域：", _DOMAIN_OPTIONS)
    num_questions = st.number_input("選擇題數", min_value=5, max_value=50, value=10, step=5)

    df = get_questions_by_domain(domain)
    if df.empty:
        st.warning("⚠️ 尚未載入題庫或該分類無題目。")
        return

    sample = df.sample(n=min(num_questions, len(df)))
    score = 0

    st.write("⏱️ 模擬考開始，請作答：")

    for idx, row in sample.iterrows():
        qid = f"exam_{domain}_{idx}"
        question = str(row.get("題目", ""))
        options = [str(row.get(f"選項{opt}", "")) for opt in ["A", "B", "C", "D"] if pd.notna(row.get(f"選項{opt}", ""))]
        correct = str(row.get("答案", "")).strip()
        render_question_card(qid, question, options, correct_answer=correct, mode="exam")

    st.markdown("---")
    st.info("📊 完成作答後，可回到首頁查看統計或回饋記錄。")

if __name__ == "__main__":
    main()
