"""
模擬考模式 - 完整考試，時間限制
"""
import os
import sys

# 確保能導入 exam_system 模組
if __name__ == "__main__":
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

import streamlit as st
import time

from exam_system.config import settings
from exam_system.ui.layout import setup_page, show_header
from exam_system.ui.exam_render import (
    setup_sidebar_config,
    create_paper,
    render_exam_questions,
    render_results_page
)

# 設定頁面
setup_page("模擬考模式")

# 顯示標題
show_header()

st.warning("⏱️ **模擬考模式**：完整模擬考試，作答時無提示，交卷後統一查看成績")

# 側邊欄設定
sidebar_config = setup_sidebar_config(mode="exam")

# 初始化考試狀態
if "exam_paper" not in st.session_state:
    st.session_state.exam_paper = None
if "exam_start_time" not in st.session_state:
    st.session_state.exam_start_time = None
if "exam_answers" not in st.session_state:
    st.session_state.exam_answers = {}
if "exam_submitted" not in st.session_state:
    st.session_state.exam_submitted = False
if "exam_results" not in st.session_state:
    st.session_state.exam_results = None

# 開始按鈕
if sidebar_config.get("start_button"):
    filtered_bank = sidebar_config["filtered_bank"]
    paper = create_paper(
        filtered_bank,
        sidebar_config["num_questions"],
        sidebar_config["shuffle_options"],
        sidebar_config["random_order"]
    )
    
    st.session_state.exam_paper = paper
    st.session_state.exam_start_time = time.time()
    st.session_state.exam_answers = {}
    st.session_state.exam_submitted = False
    st.session_state.exam_results = None
    st.rerun()

# 考試中
if st.session_state.exam_paper and not st.session_state.exam_submitted:
    paper = st.session_state.exam_paper
    time_limit = sidebar_config.get("time_limit", 0)
    
    # 顯示剩餘時間
    if time_limit > 0:
        elapsed = int(time.time() - st.session_state.exam_start_time)
        remaining = max(0, time_limit - elapsed)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            mm, ss = divmod(remaining, 60)
            st.metric("剩餘時間", f"{mm:02d}:{ss:02d}")
            
            if remaining == 0:
                st.error("⏰ 時間到！請交卷")
    
    # 渲染所有題目
    answers = render_exam_questions(
        paper,
        sidebar_config.get("show_image", True)
    )
    
    st.session_state.exam_answers = answers
    
    # 交卷按鈕
    submitted = st.button("📥 交卷並查看成績", type="primary", use_container_width=True)
    time_up = time_limit > 0 and (time.time() - st.session_state.exam_start_time) >= time_limit
    
    if submitted or time_up:
        # 計算成績
        results = []
        correct_count = 0
        
        for q in paper:
            gold = set(q["Answer"])
            user = st.session_state.exam_answers.get(q["ID"], set())
            is_correct = (user == gold)
            
            if is_correct:
                correct_count += 1
            
            results.append({
                "question": q,
                "user_answer": user,
                "correct_answer": gold,
                "is_correct": is_correct
            })
        
        st.session_state.exam_results = {
            "results": results,
            "correct_count": correct_count,
            "total": len(paper),
            "score": round(100 * correct_count / len(paper), 2) if len(paper) > 0 else 0
        }
        st.session_state.exam_submitted = True
        st.rerun()

# 顯示成績
elif st.session_state.exam_submitted and st.session_state.exam_results:
    render_results_page(
        st.session_state.exam_results,
        mode="exam"
    )
    
    # 重新考試
    if st.button("🔁 重新考試", type="secondary"):
        st.session_state.exam_paper = None
        st.session_state.exam_start_time = None
        st.session_state.exam_answers = {}
        st.session_state.exam_submitted = False
        st.session_state.exam_results = None
        st.rerun()

else:
    st.info("👈 請在左側邊欄設定並點擊「🚀 開始考試」")
