import streamlit as st
import re
import pandas as pd

# ========== 1. AI 題目解釋 ==========
def ai_explain_question(question: str):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ 尚未設定 GEMINI_API_KEY，無法產生 AI 解釋。"

    try:
        import google.generativeai as genai
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
你是一位保險相關考照的輔導老師，請用考生聽得懂的方式解釋這一題「在問什麼」、關鍵字是什麼，不要直接講正確選項。

題目：
{question}
"""
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        return f"（AI 解釋暫時無法使用：{e}）"


# ========== 2. 通用文字處理 ==========
def _normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # 全形轉半形
    out = []
    for ch in s:
        code = ord(ch)
        if code == 0x3000:
            code = 32
        elif 0xFF01 <= code <= 0xFF5E:
            code -= 0xFEE0
        out.append(chr(code))
    s = "".join(out)
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def clean_answer(ans: str) -> str:
    """把答案變成純 A/B/C/D 或數字"""
    if not isinstance(ans, str):
        return ""
    s = _normalize_text(ans).upper()
    # 移除括號、點、冒號
    s = re.sub(r"[\(\)（）\.\:：]", "", s)
    # 只留 A-D 或數字
    s = re.sub(r"[^A-D0-9]", "", s)
    return s.strip()


# ========== 3. 題幹裡拆出選項（當題目自己有 A. B. C. D.） ==========
def parse_question_and_options(raw_text: str):
    s = _normalize_text(raw_text)
    token = r"(?:\(|（)?([A-D])(?:\)|）)?[\.、]"
    marks = list(re.finditer(token, s))
    if len(marks) < 2:
        return raw_text.strip(), []

    question = s[:marks[0].start()].strip()
    opts = []
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(s)
        opt_txt = s[start:end].strip(" ．。 ")
        opts.append(opt_txt)
    return question, opts[:4]


# ========== 4. 從 DataFrame 這一列抓選項 ==========
def extract_options(row: pd.Series):
    candidate_sets = [
        ["A", "B", "C", "D"],
        ["選項A", "選項B", "選項C", "選項D"],
        ["選項一", "選項二", "選項三", "選項四"],
        ["1", "2", "3", "4"],
    ]
    for cols in candidate_sets:
        opts = []
        for c in cols:
            val = row.get(c, "")
            if pd.notna(val) and str(val).strip():
                opts.append(str(val).strip())
        if len(opts) >= 2:
            return opts
    return []


# ========== 5. 幫你從 row 裡找「正確答案的文字」 ==========
def get_correct_option_text_from_row(row: pd.Series, correct_letter: str) -> str:
    """
    專門解你現在這一題的問題：答錯的時候沒有顯示「B. xxx」
    這邊我把你可能會用到的欄位都列進來，一一嘗試。
    """
    if not correct_letter:
        return ""

    correct_letter = clean_answer(correct_letter)  # 轉成 A/B/C/D

    # 1) 題庫如果是 A/B/C/D 這四欄
    abcd_map = {
        "A": ["A", "選項A", "選項一", "1"],
        "B": ["B", "選項B", "選項二", "2"],
        "C": ["C", "選項C", "選項三", "3"],
        "D": ["D", "選項D", "選項四", "4"],
    }
    if isinstance(row, pd.Series):
        for col_name in abcd_map.get(correct_letter, []):
            if col_name in row and pd.notna(row[col_name]) and str(row[col_name]).strip():
                return str(row[col_name]).strip()

        # 有些人會這樣存：選項A內容, 選項B內容...
        # 你目前的樣子比較像前面那一種，所以這段先放著

    return ""


# ========== 6. 主 UI：練習題 ==========
def render_practice_question(qid: str, question: str, options: list, correct_answer: str, row: pd.Series = None):
    """
    qid            題號（用來組 key）
    question       題目文字
    options        題目選項（list），可能是空的 → 我們會自己抓
    correct_answer 題庫給的正確答案，可能是 A / (A) / 1
    row            原始那一列資料，拿來找「正確答案的文字」「詳解」
    """
    # --- 1. 沒有選項 → 試著從 row 抓
    if (not options or all(o == "" for o in options)) and isinstance(row, pd.Series):
        options = extract_options(row)

    # --- 2. 還是沒有 → 試著從題幹拆 A. B. C. D.
    if not options:
        q2, parsed = parse_question_and_options(question)
        if parsed:
            question, options = q2, parsed

    # --- 3. 題目 ---
    st.markdown("### 🧠 題目：")
    st.write(question)

    # --- 4. AI 解釋按鈕 ---
    if st.button("🧠 看不懂題目嗎？", key=f"exp_{qid}"):
        with st.spinner("AI 助教說明中..."):
            st.markdown("### 💬 AI 解釋：")
            st.write(ai_explain_question(question))

    # --- 5. 顯示選項 (radio) ---
    if not options:
        st.warning("⚠️ 無法取得選項，請檢查題庫欄位。")
        return

    display_options = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)]

    radio_key = f"radio_{qid}"
    picked = st.radio(label="", options=display_options, index=None, key=radio_key)

    # radio 回傳的是 "A. xxx" → 我只留 A
    selected_letter = ""
    if picked:
        selected_letter = clean_answer(picked[0])

    # --- 6. 按鈕區 ---
    c1, c2 = st.columns(2)
    with c1:
        check_btn = st.button("✅ 對答案", key=f"check_{qid}")
    with c2:
        next_btn = st.button("➡️ 下一題", key=f"next_{qid}")

    # --- 7. 清理正確答案 ---
    correct_letter = clean_answer(correct_answer)

    # --- 8. 對答案 ---
    if check_btn:
        if not selected_letter:
            st.warning("請先選一個選項喔～")
        else:
            if selected_letter == correct_letter:
                st.success("🎯 答對了！")
            else:
                # 先試著從 row 找出正確答案的文字
                correct_text = get_correct_option_text_from_row(row, correct_letter)

                # 再不行就 fallback 用 options 陣列找
                if not correct_text:
                    try:
                        idx = ord(correct_letter) - 65  # A → 0
                        if 0 <= idx < len(options):
                            correct_text = options[idx]
                    except Exception:
                        correct_text = ""

                if correct_text:
                    st.error(f"❌ 答錯了！ 👉 正確答案：{correct_letter}. {correct_text}")
                else:
                    st.error(f"❌ 答錯了！ 👉 正確答案：{correct_letter}")

                # 有「詳解」就秀出來
                if isinstance(row, pd.Series):
                    for col in ["詳解", "解析", "說明"]:
                        if col in row and pd.notna(row[col]) and str(row[col]).strip():
                            st.info(f"📘 題目解析：{row[col]}")
                            break

    # --- 9. 下一題 ---
    if next_btn:
        st.session_state["current_q"] = st.session_state.get("current_q", 0) + 1
        st.rerun()
