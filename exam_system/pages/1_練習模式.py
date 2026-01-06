"""
練習模式 - 逐題作答，即時反饋
"""
import os
import sys

# 確保能導入 exam_system 模組
if __name__ == "__main__":
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

import streamlit as st
import random

from exam_system.config import settings
from exam_system.ui.layout import setup_page, show_header
from exam_system.ui.exam_render import (
    setup_sidebar_config,
    create_paper,
    render_practice_question
)
from exam_system.services.gemini_client import gemini_service

# 設定頁面
setup_page("練習模式")

# 顯示標題
show_header()

st.info("📝 **練習模式**：逐題作答，可查看 AI 提示，答對立即反饋")

# 側邊欄設定
sidebar_config = setup_sidebar_config(mode="practice")

# 初始化練習狀態
if "practice_paper" not in st.session_state:
    st.session_state.practice_paper = None
if "practice_idx" not in st.session_state:
    st.session_state.practice_idx = 0
if "practice_correct" not in st.session_state:
    st.session_state.practice_correct = 0
if "practice_answers" not in st.session_state:
    st.session_state.practice_answers = {}

# 開始按鈕
if sidebar_config.get("start_button"):
    filtered_bank = sidebar_config["filtered_bank"]
    paper = create_paper(
        filtered_bank,
        sidebar_config["num_questions"],
        sidebar_config["shuffle_options"],
        sidebar_config["random_order"]
    )
    
    st.session_state.practice_paper = paper
    st.session_state.practice_idx = 0
    st.session_state.practice_correct = 0
    st.session_state.practice_answers = {}
    st.rerun()

# 顯示練習題目
if st.session_state.practice_paper:
    paper = st.session_state.practice_paper
    idx = st.session_state.practice_idx
    
    if idx < len(paper):
        question = paper[idx]
        
        # 渲染題目
        result = render_practice_question(
            question,
            idx,
            len(paper),
            sidebar_config.get("show_image", True)
        )
        
        # 處理提交
        if result["submitted"]:
            is_correct = result["is_correct"]
            
            if is_correct:
                st.success("✅ 答對了！")
                st.session_state.practice_correct += 1
            else:
                st.error(f"❌ 答錯了。正確答案：{result['correct_answer']}")
                if result.get("explanation"):
                    st.caption(f"📖 題庫詳解：{result['explanation']}")
            
            st.session_state.practice_answers[question["ID"]] = result["user_answer"]
        
        # 下一題 / 完成
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if idx < len(paper) - 1:
                if st.button("➡️ 下一題", key=f"next_{idx}", use_container_width=True):
                    st.session_state.practice_idx += 1
                    st.rerun()
            else:
                st.success(f"🎉 練習完成！答對：{st.session_state.practice_correct}/{len(paper)}")
        
        with col2:
            if st.button("🔁 重新練習", key=f"restart_{idx}", use_container_width=True):
                st.session_state.practice_paper = None
                st.session_state.practice_idx = 0
                st.session_state.practice_correct = 0
                st.session_state.practice_answers = {}
                st.rerun()
        
        with col3:
            if st.button("📊 查看統計", key=f"stats_{idx}", use_container_width=True):
                st.session_state.practice_show_stats = True
                st.rerun()
    
    # 顯示統計
    if st.session_state.get("practice_show_stats"):
        st.divider()
        st.subheader("📊 練習統計")
        
        total = len(st.session_state.practice_answers)
        correct = st.session_state.practice_correct
        accuracy = (correct / total * 100) if total > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("已答題數", total)
        with col2:
            st.metric("答對題數", correct)
        with col3:
            st.metric("正確率", f"{accuracy:.1f}%")

else:
    st.info("👈 請在左側邊欄設定並點擊「🚀 開始練習」")
