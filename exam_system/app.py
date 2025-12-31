import streamlit as st
from config.settings import init_page_config
from ui.layout import render_header, render_footer

# 初始化設定 (必須在最前面)
init_page_config()

def main():
    render_header("📘 錠嵂保經 AI 模擬考系統")

    st.markdown("""
    ### 歡迎使用
    請從下方選擇模式開始：
    
    ---
    
    #### 🧠 **練習模式**
    - 逐題顯示，答錯即時提示
    - 支援 AI 助教解析
    
    #### 📝 **模擬考模式**
    - 模擬真實考試情境
    - 計時、交卷後結算成績
    
    ---
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        st.page_link("pages/1_練習模式.py", label="前往 練習模式", icon="💪", use_container_width=True)
    with col2:
        st.page_link("pages/2_模擬考模式.py", label="前往 模擬考模式", icon="📝", use_container_width=True)
        
    render_footer()

if __name__ == "__main__":
    main()
