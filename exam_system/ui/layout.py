"""
版面配置與共用 UI 元件
"""
import streamlit as st
from exam_system.config import settings


def setup_page(page_title: str = None):
    """設定頁面基本配置"""
    title = page_title or settings.APP_TITLE
    st.set_page_config(
        page_title=title,
        page_icon=settings.PAGE_ICON,
        layout="wide"
    )


def show_header():
    """顯示標題與使用說明"""
    st.title(f"{settings.PAGE_ICON} {settings.APP_TITLE}")
    
    with st.expander("📖 使用說明", expanded=True):
        st.markdown("""
        歡迎使用 **錠嵂保經AI模擬考試機器人** 🎉

        **模式與 AI 助教：**
        - **練習模式**：作答時可查看
