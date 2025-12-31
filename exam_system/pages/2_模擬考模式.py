import time
import streamlit as st

from exam_system.config import settings
from exam_system.services import github_repo
from exam_system.services.bank_loader import load_bank_from_github
from exam_system.ui.layout import apply_page_config, render_header
from exam_system.ui.admin_panel import render_admin_panel
from exam_system.ui.exam_render import (
    ensure_session_defaults,
    build_option_cols,
    sample_paper,
    render_mock_exam,
    render_results,
)

apply_page_config()
ensure_session_defaults()
render_header("📝 模擬考模式")

# 管理者面板（在 sidebar expander）
render_admin_panel()

with st.sidebar:
    st.header("⚙️ 考試設定（模擬考模式）")
    st.subheader("題庫來源")

    pick_type = st.selectbox("選擇類型", options=settings.BANK_TYPES, index=0, key="mock_type")
    merge_all = st.checkbox("合併載入此類型下所有題庫檔", value=False, key="mock_merge_all")

    type_files = github_repo.list_bank_files(pick_type)
    if not type_files:
        st.error(f"❌ {pick_type} 類型目前沒有 .xlsx 題庫檔")
        st.stop()

    if merge_all:
        bank_source = type_files
        st.caption(f"將合併 {len(type_files)} 檔")
    else:
        current_path = github_repo.get_current_bank_path(pick_type)
        idx = type_files.index(current_path) if current_path in type_files else 0
        pick_file = st.selectbox("選擇題庫檔", options=type_files, index=idx, key="mock_pick_file")
        bank_source = pick_file

    bank_df = load_bank_from_github(bank_source)
    st.session_state["df"] = bank_df

    all_tags = sorted({t.strip() for tags in bank_df["Tag"].dropna().astype(str) for t in tags.split(";") if t.strip()})
    picked_tags = st.multiselect("選擇標籤（可多選，不選=全選）", options=all_tags, key="mock_tags")

    if picked_tags:
        mask = bank_df["Tag"].astype(str).apply(
            lambda s: any(t in [x.strip() for x in s.split(";")] for t in picked_tags)
        )
        filtered = bank_df[mask].copy()
    else:
        filtered = bank_df.copy()

    max_q = len(filtered)
    num_q = st.number_input("抽題數量", min_value=1, max_value=max(1, max_q), value=min(30, max_q), step=1, key="mock_numq")

    shuffle_options = st.checkbox("隨機打亂選項順序", value=True, key="mock_shuffle_opt")
    random_order = st.checkbox("隨機打亂題目順序", value=True, key="mock_shuffle_q")
    show_image = st.checkbox("顯示圖片（若有）", value=True, key="mock_show_img")

    st.divider()
    time_limit_min = st.number_input("時間限制（分鐘，0=無限制）", min_value=0, max_value=300, value=0, key="mock_time")
    time_limit_sec = int(time_limit_min) * 60

    start_btn = st.button("🚀 開始模擬考", type="primary", key="mock_start")

    if start_btn and (not merge_all) and isinstance(bank_source, str):
        try:
            github_repo.set_current_bank_path(pick_type, bank_source)
        except Exception as e:
            st.warning("無法寫回指標檔，將以當前選擇直接出題。")
            st.caption(str(e))


if start_btn:
    option_cols = build_option_cols(filtered)
    if len(option_cols) < 2:
        st.error("題庫格式不完整：找不到足夠的 Option 欄位（OptionA/OptionB...）。")
        st.stop()

    st.session_state.paper = sample_paper(
        filtered,
        option_cols=option_cols,
        n=int(num_q),
        shuffle_options=shuffle_options,
        random_order=random_order,
    )
    st.session_state.start_ts = time.time()
    st.session_state.answers = {}
    st.session_state.started = True
    st.session_state.show_results = False
    st.session_state.results_df = None
    st.session_state.score_tuple = None
    st.session_state.time_limit = time_limit_sec
    st.rerun()


if st.session_state.started and st.session_state.paper and not st.session_state.show_results:
    render_mock_exam(
        st.session_state.paper,
        show_image=show_image,
        time_limit_sec=st.session_state.time_limit,
    )

elif st.session_state.started and st.session_state.paper and st.session_state.show_results:
    render_results(exam_mode="模擬考模式", paper=st.session_state.paper)
