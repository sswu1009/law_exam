import streamlit as st
from config.settings import APP_TITLE, APP_ICON, init_page_config
from ui.layout import render_header

# 初始化頁面設定
init_page_config()

# 主頁
def main():
    render_header("📘 錠嵂保經 AI 模擬考系統")

    st.markdown("""
    ### 模式選擇
    選擇你要進入的模式 👇  
    - **練習模式**：支援 AI 題目提示與章節導讀  
    - **模擬考模式**：計時作答與分數統計  
    - **AI 解釋區**：瀏覽 AI 詳解與歷史回饋
    """)

    st.page_link("pages/1_練習模式.py", label="🧠 練習模式")
    st.page_link("pages/2_模擬考模式.py", label="📝 模擬考模式")
    st.page_link("pages/3_AI解釋區.py", label="💬 AI 解釋區")

if __name__ == "__main__":
    main()
