import streamlit as st
import re
import pandas as pd

# ========== (1) AI 題目解釋 ==========
def ai_explain_question(question: str):
    """
    若有 GEMINI_API_KEY 才呼叫，沒有就回傳友善提示。
    你之後要換成 Ollama / OpenAI 只要改這裡就好。
    """
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ 目前未設定 AI 金鑰，無法產生題目解釋。\n請在 .streamlit/secrets.toml 加上 GEMINI_API_KEY。"

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
        return f"（AI 解釋暫時無法使用：{e}）"


# ========== (2) 文字清理 ==========
def _normalize_text(s: str) -> str:
    """統一中英文字型、移除控制符號與多餘空白"""
    if not isinstance(s, str):
        return ""
    # 全形轉半形
    def to_halfwidth(txt):
        result = ""
        for char in txt:
            code = ord(char)
            if code == 0x3000:
                code = 32
            elif 0xFF01 <= code <= 0xFF5E:
                code -= 0xFEE0
            result += chr(code)
        return result

    s = to_halfwidth(s)
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
    s = s.replace("（", "(").replace("）", ")").replace("．", ".").replace("、", ".")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def escape_markdown(s: str) -> str:
    """清除或跳脫特殊符號，防止選項殘留 *、全形＊ 等干擾符號"""
    if not isinstance(s, str):
        return ""
    s = _normalize_text(s)
    s = re.sub(r"^[\*\＊]+", "", s)
    s = s.replace("＊", "").replace("*", "")
    s = s.strip(" .:")
    return s.strip()


# ========== (3) 題目/選項解析 ==========
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


# ========== (4) 自動擷取選項欄位 ==========
def extract_options(row: pd.Series):
    """
    依序嘗試多種欄位名稱
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


# ========== (5) 練習模式題目渲染 ==========
def render_practice_question(qid: str, question: str, options: list, correct_answer: str, row=None):
    """
    題目 + AI提示 + 選項 + 對答案 + 下一題
    """
    # 1. 若 options 沒資料，試著從 row 抓
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        options = extract_options(row)

    # 2. 若還是沒有，從題目中拆
    if not options:
        parsed_q, parsed_opts = parse_question_and_options(question)
        if parsed_opts:
            question, options = parsed_q, parsed_opts

    # 題目
    st.markdown("### 🧠 **題目：**")
    st.write(question)

    # 「看不懂題目嗎？」按鈕
    if st.button("🧠 看不懂題目嗎？", key=f"exp_{qid}"):
        with st.spinner("AI 助教說明中..."):
            msg = ai_explain_question(question)
            st.markdown("### 💬 AI 解釋：")
            st.write(msg)

    # 若沒有選項
    if not options:
        st.warning("⚠️ 無法取得選項，請檢查題庫欄位。")
        return

    # 準備選項顯示
    display_options = [f"{chr(65+i)}. {escape_markdown(opt)}" for i, opt in enumerate(options)]

    # session 狀態
    sel_key = f"radio_{qid}"
    sel_store = f"{qid}_selected"
    if sel_store not in st.session_state:
        st.session_state[sel_store] = None

    picked = st.radio("", display_options, index=None, key=sel_key)
    if picked:
        st.session_state[sel_store] = picked[0]  # 僅存 A/B/C/D

    # 按鈕列
    col1, col2 = st.columns(2)
    with col1:
        check = st.button("✅ 對答案", key=f"check_{qid}")
    with col2:
        next_q = st.button("➡️ 下一題", key=f"next_{qid}")

    # 顯示結果
    if check:
        selected = st.session_state.get(sel_store)
        if not selected:
            st.warning("請先選擇一個答案！")
        elif selected == correct_answer:
            st.success("🎯 答對了！")
        else:
            correct_text = ""
            if row is not None and f"選項{correct_answer}" in row:
                correct_text = row[f"選項{correct_answer}"]
            elif len(options) >= 4:
                try:
                    # 若答案是 A/B/C/D
                    if correct_answer.upper() in ["A", "B", "C", "D"]:
                        idx = ord(correct_answer.upper()) - 65
                    # 若答案是數字 1~4
                    elif correct_answer.strip().isdigit():
                        idx = int(correct_answer.strip()) - 1
                    else:
                        idx = 0
                    correct_text = options[idx] if idx < len(options) else ""
            except Exception:
                    correct_text = ""


    # 下一題
    if next_q:
        st.session_state["current_q"] = st.session_state.get("current_q", 0) + 1
        st.rerun()
