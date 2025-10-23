import streamlit as st
import re
import pandas as pd

# --------------------------------------
# 🧠 自動解析題目＋選項
# --------------------------------------
def parse_question_and_options(text: str):
    """
    自動從題目文字中解析出題幹與選項
    例如：
    '風險頻率和幅度的定義？A.損失頻率...B.損失幅度...C.損失金額...D.損失率...'
    """
    pattern = r'(.*?)A[\.、](.*?)B[\.、](.*?)C[\.、](.*?)D[\.、](.*)'
    match = re.match(pattern, text.strip().replace("\n", " "))
    if match:
        question = match.group(1).strip()
        options = [
            match.group(2).strip(),
            match.group(3).strip(),
            match.group(4).strip(),
            match.group(5).strip(),
        ]
        return question, options
    return text.strip(), []


# --------------------------------------
# 🧩 單題渲染（練習模式）
# --------------------------------------
def render_practice_question(qid: str, question: str, options: list, correct_answer: str):
    """顯示單題（練習模式）"""

    # 自動解析合併型題目
    parsed_question, parsed_options = parse_question_and_options(question)
    if parsed_options:
        question = parsed_question
        options = parsed_options

    st.markdown(f"### 📝 題目：\n{question}")

    # 使用者作答狀態
    if f"{qid}_answered" not in st.session_state:
        st.session_state[f"{qid}_answered"] = False
        st.session_state[f"{qid}_selected"] = None

    # 顯示選項
    st.write("請選擇答案：")
    selected = st.radio(
        label="",
        options=[f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)],
        index=None,
        key=f"radio_{qid}",
    )

    if selected:
        st.session_state[f"{qid}_selected"] = selected[0]

    # --- 按鈕互動 ---
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("✅ 對答案", key=f"check_{qid}"):
            st.session_state[f"{qid}_answered"] = True

    with col2:
        if st.button("➡️ 下一題", key=f"next_{qid}"):
            # 若已作答則計分
            if st.session_state[f"{qid}_answered"]:
                if st.session_state[f"{qid}_selected"] == correct_answer:
                    st.session_state["score"] += 1
                else:
                    st.session_state["results"].append({
                        "題號": qid,
                        "題目": question,
                        "你的答案": st.session_state[f"{qid}_selected"],
                        "正確答案": correct_answer,
                    })
            st.session_state["current_q"] += 1
            st.experimental_rerun()

    # --- 顯示對錯與正解 ---
    if st.session_state[f"{qid}_answered"]:
        selected_answer = st.session_state[f"{qid}_selected"]
        if selected_answer == correct_answer:
            st.success(f"✅ 答對了！正確答案是 {correct_answer}")
        else:
            st.error(f"❌ 答錯了，正確答案是 {correct_answer}")

        st.markdown("---")
        st.markdown("💡 **AI 答題助教建議（預留區）**")


# --------------------------------------
# 🧩 模擬考渲染（自動算分）
# --------------------------------------
def render_question_card(qid: str, question: str, options: list):
    """顯示單題（模擬考模式）"""

    # 自動解析題目內含選項
    parsed_question, parsed_options = parse_question_and_options(question)
    if parsed_options:
        question = parsed_question
        options = parsed_options

    st.markdown(f"**題目：** {question}")
    selected = st.radio(
        label="請選擇答案：",
        options=[f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)],
        index=None,
        key=f"radio_{qid}",
    )
    return selected
