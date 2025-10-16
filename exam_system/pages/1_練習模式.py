import streamlit as st
from ui.layout import render_header
from ui.components import render_question_card
from services.db_client import get_questions_by_domain
from config.settings import _DOMAIN_OPTIONS

def main():
    render_header("🧠 練習模式")

    domain = st.selectbox("請選擇題庫領域：", _DOMAIN_OPTIONS)
    df = get_questions_by_domain(domain)

    if df.empty:
        st.warning("⚠️ 尚未載入題庫或該分類無題目。")
        return

    for idx, row in df.iterrows():
        qid = f"{domain}_{idx+1}"
        question = str(row.get("題目", ""))
        options = [str(row.get(f"選項{opt}", "")) for opt in ["A", "B", "C", "D"] if pd.notna(row.get(f"選項{opt}", ""))]
        correct = str(row.get("答案", "")).strip()
        render_question_card(qid, question, options, correct_answer=correct, mode="practice")

if __name__ == "__main__":
    main()
