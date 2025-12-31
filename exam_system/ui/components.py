import streamlit as st
from services.ai_client import get_ai_hint

def render_question_card(row: dict, index: int, mode="practice", user_ans=None):
    """
    通用題目卡片
    mode: 'practice' (練習模式), 'exam' (模擬考作答), 'review' (復盤)
    """
    qid = f"{mode}_{row['ID']}"
    question_text = row['Question']
    correct = row['Answer']
    explanation = row.get('Explanation', '')

    st.markdown(f"### Q{index+1}. {question_text}")
    
    # 準備選項 Dict
    options = {}
    for code in ["A", "B", "C", "D"]:
        val = row.get(f"Option{code}")
        if val:
            options[code] = val

    # === 模式 A: 練習模式 (即時回饋) ===
    if mode == "practice":
        # 使用 radio 顯示選項
        choice_list = [f"{k}. {v}" for k, v in options.items()]
        selected = st.radio("請作答：", choice_list, index=None, key=qid)
        
        if selected:
            sel_code = selected.split(".")[0]
            if sel_code == correct:
                st.success("✅ 答對了！")
            else:
                st.error(f"❌ 答錯了，正確答案是 {correct}")
            
            # AI 按鈕
            if st.button("🤖 AI 詳解", key=f"ai_{qid}"):
                with st.spinner("AI 分析中..."):
                    hint = get_ai_hint(question_text, options, correct, explanation)
                    st.info(hint)

    # === 模式 B: 模擬考作答 (無回饋) ===
    elif mode == "exam":
        choice_list = [f"{k}. {v}" for k, v in options.items()]
        # 嘗試還原使用者之前的選擇
        prev_idx = None
        if user_ans:
            # 找出 user_ans 在 list 中的 index
            for i, c_str in enumerate(choice_list):
                if c_str.startswith(f"{user_ans}."):
                    prev_idx = i
                    break
        
        selected = st.radio(
            "選擇答案：", 
            choice_list, 
            index=prev_idx, 
            key=qid
        )
        # 回傳選擇代號 (A, B...) 供外部儲存
        return selected.split(".")[0] if selected else None

    # === 模式 C: 復盤 (顯示對錯與詳解) ===
    elif mode == "review":
        st.markdown("---")
        for code, text in options.items():
            prefix = ""
            color = "black"
            weight = "normal"
            
            if code == correct:
                prefix = "✅ "
                color = "green"
                weight = "bold"
            elif code == user_ans and code != correct:
                prefix = "❌ (你的答案) "
                color = "red"
                weight = "bold"
            elif code == user_ans:
                prefix = "(你的答案) "
            
            st.markdown(f"<span style='color:{color}; font-weight:{weight}'>{prefix}{code}. {text}</span>", unsafe_allow_html=True)
            
        with st.expander(f"📖 查看詳解 ({correct})"):
            st.write(f"**官方詳解**：{explanation}")
            if st.button("🤖 AI 深度解析", key=f"rev_ai_{qid}"):
                with st.spinner("AI 分析中..."):
                    hint = get_ai_hint(question_text, options, correct, explanation)
                    st.write(hint)
