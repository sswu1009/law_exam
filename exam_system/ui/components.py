import streamlit as st
import re
import pandas as pd

# ========== (1) AI 題目解釋 ==========
def ai_explain_question(question: str):
    """
    若有 GEMINI_API_KEY 才呼叫，沒有就回傳友善提示。
    你之後要換成 Ollama / OpenAI 只要改這裡就好。
    """
    # 沒有金鑰就直接回傳提示，避免整頁報錯
    if "GEMINI_API_KEY" not in st.secrets:
        return "（目前未設定 AI 金鑰，無法產生題目解釋，請到 .streamlit/secrets.toml 加上 GEMINI_API_KEY）"

    try:
        import google.generativeai as genai
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
你是一位保險相關考照的輔導老師，請把下面這題「題意」講清楚，讓考生知道它在問什麼、要抓哪幾個關鍵字。
不要直接說出正確選項，只要解釋題目。

題目：
{question}
"""
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        # 這裡一樣不要炸版，回簡短訊息即可
        return f"（AI 解釋暫時無法使用：{e}）"


# ========== (2) 文字前處理 ==========
def _normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    trans = str.maketrans({
        "Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D",
        "（": "(", "）": ")", "．": ".", "、": ".", "：": ":", "；": ";"
    })
    s = s.translate(trans)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_question_and_options(raw_text: str):
    """
    當題目本身有 A. B. C. D. 時，從一行裡拆出來
    """
    s = _normalize_text(raw_text)
    token = r"(?:\(|（)?([A-D])(?:\)|）)?[\.、]"
    marks = list(re.finditer(token, s))
    if len(marks) < 4:
        return raw_text.strip(), []

    q = s[:marks[0].start()].strip()

    def seg(i, j):
        return s[marks[i].end(): marks[j].start()].lstrip(" ;").strip()

    A = seg(0, 1)
    B = seg(1, 2)
    C = seg(2, 3)
    D = s[marks[3].end():].lstrip(" ;").strip()
    return q, [A, B, C, D]


# ========== (3) 題庫欄位 → 選項 自動偵測 ==========
def extract_options(row: pd.Series):
    """
    依序嘗試多種可能的欄位名稱
    你的題庫是「選項一～選項四」，這裡有放進來
    """
    possible_sets = [
        ["A", "B", "C", "D"],
        ["選項A", "選項B", "選項C", "選項D"],
        ["選項一", "選項二", "選項三", "選項四"],
        ["1", "2", "3", "4"],
        ["option1", "option2", "option3", "option4"],
    ]
    for cols in possible_sets:
        opts = []
        for c in cols:
            val = row.get(c, "")
            if pd.notna(val) and str(val).strip():
                opts.append(str(val).strip())
        if len(opts) >= 2:
            return opts
    return []


# ========== (4) Markdown 會吃掉 * 或 _ → 先跳脫 ==========
def escape_markdown(s: str) -> str:
    """移除或跳脫 Markdown 符號，確保 radio 顯示正常"""
    if not isinstance(s, str):
        return ""
    # 若開頭就是 * ，則移除，不做跳脫
    s = re.sub(r"^\*+", "", s.strip())
    # 中間若有 Markdown 特殊符號則跳脫
    s = s.replace("*", "\\*")
    s = s.replace("_", "\\_")
    s = s.replace("`", "\\`")
    s = s.replace("#", "\\#")
    s = s.replace("-", "\\-")
    s = s.replace(">", "\\>")
    s = s.replace("|", "\\|")
    return s.strip()



# ========== (5) 練習模式題目渲染 ==========
def render_practice_question(qid: str, question: str, options: list, correct_answer: str, row=None):
    """
    題目 + 「看不懂題目嗎？」按鈕 + 選項 + 對答案 + 下一題
    """

    # 1. 若 options 沒資料，試著從這一列(row)抓
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        options = extract_options(row)

    # 2. 若還是沒有，試著從題目文字裡解析
    if not options:
        parsed_q, parsed_opts = parse_question_and_options(question)
        if parsed_opts:
            question, options = parsed_q, parsed_opts

    # 3. 題目
    st.markdown("### 🧠 **題目：**")
    st.write(question)

    # 4. AI 解釋按鈕（不強制，點了才跑）
    if st.button("🧠 看不懂題目嗎？", key=f"exp_{qid}"):
        with st.spinner("AI 助教說明中..."):
            msg = ai_explain_question(question)
            st.markdown("### 💬 AI 解釋：")
            st.write(msg)

    # 5. 顯示選項
    if not options:
        st.warning("⚠️ 無法取得選項，請檢查題庫欄位（例如『選項一～選項四』或『A～D』）。")
        return

    # 跳脫 markdown，再組成 radio
    display_options = [f"{chr(65+i)}. {escape_markdown(opt)}" for i, opt in enumerate(options)]

    sel_key = f"radio_{qid}"
    ans_flag = f"{qid}_answered"
    sel_store = f"{qid}_selected"

    if ans_flag not in st.session_state:
        st.session_state[ans_flag] = False
    if sel_store not in st.session_state:
        st.session_state[sel_store] = None

    picked = st.radio(
        label="",
        options=display_options,
        index=None,
        key=sel_key,
    )

    if picked:
        # 只存 A/B/C/D
        st.session_state[sel_store] = picked[0]

    # 6. 對答案 & 下一題
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
                st.session_state.setdefault("results", []).append({
                    "題號": qid,
                    "題目": question,
                    "你的答案": chosen,
                    "正確答案": correct_answer,
                })
            # 換下一題
            st.session_state["current_q"] = st.session_state.get("current_q", 0) + 1
            # 重置「已對答案」狀態
            st.session_state[ans_flag] = False
            st.rerun()

    # 7. 顯示對答案結果
    if st.session_state.get(ans_flag):
        chosen = st.session_state.get(sel_store)
        if chosen == correct_answer:
            st.success(f"✅ 答對了！正確答案：{correct_answer}")
        else:
            st.error(f"❌ 答錯了！正確答案：{correct_answer}")
