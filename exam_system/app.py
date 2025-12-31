import streamlit as st

from exam_system.ui.layout import apply_page_config, render_header, render_usage_guide
from exam_system.ui.admin_panel import render_admin_panel
from exam_system.services.github_repo import migrate_pointer_prefix_if_needed

apply_page_config()

# pointer 自動遷移（banks/ -> bank/）
migrate_pointer_prefix_if_needed()

render_header("錠嵂AI考照機器人")
render_usage_guide()

st.info("請從左側 Pages 選單進入：練習模式 / 模擬考模式。")

# sidebar 管理者面板（可上傳題庫/切換 pointer）
render_admin_panel()
