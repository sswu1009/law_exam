import streamlit as st
import re
import pandas as pd
import google.generativeai as genai  # 若你改用 Ollama，可換成自己的模組


# ========== AI 題目解釋邏輯 ==========
def ai_explain_question(question: str):
    """AI 題目解釋（使用 Gemini，可依需求改成 Ollama / OpenAI）"""
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


# ========== 題目文字解析工具 ==========
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
    """從題目中解析題幹與 A~D 選項"""
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


# ========== 練習模式 題目顯示 ==========
def render_practice_question(qid: str, question: str, options: list, correct_answer: str, row=None):
    """顯示練習題（題目＋AI提示＋選項）"""

    # --- 若沒 options，從 Excel 裡找 A~D ---
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        opts = []
        for col in ["A","B","C","D","選項A","選項B","選項C","選項D"]:
            val = str(row.get(col, "")).strip()
            if val: opts.append(val)
        options = opts

    # --- 若仍沒有，從題目內拆 A~D ---
    if not options:
        q2, opts2 = parse_question_and_options(question)
        if opts2:
            question, options = q2, opts2

    # --- 題目文字 ---
    st.markdown("### 🧠 **題目：**")
    st.write(question)

    # --- AI 解釋區 ---
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
