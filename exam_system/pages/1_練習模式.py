import streamlit as st
from services.db_client import load_all_banks, list_chapters
from ui.layout import render_header
from ui.components import render_question_card

st.set_page_config(page_title="練習模式", layout="wide")
render_header("🧠 練習模式", "單題練習、即時回饋")

# 1. 載入題庫
all_banks = load_all_banks()
if not all_banks:
    st.warning("⚠️ 尚未偵測到題庫，請檢查 bank/ 資料夾。")
    st.stop()

# 2. Sidebar 選單
with st.sidebar:
    st.header("設定")
    domain = st.selectbox("選擇分類", list(all_banks.keys()))
    df = all_banks[domain]
    
    chapters = list_chapters(df)
    chapter = st.selectbox("選擇章節", ["全部"] + chapters)
    
    if st.button("🔄 重置題目"):
        st.session_state.pop("practice_df", None)
        st.rerun()

# 3. 題目狀態管理
if "practice_df" not in st.session_state:
    # 篩選題目
    target_df = df if chapter == "全部" else df[df["Chapter"] == chapter]
    # 隨機取 50 題
    st.session_state.practice_df = target_df.sample(n=min(50, len(target_df))).reset_index(drop=True)
    st.session_state.p_index = 0

current_df = st.session_state.practice_df
idx = st.session_state.p_index

if current_df.empty:
    st.info("此章節無題目。")
    st.stop()

# 4. 顯示題目
row = current_df.iloc[idx].to_dict()
render_question_card(row, idx, mode="practice")

# 5. 翻頁按鈕
c1, c2, c3 = st.columns([1, 1, 4])
with c1:
    if st.button("⬅️ 上一題") and idx > 0:
        st.session_state.p_index -= 1
        st.rerun()
with c2:
    if st.button("下一題 ➡️") and idx < len(current_df) - 1:
        st.session_state.p_index += 1
        st.rerun()

st.caption(f"進度：{idx + 1} / {len(current_df)}")
