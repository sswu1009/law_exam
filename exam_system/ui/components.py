import streamlit as st
from config.settings import LETTERS, AI_HINT_BUTTON, OPENBOOK_BUTTON, FEEDBACK_GOOD, FEEDBACK_BAD
from services.ai_client import ai_answer
from services.feedback import save_feedback

def render_question_card(qid, question_text, options, correct_answer=None, mode="practice"):
    """呈現題目卡：可切換練習 / 模擬考模式"""
    st.markdown(f"<div class='question-card'><b>題目：</b> {question_text}</div>", unsafe_allow_html=True)
    selected = st.radio("請選擇答案：", options, index=None, key=f"q_{qid}")

    if mode == "exam":
        if st.button("確認答案", key=f"submit_{qid}"):
            if selected == correct_answer:
                st.success("✅ 答對了！")
            else:
                st.error(f"❌ 答錯，正確答案為：{correct_answer}")
    else:
        # 練習模式
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(AI_HINT_BUTTON, key=f"ai_{qid}"):
                with st.spinner("AI 解釋生成中..."):
                    system_msg = "請用保險業專業知識解釋以下題目"
                    ai_resp = ai_answer(system_msg, question_text)
                    st.info(ai_resp)
                    # 收集回饋
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
