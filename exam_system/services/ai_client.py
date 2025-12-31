import os
import streamlit as st
import hashlib

# 嘗試匯入 Gemini
try:
    import google.generativeai as genai
    _HAS_GEMINI = True
except ImportError:
    _HAS_GEMINI = False

from config.settings import GEMINI_API_KEY, GEMINI_MODEL

def _gemini_ready() -> bool:
    return _HAS_GEMINI and bool(GEMINI_API_KEY)

@st.cache_data(show_spinner=False)
def get_ai_hint(question_text: str, choices: dict, correct: str = "", explanation: str = "") -> str:
    """
    產生 AI 解析 (含快取)
    """
    if not _gemini_ready():
        return "⚠️ 請先設定 GEMINI_API_KEY 以啟用 AI 解析功能。"

    # 組合 Prompt
    choices_text = "\n".join([f"{k}. {v}" for k, v in choices.items() if v])
    
    system_msg = "你是一位保險證照考試的專業助教。請針對題目進行解析，解釋正確選項為何正確，並指出錯誤選項的盲點。請勿直接給出答案代號，而是著重觀念講解。"
    user_msg = f"""
    題目：{question_text}
    選項：
    {choices_text}
    正確答案：{correct}
    官方詳解參考：{explanation}
    
    請用條列式說明，最後加上 [Powered by Gemini]。
    """

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(f"{system_msg}\n\n{user_msg}")
        return resp.text
    except Exception as e:
        return f"AI 連線失敗：{str(e)}"
