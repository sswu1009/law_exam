# exam_system/pages/2_模擬考模式.py
import streamlit as st
import time
from exam_system.ui import layout, exam_render

layout.setup_page("模擬考模式")

config = layout.render_sidebar_settings()

# Start
if config["start"]:
    st.session_state.paper = exam_render.sample_paper(
        config["df"], config["num_q"], config["random_q"], config["shuffle_opt"]
    )
    st.session_state.start_ts = time.time()
    st.session_state.answers = {}
    st.session_state.mode = "mock"
    st.session_state.submitted = False
    st.rerun()

# Render
if st.session_state.get("mode") == "mock" and st.session_state.get("paper"):
    if not st.session_state.get("submitted", False):
        exam_render.render_mock_exam_questions(
            st.session_state.paper, 
            show_image=config["show_img"]
        )
        
        if st.button("📥 交卷", type="primary", use_container_width=True):
            st.session_state.submitted = True
            st.rerun()
    else:
        # Results
        df_res, correct = exam_render.calculate_results(
            st.session_state.paper, 
            st.session_state.answers
        )
        exam_render.render_result_page(df_res, correct, len(st.session_state.paper))
        
        if st.button("再來一次"):
            st.session_state.mode = None
            st.rerun()
else:
    st.info("請從左側設定並開始模擬考。")
