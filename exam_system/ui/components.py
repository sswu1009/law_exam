import streamlit as st
import re
import pandas as pd

# =========================================
# 強韌題目/選項解析
# =========================================
def _normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # 全形字元與標點轉半形
    trans = str.maketrans({
        "Ａ":"A","Ｂ":"B","Ｃ":"C","Ｄ":"D",
        "（":"(", "）":")", "．":".", "、":".", "：":":"
    })
    s = s.translate(trans)
    # (A) / （A） -> A.
    s = re.sub(r"\(\s*([A-D])\s*\)", r"\1.", s)
    # 消弭多餘空白與換行
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_question_and_options(raw_text: str):
    """
    從「題目字串」中抽出 (question, [A,B,C,D])。
    支援標記：A. / A、/ (A) / （A） ，含全形/半形、換行、空白。
    解析失敗回傳 (原字串, [])。
    """
    s = _normalize_text(raw_text)

    # 先找 A. 的切點
    a_split = re.split(r"\sA\.\s", s, maxsplit=1)
    if len(a_split) != 2:
        return raw_text.strip(), []

    q_text, rest = a_split[0].strip(), a_split[1].strip()

    # 依序切 B.、C.、D.
    b_split = re.split(r"\sB\.\s", rest, maxsplit=1)
    if len(b_split) != 2:  # 沒有 B. 就當作解析失敗
        return raw_text.strip(), []
    A_text, rest = b_split[0].strip(), b_split[1].strip()

    c_split = re.split(r"\sC\.\s", rest, maxsplit=1)
    if len(c_split) != 2:
        return raw_text.strip(), []
    B_text, rest = c_split[0].strip(), c_split[1].strip()

    d_split = re.split(r"\sD\.\s", rest, maxsplit=1)
    if len(d_split) != 2:
        return raw_text.strip(), []
    C_text, D_text = d_split[0].strip(), d_split[1].strip()

    options = [A_text, B_text, C_text, D_text]
    return q_text, options

# =========================================
# 練習模式：單題渲染（對答案→下一題時計分）
# =========================================
def render_practice_question(qid: str, question: str, options: list, correct_answer: str):
    # 若 options 為空，嘗試從題目字串解析
    parsed_q, parsed_opts = parse_question_and_options(question)
    if parsed_opts:  # 解析成功就覆蓋
        question = parsed_q
        options = parsed_opts

    st.markdown("### 📝 **題目：**")
    st.write(question)

    if not options:
        st.warning("此題缺少選項欄位，且無法從題目內解析出 A/B/C/D，請檢查題庫格式。")
        return

    # 初始化作答狀態
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
        st.session_state[sel_store] = picked[0]  # 取字首 A/B/C/D

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 對答案", key=f"check_{qid}"):
            st.session_state[ans_flag] = True

    with col2:
        if st.button("➡️ 下一題", key=f"next_{qid}"):
            # 已對過答案才即時計分；未對也要在跳題時自動計分
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
            st.session_state[ans_flag] = False
            st.session_state["current_q"] = st.session_state.get("current_q", 0) + 1
            st.rerun()

    if st.session_state[ans_flag]:
        chosen = st.session_state.get(sel_store)
        if chosen == correct_answer:
            st.success(f"✅ 答對了！正確答案：{correct_answer}")
        else:
            st.error(f"❌ 答錯了！正確答案：{correct_answer}")

# =========================================
# 模擬考模式：單題渲染（回傳所選選項字母）
# =========================================
def render_question_card(qid: str, question: str, options: list, correct_answer=None, mode="exam"):
    # 若 options 為空，嘗試從題目字串解析
    parsed_q, parsed_opts = parse_question_and_options(question)
    if parsed_opts:
        question = parsed_q
        options = parsed_opts

    st.markdown(f"**題目：** {question}")

    if not options:
        st.warning("此題缺少選項欄位，且無法從題目內解析出 A/B/C/D，請檢查題庫格式。")
        return None

    picked = st.radio(
        "請選擇答案：",
        [f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)],
        index=None,
        key=f"exam_{qid}",
    )

    if picked and mode == "exam" and correct_answer:
        # 若需要當場評分可在此比對（目前模擬考通常最後一起評分）
        pass

    return picked[0] if picked else None
