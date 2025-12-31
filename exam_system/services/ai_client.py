import streamlit as st
import google.generativeai as genai
from config import settings

def is_ready():
    return bool(settings.GEMINI_API_KEY)

def get_ai_explanation(question: dict):
    """
    question dict 需包含: Question, OptionA~D, Answer, Explanation
    """
    if not is_ready():
        return "⚠️ 請先設定 GEMINI_API_KEY"

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # 組裝 Prompt
        options_text = "\n".join([f"{k[-1]}. {v}" for k, v in question.items() if k.startswith("Option") and v])
        
        prompt = f"""
        [角色設定]
        你是一位專業的保險證照考試助教。
        
        [任務]
        請針對以下題目進行解析。
        1. 解釋為何正確答案是正確的。
        2. 簡單說明其他選項為何錯誤。
        3. 若有官方詳解，請參考並補充，但不要照抄。
        
        [題目資訊]
        題目: {question.get('Question')}
        選項:
        {options_text}
        正確答案: {question.get('Answer')}
        官方詳解: {question.get('Explanation', '無')}
        
        [輸出格式]
        請用條列式清楚說明，語氣親切專業。
        最後加上一行: [Powered by Gemini]
        """
        
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        return f"AI 連線錯誤: {str(e)}"
