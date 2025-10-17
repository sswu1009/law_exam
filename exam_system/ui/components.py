import streamlit as st
from config.settings import LETTERS, AI_HINT_BUTTON, OPENBOOK_BUTTON, FEEDBACK_GOOD, FEEDBACK_BAD
from services.ai_client import ai_answer
from services.feedback import save_feedback


def render_practice_question(qid, question_text, options, correct_answer):
    """練習模式題目卡（支援：對答案 / 自動計分 / AI 解釋 / 開啟章節）"""
    st.markdown(f"<div class='question-card'><b>題目：</b> {question_text}</div>", unsafe_allow_html=True)

    selected = st.radio("請選擇答案：", options, index=None, key=f"sel_{qid}")

    # 初始化狀態
    if "checked" not in st.session_state:
        st.session_state["checked"] = False
    if "score" not in st.session_state:
        st.session_state["score"] = 0
    if "results" not in st.session_state:
        st.session_state["results"] = []

    # 對答案按鈕
    if st.button("✅ 對答案", key=f"check_{qid}"):
        if not selected:
            st.warning("請先選擇答案再對答案！")
        else:
            st.session_state["checked"] = True
            if selected == correct_answer:
                st.success("✅ 答對了！")
            else:
                st.error(f"❌ 答錯了，正確答案為：{correct_answer}")

    # 顯示 AI 解釋與章節導讀
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button(AI_HINT_BUTTON, key=f"ai_{qid}"):
            with st.spinner("AI 解釋生成中..."):
                system_msg = "請用保險專業知識解釋以下題目，重點放在為什麼答案正確。"
                ai_resp = ai_answer(system_msg, question_text)
                st.info(ai_resp)
                st.write("這個解釋有幫助嗎？")
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button(FEEDBACK_GOOD, key=f"good_{qid}"):
                        save_feedback(qid, True)
                with c2:
                    if st.button(FEEDBACK_BAD, key=f"bad_{qid}"):
                        save_feedback(qid, False)
    with col2:
        if st.button(OPENBOOK_BUTTON, key=f"openbook_{qid}"):
            st.info("📖 開啟該章節解釋（未來版本可導向筆記章節）")

    # 下一題按鈕
    if st.button("➡️ 下一題", key=f"next_{qid}"):
        # 自動比對與記錄
        if selected == correct_answer:
            st.session_state["score"] += 1
        else:
            st.session_state["results"].append({
                "question": question_text,
                "your_answer": selected,
                "correct": correct_answer
            })
        # 重設狀態與題號
        st.session_state["checked"] = False
        st.session_state["current_q"] = st.session_state.get("current_q", 0) + 1
        st.experimental_rerun()
def render_question_card(qid, question_text, options, correct_answer=None, mode="exam"):
    """模擬考模式：單純對錯顯示與評分"""
    st.markdown(f"<div class='question-card'><b>題目：</b> {question_text}</div>", unsafe_allow_html=True)
    selected = st.radio("請選擇答案：", options, index=None, key=f"exam_{qid}")

    if st.button("提交答案", key=f"submit_{qid}"):
        if not selected:
            st.warning("請先選擇答案再提交！")
        else:
            if selected == correct_answer:
                st.success("✅ 答對了！")
            else:
                st.error(f"❌ 答錯了，正確答案為：{correct_answer}")
