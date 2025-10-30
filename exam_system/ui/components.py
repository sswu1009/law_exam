import streamlit as st
import re
import pandas as pd
import google.generativeai as genai


# ========== AI 題目解釋 ==========
def ai_explain_question(question: str):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
你是一位保險法與金融專業講師。
請用清楚、簡短且容易理解的方式解釋下列題目的意思與考點（不要直接給答案）。

題目：
{question}
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ AI 解釋時出錯：{e}"


# ========== 解析文字 ==========
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
    s = _normalize_text(raw_text)
    token = r"(?:\(|（)?([A-D])(?:\)|）)?[\.、]"
    marks = list(re.finditer(token, s))
    if len(marks) < 4:
        return raw_text.strip(), []
    q = s[:marks[0].start()].strip()
    def seg(i, j):
        return s[marks[i].end(): marks[j].start()].lstrip(" ;").strip()
    A = seg(0,1); B = seg(1,2); C = seg(2,3); D = s[marks[3].end():].lstrip(" ;").strip()
    return q, [A,B,C,D]


# ========== 智慧選項擷取 ==========
def extract_options(row: pd.Series):
    """可自動辨識欄名：A~D、選項A~D、選項一~選項四、1~4"""
    possible_sets = [
        ["A", "B", "C", "D"],
        ["選項A", "選項B", "選項C", "選項D"],
        ["選項一", "選項二", "選項三", "選項四"],
        ["1", "2", "3", "4"],
        ["option1", "option2", "option3", "option4"]
    ]
    for cols in possible_sets:
        opts = [str(row.get(c, "")).strip() for c in cols if str(row.get(c, "")).strip()]
        if len(opts) >= 2:  # 至少要有兩個選項才視為有效
            return opts
    return []


# ========== 題目渲染 ==========
def render_practice_question(qid: str, question: str, options: list, correct_answer: str, row=None):
    """顯示題目 + AI提示 + 選項 + 對答案"""

    # --- 智慧抓選項 ---
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        options = extract_options(row)

    if not options:
        q2, opts2 = parse_question_and_options(question)
        if opts2:
            question, options = q2, opts2

    # --- 題目 ---
    st.markdown("### 🧠 **題目：**")
    st.write(question)

    # --- AI 解釋 ---
    explain_key = f"explain_{qid}"
    if st.button("🧠 看不懂題目嗎？", key=explain_key):
        with st.spinner("AI 助教正在說明中..."):
            explanation = ai_explain_question(question)
            st.markdown(f"#### 💬 AI 解釋：\n{explanation}")

    # --- 顯示選項 ---
    if not options:
        st.warning("⚠️ 無法取得選項，請檢查題庫格式。")
        return

    sel_key = f"radio_{qid}"
    ans_flag = f"{qid}_answered"
    sel_store = f"{qid}_selected"

    if ans_flag not in st.session_state: st.session_state[ans_flag] = False
    if sel_store not in st.session_state: st.session_state[sel_store] = None

    display = [f"{chr(65+i)}. {opt}" for i,opt in enumerate(options)]
    picked = st.radio("", display, index=None, key=sel_key)
    if picked: st.session_state[sel_store] = picked[0]

    # --- 對答案與下一題 ---
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
                    "題號": qid,
                    "題目": question,
                    "你的答案": chosen,
                    "正確答案": correct_answer,
                })
            st.session_state["current_q"] = st.session_state.get("current_q", 0) + 1
            st.session_state[ans_flag] = False
            st.rerun()

    # --- 對答案顯示 ---
    if st.session_state.get(ans_flag):
        chosen = st.session_state.get(sel_store)
        if chosen == correct_answer:
            st.success(f"✅ 答對了！正確答案：{correct_answer}")
        else:
            st.error(f"❌ 答錯了！正確答案：{correct_answer}")
