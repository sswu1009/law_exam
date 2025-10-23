import streamlit as st
import re
import pandas as pd

# -----------------------------
# 題目字串解析工具
# -----------------------------
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
    """從題目中切出題幹與選項（支援 A. / A、 / (A)）"""
    s = _normalize_text(raw_text)

    # 嘗試切出 A~D
    pattern = r"(.*?)A[\.、]\s*(.*?)B[\.、]\s*(.*?)C[\.、]\s*(.*?)D[\.、]\s*(.*)"
    m = re.match(pattern, s)
    if m:
        q = m.group(1).strip()
        options = [m.group(2).strip(), m.group(3).strip(), m.group(4).strip(), m.group(5).strip()]
        return q, options
    return raw_text.strip(), []


# -----------------------------
# 練習模式題目顯示
# -----------------------------
def render_practice_question(qid: str, question: str, options: list, correct_answer: str, row=None):
    """顯示練習題（題目與選項分開）"""

    # 若沒傳入 options，嘗試從 Excel 欄位取 A~D
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        alt_opts = []
        for col in ["A", "B", "C", "D", "選項A", "選項B", "選項C", "選項D"]:
            if col in row and pd.notna(row[col]):
                alt_opts.append(str(row[col]).strip())
        options = alt_opts

    # 若還是沒有就解析題目文字
    if not options:
        parsed_q, parsed_opts = parse_question_and_options(question)
        if parsed_opts:
            question, options = parsed_q, parsed_opts

    # -----------------------------
    # 顯示題目 + 選項
    # -----------------------------
    st.markdown("### 📝 **題目：**")
    st.write(question)

    if options:
        st.markdown("#### **選項：**")
        for i, opt in enumerate(options):
            st.markdown(f"- **{chr(65+i)}.** {opt}")
    else:
        st.warning("⚠️ 此題缺少選項資料。")
        return

    # -----------------------------
    # 作答區
    # -----------------------------
    sel_key = f"radio_{qid}"
    ans_flag = f"{qid}_answered"
    sel_store = f"{qid}_selected"

    if ans_flag not in st.session_state:
        st.session_state[ans_flag] = False
    if sel_store not in st.session_state:
        st.session_state[sel_store] = None

    st.write("請選擇答案：")
    picked = st.radio(
        "",
        [f"{chr(65+i)}" for i in range(len(options))],
        index=None,
        key=sel_key,
        horizontal=False,
    )

    if picked:
        st.session_state[sel_store] = picked

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

    # -----------------------------
    # 對答案回饋
    # -----------------------------
    if st.session_state[ans_flag]:
        chosen = st.session_state.get(sel_store)
        if chosen == correct_answer:
            st.success(f"✅ 答對了！正確答案是 {correct_answer}")
        else:
            st.error(f"❌ 答錯了！正確答案是 {correct_answer}")


# -----------------------------
# 模擬考模式題目顯示
# -----------------------------
def render_question_card(qid: str, question: str, options: list, correct_answer=None, row=None):
    """模擬考模式，題目與選項分開"""
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
    if options:
        for i, opt in enumerate(options):
            st.markdown(f"- **{chr(65+i)}.** {opt}")
    else:
        st.warning("⚠️ 無法顯示選項。")
        return None

    picked = st.radio(
        "請選擇答案：",
        [f"{chr(65+i)}" for i in range(len(options))],
        index=None,
        key=f"exam_{qid}",
    )
    return picked if picked else None
