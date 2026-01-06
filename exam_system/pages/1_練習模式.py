import sys
import os

# 顯示當前工作目錄
print("Current Working Directory:", os.getcwd())
# 顯示 Python 搜尋路徑
print("System Path:", sys.path)


# exam_system/pages/1_練習模式.py
import streamlit as st
import time
from exam_system.ui import layout, exam_render

layout.setup_page("練習模式")

# Sidebar
config = layout.render_sidebar_settings()

if config["start"]:
    st.session_state.paper = exam_render.sample_paper(
        config["df"], 
        config["num_q"], 
        config["random_q"], 
        config["shuffle_opt"]
    )
    # Reset practice state
    st.session_state.practice_idx = 0
    st.session_state.practice_correct = 0
    st.session_state.mode = "practice"
    st.rerun()

if st.session_state.get("mode") == "practice" and st.session_state.get("paper"):
    exam_render.render_practice_mode(
        st.session_state.paper, 
        show_image=config["show_img"]
    )
else:
    st.info("請從左側設定並開始考試。")
