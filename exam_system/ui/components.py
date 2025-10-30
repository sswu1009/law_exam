import re
import pandas as pd
import streamlit as st

def _normalize_text(s: str) -> str:
    if not isinstance(s, str): return ""
    trans = str.maketrans({
        "Ａ":"A","Ｂ":"B","Ｃ":"C","Ｄ":"D",
        "（":"(","）":")","．":".","、":".","：":":","；":";"
    })
    s = s.translate(trans)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_question_and_options(raw_text: str):
    """
    從題目內解析 A/B/C/D，支援：
    A. / A、 / (A) / （A），以及分隔符為空白或； ; 。
    """
    s = _normalize_text(raw_text)

    # 找出 A/B/C/D 標記位置
    token = r"(?:\(|（)?([A-D])(?:\)|）)?[\.]"
    marks = list(re.finditer(token, s))
    if len(marks) < 4:           # 找不到完整四個選項
        return raw_text.strip(), []

    # 題幹：從開頭到 A. 之前
    q = s[:marks[0].start()].strip()

    # 依序切 A~D 之間的文字（允許前面有 ; 或 ；）
    def seg(i, j):
        return s[marks[i].end(): marks[j].start()].lstrip(" ;").strip()

    A = seg(0,1); B = seg(1,2); C = seg(2,3)
    D = s[marks[3].end():].lstrip(" ;").strip()

    return q, [A, B, C, D]

def render_practice_question(qid: str, question: str, options: list, correct_answer: str, row=None):
    # 1) 優先：從 Excel 欄位 A/B/C/D 取
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        opts = []
        for col in ["A","B","C","D","選項A","選項B","選項C","選項D"]:
            val = str(row.get(col, "")).strip()
            if val: opts.append(val)
        options = opts

    # 2) 仍沒有 → 從題目字串解析
    if not options:
        q2, opts2 = parse_question_and_options(question)
        if opts2:
            question, options = q2, opts2

    st.markdown("### 📝 **題目：**")
    st.write(question)

    if not options:
        st.warning("⚠️ 無法取得選項（請確認是否有 A~D 欄位或題目內含 A./B./C./D.）。")
        return

    # radio 直接帶「A. 文字」「B. 文字」
    sel_key = f"radio_{qid}"
    ans_flag = f"{qid}_answered"
    sel_store = f"{qid}_selected"

    if ans_flag not in st.session_state: st.session_state[ans_flag] = False
    if sel_store not in st.session_state: st.session_state[sel_store] = None

    display = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)]
    picked = st.radio("", display, index=None, key=sel_key)
    if picked: st.session_state[sel_store] = picked[0]  # A/B/C/D

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ 對答案", key=f"check_{qid}"):
            st.session_state[ans_flag] = True
    with c2:
        if st.button("➡️ 下一題", key=f"next_{qid}"):
            chosen = st.session_state.get(sel_store)
            if chosen == correct_answer:
                st.session_state["score"] = st.session_state.get("score", 0) + 1
            else:
                st.session_state.setdefault("results", []).append({
                    "題號": qid, "題目": question, "你的答案": chosen, "正確答案": correct_answer
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
