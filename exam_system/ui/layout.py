from __future__ import annotations

import streamlit as st
from exam_system.config import settings


def apply_page_config():
    st.set_page_config(page_title=settings.PAGE_TITLE, layout=settings.LAYOUT)


def render_header(title: str):
    st.title(title)


def render_usage_guide():
    with st.expander("📖 使用說明", expanded=True):
        st.markdown(
            """
歡迎使用 **錠嵂保經AI模擬考試機器人**

**模式與 AI 助教：**
- **練習模式**：作答時可查看「💡 AI 提示」（可選擇是否查看）；交卷後提供「錯題 AI 分析/復盤」，並可對**錯題**逐題顯示 AI 詳解。
- **模擬考模式**：作答時**沒有提示**；交卷後**每題**都可顯示 AI 詳解（自選是否查看），另提供「錯題 AI 復盤」。

**操作方式：**
1. 左側設定抽題數量、是否隨機打亂題目/選項與題庫來源。
2. 點擊 🚀 開始考試。
3. 完成後按「📥 交卷並看成績」查看分數、詳解與 AI 復盤。
4. 結果頁可下載作答明細（CSV）。

⚠️ 管理者可於側欄 **題庫管理** 上傳或切換題庫。
"""
        )


def powered_by_gemini_caption():
    st.caption("[Powered by Gemini]")
