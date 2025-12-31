import streamlit as st
import time
from services.db_client import load_all_banks
from ui.layout import render_header
from ui.components import render_question_card

st.set_page_config(page_title="模擬考模式", layout="wide")

# 狀態機：setup (設定) -> exam (考試中) -> review (結果)
if "exam_stage" not in st.session_state:
    st.session_state.exam_stage = "setup"
    st.session_state.exam_answers = {}
    st.session_state.exam_paper = None

# === 階段 1: 設定 ===
if st.session_state.exam_stage == "setup":
    render_header("📝 模擬考模式", "仿真計時、交卷後顯示成績")
    
    all_banks = load_all_banks()
    if not all_banks:
        st.warning("無題庫資料")
        st.stop()
        
    c1, c2 = st.columns(2)
    with c1:
        domain = st.selectbox("選擇科目", list(all_banks.keys()))
    with c2:
        num = st.number_input("題數", 10, 100, 20)
        
    if st.button("🚀 開始考試", type="primary"):
        df = all_banks[domain]
        # 抽題
        st.session_state.exam_paper = df.sample(n=min(num, len(df))).reset_index(drop=True)
        st.session_state.exam_answers = {}
        st.session_state.start_time = time.time()
        st.session_state.exam_stage = "exam"
        st.rerun()

# === 階段 2: 考試中 ===
elif st.session_state.exam_stage == "exam":
    st.title("📝 考試進行中...")
    
    # 計時顯示
    elapsed = int(time.time() - st.session_state.start_time)
    mins, secs = divmod(elapsed, 60)
    st.sidebar.metric("⏳ 已用時間", f"{mins:02d}:{secs:02d}")
    
    if st.sidebar.button("放棄/重來"):
        st.session_state.exam_stage = "setup"
        st.rerun()

    paper = st.session_state.exam_paper
    
    # 顯示所有題目
    for idx, row in paper.iterrows():
        qid = row['ID']
        # 取得之前的答案
        prev_ans = st.session_state.exam_answers.get(qid)
        
        # 呼叫元件並接收回傳值
        user_choice = render_question_card(row.to_dict(), idx, mode="exam", user_ans=prev_ans)
        
        # 紀錄答案
        if user_choice:
            st.session_state.exam_answers[qid] = user_choice
        
        st.divider()
        
    if st.button("📥 交卷", type="primary"):
        st.session_state.exam_stage = "review"
        st.rerun()

# === 階段 3: 結果與復盤 ===
elif st.session_state.exam_stage == "review":
    render_header("📊 考試結果")
    
    paper = st.session_state.exam_paper
    answers = st.session_state.exam_answers
    
    # 計算成績
    correct_count = 0
    for idx, row in paper.iterrows():
        if answers.get(row['ID']) == row['Answer']:
            correct_count += 1
            
    score = int((correct_count / len(paper)) * 100)
    st.metric("最終成績", f"{score} 分", f"答對 {correct_count} / {len(paper)}")
    
    st.subheader("詳細檢討")
    for idx, row in paper.iterrows():
        user_ans = answers.get(row['ID'])
        render_question_card(row.to_dict(), idx, mode="review", user_ans=user_ans)
        
    if st.button("🔄 再考一次"):
        st.session_state.exam_stage = "setup"
        st.rerun()
