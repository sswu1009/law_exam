# exam_system/ui/layout.py
import streamlit as st
import random
from exam_system.config import settings
from exam_system.services import github_repo
from exam_system.services import bank_loader
from exam_system.ui import admin_panel

def setup_page(title="錠嵂AI考照"):
    st.set_page_config(page_title=title, layout="wide")
    st.title("🛡️ 錠嵂AI考照機器人")
    with st.expander("📖 使用說明", expanded=False):
        st.markdown("""
        **模式與 AI 助教：**
        - **練習模式**：作答時可查看「💡 AI 提示」；交卷後提供「錯題 AI 分析」。
        - **模擬考模式**：作答時無提示；交卷後可顯示 AI 詳解與復盤。
        """)

def render_sidebar_settings():
    """渲染側邊欄並回傳考試設定"""
    with st.sidebar:
        st.header("⚙️ 考試設定")
        
        # 1. 題庫選擇
        st.subheader("題庫來源")
        pick_type = st.selectbox("選擇類型", options=settings.BANK_TYPES, index=0)
        merge_all = st.checkbox("合併此類型下所有檔案", value=False)
        
        type_files = github_repo.list_files(settings.get_type_dir(pick_type))
        selected_paths = []

        if merge_all:
            if not type_files:
                st.warning(f"{pick_type} 下無檔案")
            else:
                selected_paths = type_files
                st.caption(f"將合併 {len(type_files)} 檔")
        else:
            current_ptr = github_repo.get_current_bank_path(pick_type)
            # Find index
            try:
                idx = type_files.index(current_ptr)
            except ValueError:
                idx = 0
            
            pick_file = st.selectbox("選擇題庫檔", options=type_files or ["（尚無檔案）"], index=idx if type_files else 0)
            if type_files:
                selected_paths = [pick_file]

        # 2. 載入題庫 (Cache Check)
        if "df" not in st.session_state or st.session_state.get("current_paths") != selected_paths:
             if selected_paths:
                 st.session_state.df = bank_loader.load_banks(selected_paths)
                 st.session_state.current_paths = selected_paths
             else:
                 st.session_state.df = None

        bank = st.session_state.get("df")
        if bank is None or bank.empty:
            st.error("無有效題庫資料")
            st.stop()
            
        # 3. 標籤與篩選
        all_tags = sorted({t.strip() for tags in bank["Tag"].dropna().astype(str) for t in tags.split(";") if t.strip()})
        picked_tags = st.multiselect("標籤篩選", options=all_tags)
        
        if picked_tags:
            mask = bank["Tag"].astype(str).apply(lambda s: any(t in [x.strip() for x in s.split(";")] for t in picked_tags))
            filtered_df = bank[mask].copy()
        else:
            filtered_df = bank.copy()
            
        max_q = len(filtered_df)
        st.caption(f"可用題數：{max_q}")
        
        num_q = st.number_input("抽題數量", min_value=1, max_value=max(1, max_q), value=min(20, max_q))
        shuffle_opt = st.checkbox("隨機選項順序", value=True)
        random_q = st.checkbox("隨機題目順序", value=True)
        show_img = st.checkbox("顯示圖片", value=True)
        
        st.divider()
        time_min = st.number_input("時間限制 (分, 0=不限)", 0, 300, 0)
        
        start_btn = st.button("🚀 開始考試", type="primary")
        
        # Admin Panel
        admin_panel.render_admin_panel()
        
        return {
            "start": start_btn,
            "df": filtered_df,
            "num_q": num_q,
            "shuffle_opt": shuffle_opt,
            "random_q": random_q,
            "show_img": show_img,
            "time_limit": int(time_min * 60)
        }
