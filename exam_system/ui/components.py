import streamlit as st
import re
import pandas as pd

# --------------------------------------
# 題目文字清理與解析（備用方案）
# --------------------------------------
def _normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    trans = str.maketrans({
        "Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D",
        "（": "(", "）": ")", "．": ".", "、": ".", "：": ":"
    })
    s = s.translate(trans)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_question_and_options(raw_text: str):
    """當題目內含 A./A、/(A) 時自動切割"""
    s = _normalize_text(raw_text)
    # 嘗試從題目中切出 A~D
    a_split = re.split(r"\sA[\.、]\s*", s, maxsplit=1)
    if len(a_split) != 2:
        return raw_text.strip(), []

    q_text, rest = a_split[0].strip(), a_split[1].strip()
    b_split = re.split(r"\sB[\.、]\s*", rest, maxsplit=1)
    if len(b_split) != 2:
        return raw_text.strip(), []
    A_text, rest = b_split[0].strip(), b_split[1].strip()

    c_split = re.split(r"\sC[\.、]\s*", rest, maxsplit=1)
    if len(c_split) != 2:
        return raw_text.strip(), []
    B_text, rest = c_split[0].strip(), rest

    d_split = re.split(r"\sD[\.、]\s*", rest, maxsplit=1)
    if len(d_split) != 2:
        return raw_text.strip(), []
    C_text, D_text = d_split[0].strip(), d_split[1].strip()

    return q_text, [A_text, B_text, C_text, D_text]


# --------------------------------------
# 練習模式題目顯示
# --------------------------------------
def render_practice_question(qid: str, question: str, options: list, correct_answer: str, row=None):
    """顯示練習題，支援欄位或內嵌選項格式"""

    # 🔹 若 options 為空，嘗試從 row 取得 A/B/C/D 欄位
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        alt_opts = []
        for col in ["A", "B", "C", "D", "選項A", "選項B", "選項C", "選項D"]:
            if col in row and pd.notna(row[col]):
                alt_opts.append(str(row[col]).strip())
        options = alt_opts

    # 🔹 若仍無法取得，嘗試從題目內解析
    if not options:
        parsed_q, parsed_opts = parse_question_and_options(question)
        if parsed_opts:
            question, options = parsed_q, parsed_opts

    st.markdown("### 📝 **題目：**")
    st.write(question)

    if not options:
        st.warning("⚠️ 此題缺少選項欄位，且無法從題目內解析 A/B/C/D，請檢查題庫格式。")
        return

    sel_key = f"radio_{qid}"
    ans_flag = f"{qid}_answered"
    sel_store = f"{qid}_selected"

    if ans_flag not in st.session_state:
        st.session_state[ans_flag] = False
    if sel_store not in st.session_state:
        st.session_state[sel_store] = None

    picked = st.radio(
        "請選擇答案：",
        [f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)],
        index=None,
        key=sel_key,
    )

    if picked:
        st.session_state[sel_store] = picked[0]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 對答案", key=f"check_{qid}"):
            st.session_state[ans_flag] = True
    with col2:
        if st.button("➡️ 下一題", key=f"next_{qid}"):
            chosen = st.session_state.get(sel_store)
            if chosen == correct_answer:
                st.session_state["score"] = st.session_state.get("score", 0) + 1
            else:
                if "results" not in st.session_state:
                    st.session_state["results"] = []
                st.session_state["results"].append({
                    "題號": qid,
                    "題目": question,
                    "你的答案": chosen,
                    "正確答案": correct_answer,
                })
            st.session_state["current_q"] = st.session_state.get("current_q", 0) + 1
            st.session_state[ans_flag] = False
            st.rerun()

    if st.session_state[ans_flag]:
        chosen = st.session_state.get(sel_store)
        if chosen == correct_answer:
            st.success(f"✅ 答對了！正確答案：{correct_answer}")
        else:
            st.error(f"❌ 答錯了！正確答案：{correct_answer}")


# --------------------------------------
# 模擬考模式題目顯示
# --------------------------------------
def render_question_card(qid: str, question: str, options: list, correct_answer=None, row=None):
    """顯示模擬考題，支援欄位或內嵌格式"""
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        alt_opts = []
        for col in ["A", "B", "C", "D", "選項A", "選項B", "選項C", "選項D"]:
            if col in row and pd.notna(row[col]):
                alt_opts.append(str(row[col]).strip())
        options = alt_opts

    if not options:
        parsed_q, parsed_opts = parse_question_and_options(question)
        if parsed_opts:
            question, options = parsed_q, parsed_opts

    st.markdown(f"**題目：** {question}")
    if not options:
        st.warning("⚠️ 無法顯示選項。")
        return None

    picked = st.radio(
        "請選擇答案：",
        [f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)],
        index=None,
        key=f"exam_{qid}",
    )
    return picked[0] if picked else None
