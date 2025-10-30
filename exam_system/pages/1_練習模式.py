import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from services.ai_client import get_ai_hint
st.set_page_config(page_title="練習模式", layout="wide")

st.title("🧠 練習模式")

# === 選擇題庫 ===
@st.cache_data
def load_question_bank(domain):
    file_map = {
        "人身": "bank/life.csv",
        "外幣": "bank/fx.csv",
        "投資型": "bank/invest.csv"
    }
    df = pd.read_csv(file_map[domain])
    df = df.dropna(subset=["題目", "答案"])
    return df

domain = st.selectbox("請選擇題庫領域：", ["人身", "外幣", "投資型"])
num_questions = st.number_input("請選擇要練習的題數：", min_value=1, max_value=50, value=5, step=1)

if st.button("開始練習"):
    st.session_state.current_q = 0
    st.session_state.questions = load_question_bank(domain).sample(num_questions).to_dict(orient="records")
    st.session_state.finished = False

if "questions" in st.session_state and not st.session_state.get("finished", False):
    q_list = st.session_state.questions
    q_index = st.session_state.current_q
    q_data = q_list[q_index]

    st.markdown(f"### 🧩 題目 {q_index+1} / {len(q_list)}")
    st.markdown(f"**{q_data['題目']}**")

    options = [q_data[c] for c in ["A", "B", "C", "D"] if c in q_data and pd.notna(q_data[c])]
    correct_answer = str(q_data["答案"]).strip().upper()

    user_choice = st.radio("請選擇答案：", options, key=f"q_{q_index}")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("對答案", key=f"check_{q_index}"):
            if not user_choice:
                st.warning("請先選擇答案")
            else:
                selected_letter = user_choice[0].upper()  # 取選項開頭字母比對
                if selected_letter == correct_answer:
                    st.success("✅ 答對了！")
                else:
                    st.error(f"❌ 答錯了！ 正確答案：{correct_answer}")

    with col2:
        if st.button("看不懂題目嗎？", key=f"hint_{q_index}"):
            hint = get_ai_hint(q_data["題目"], domain)
            st.info(hint or "AI 提示暫無法提供")

    if st.button("➡️ 下一題", key=f"next_{q_index}"):
        if q_index + 1 < len(q_list):
            st.session_state.current_q += 1
            st.rerun()
        else:
            st.session_state.finished = True
            st.success("🎉 所有題目已完成練習！")

elif "finished" in st.session_state and st.session_state.finished:
    st.success("✅ 練習結束，請回上方重新選擇題庫以再練一次。")
