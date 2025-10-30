import streamlit as st
import re
import pandas as pd


# ========== (1) AI 題目解釋 ==========
def ai_explain_question(question: str):
    """若有 GEMINI_API_KEY 才呼叫，沒有就回傳提示"""
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ 未設定 GEMINI_API_KEY，無法使用 AI 解釋功能。"

    try:
        import google.generativeai as genai
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
你是一位保險相關考照的輔導老師，請清楚解釋題意、關鍵字與考點，不要直接給答案。
題目：
{question}
"""
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        return f"（AI 解釋暫時無法使用：{e}）"


# ========== (2) 文字標準化 ==========
def _normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
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
    if not isinstance(s, str):
        return ""
    s = _normalize_text(s)
    s = re.sub(r"^[\*\＊]+", "", s)
    s = s.replace("＊", "").replace("*", "").strip(" .:")
    return s.strip()


# ========== (3) 題目與選項自動解析 ==========
def parse_question_and_options(raw_text: str):
    """從題目文字中自動拆出 A. B. C. D."""
    s = _normalize_text(raw_text)
    token = r"(?:\(|（)?([A-D])(?:\)|）)?[\.、]"
    marks = list(re.finditer(token, s))
    if len(marks) < 2:
        return raw_text.strip(), []

    q = s[:marks[0].start()].strip()

    def seg(i, j):
        return s[marks[i].end(): marks[j].start()].strip(" ；: ")
    opts = []
    for i in range(len(marks)):
        start = marks[i].end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(s)
        opt = s[start:end].strip(" ;．。 ")
        opts.append(opt)
    return q, opts[:4]


# ========== (4) 從資料列擷取選項 ==========
def extract_options(row: pd.Series):
    possible_sets = [
        ["A", "B", "C", "D"],
        ["選項A", "選項B", "選項C", "選項D"],
        ["選項一", "選項二", "選項三", "選項四"],
        ["1", "2", "3", "4"],
    ]
    for cols in possible_sets:
        opts = [str(row.get(c, "")).strip() for c in cols if pd.notna(row.get(c, ""))]
        if len(opts) >= 2:
            return opts
    return []


# ========== (5) 顯示練習題 ==========
def render_practice_question(qid: str, question: str, options: list, correct_answer: str, row=None):
    """題目 + 選項 + 對答案 + 下一題 + AI 解釋 + 詳解"""
    # 自動補選項
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        options = extract_options(row)
    if not options:
        parsed_q, parsed_opts = parse_question_and_options(question)
        if parsed_opts:
            question, options = parsed_q, parsed_opts

    # 顯示題目
    st.markdown("### 🧠 **題目：**")
    st.write(question)

    # AI 提示按鈕
    if st.button("🧠 看不懂題目嗎？", key=f"exp_{qid}"):
        with st.spinner("AI 助教說明中..."):
            st.markdown("### 💬 AI 解釋：")
            st.write(ai_explain_question(question))

    # 沒選項就警告
    if not options:
        st.warning("⚠️ 無法取得選項，請檢查題庫格式。")
        return

    # 顯示選項
    display_options = [f"{chr(65+i)}. {escape_markdown(opt)}" for i, opt in enumerate(options)]
    sel_key = f"radio_{qid}"
    sel_store = f"{qid}_selected"
    if sel_store not in st.session_state:
        st.session_state[sel_store] = None

    picked = st.radio("", display_options, index=None, key=sel_key)
    if picked:
        st.session_state[sel_store] = picked[0]

    col1, col2 = st.columns(2)
    with col1:
        check = st.button("✅ 對答案", key=f"check_{qid}")
    with col2:
        next_q = st.button("➡️ 下一題", key=f"next_{qid}")

    # 對答案邏輯
    if check:
        selected = st.session_state.get(sel_store)
        if not selected:
            st.warning("請先選擇一個答案！")
        elif selected == correct_answer:
            st.success("🎯 答對了！")
        else:
            # ========== 正確答案顯示 ==========
            correct_text = ""

            # (1) 從 row 中找
            if row is not None:
                col_name = f"選項{correct_answer}"
                if col_name in row and pd.notna(row[col_name]):
                    correct_text = str(row[col_name]).strip()
                else:
                    mapping = {"A": "選項一", "B": "選項二", "C": "選項三", "D": "選項四"}
                    alt_col = mapping.get(correct_answer.upper())
                    if alt_col and alt_col in row and pd.notna(row[alt_col]):
                        correct_text = str(row[alt_col]).strip()

            # (2) 從畫面 options 拿
            if not correct_text and options:
                try:
                    ans = correct_answer.strip().upper()
                    if ans in ["A", "B", "C", "D"]:
                        idx = ord(ans) - 65
                    elif ans.isdigit():
                        idx = int(ans) - 1
                    else:
                        idx = 0
                    if 0 <= idx < len(options):
                        correct_text = options[idx]
                except Exception:
                    correct_text = ""

            # (3) 顯示錯題訊息
            if correct_text:
                st.error(f"❌ 答錯了！👉 正確答案：{correct_answer}. {correct_text}")
            else:
                st.error(f"❌ 答錯了！👉 正確答案：{correct_answer}")

            # (4) 顯示詳解
            if row is not None:
                for explain_col in ["詳解", "解析", "說明"]:
                    if explain_col in row and pd.notna(row[explain_col]):
                        st.info(f"📘 題目解析：{row[explain_col]}")
                        break

    # 下一題
    if next_q:
        st.session_state["current_q"] = st.session_state.get("current_q", 0) + 1
        st.rerun()
