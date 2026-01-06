"""
錠嵂AI考照系統 - 首頁
"""
import os
import sys

# 確保能導入 exam_system 模組
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

import streamlit as st
from exam_system.config import settings
from exam_system.ui.layout import setup_page, show_header
from exam_system.ui.admin_panel import show_admin_panel

# 設定頁面
setup_page()

# 顯示標題
show_header()

# 主頁內容
st.markdown("""
## 🎯 選擇考試模式

請從左側選單選擇：
- **練習模式**：逐題作答，可查看 AI 提示，答對立即反饋
- **模擬考模式**：完整模擬考試，時間限制，交卷後查看成績

---

## ⚙️ 系統設定

在左側邊欄可以：
1. 選擇題庫類型（人身/投資型/外幣）
2. 選擇或合併題庫檔案
3. 設定抽題數量與考試時間
4. 管理者可上傳新題庫
""")

# 側邊欄 - 管理者面板
with st.sidebar:
    st.divider()
    show_admin_panel()

# 頁尾
st.divider()
st.caption(f"💡 提示：AI 助教功能{'已啟用' if settings.gemini_ready() else '未啟用（需設定 GEMINI_API_KEY）'}")
