"""
Gemini AI 客戶端服務
負責所有 AI 提示、詳解、復盤功能
"""
import hashlib
import streamlit as st
import google.generativeai as genai
import pandas as pd

from exam_system.config import settings


def _hash(s: str) -> str:
    """產生字串的 MD5 雜湊"""
    return hashlib.md5(s.encode("utf-8")).hexdigest()


class GeminiService:
    """Gemini AI 服務"""
    
    def __init__(self):
        if not settings.gemini_ready():
            self.enabled = False
            return
        
        self.enabled = True
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_MODEL
    
    def _get_model(self):
        """取得 Gemini 模型實例"""
        if not self.enabled:
            raise RuntimeError("Gemini 未啟用")
        return genai.GenerativeModel(self.model_name)
    
    @st.cache_data(show_spinner=False)
    def generate_cached(_self, cache_key: str, system_msg: str, user_msg: str) -> str:
        """
        快取式生成內容（使用 _self 避免序列化問題）
        cache_key: 用於 Streamlit 快取的唯一鍵
        """
        if not _self.enabled:
            return "AI 功能未啟用，請設定 GEMINI_API_KEY"
        
        model = _self._get_model()
        prompt = f"[系統指示]\n{system_msg}\n\n[使用者需求]\n{user_msg}".strip()
        
        try:
            resp = model.generate_content(prompt)
            return (resp.text or "").strip()
        except Exception as e:
            return f"AI 生成失敗：{str(e)}"
    
    def build_hint_prompt(self, question: dict) -> tuple[str, str, str]:
        """
        建立提示 Prompt（作答時的方向提示）
        返回：(cache_key, system_msg, user_msg)
        """
        sys = (
            "你是考試助教，只能提供方向提示，嚴禁輸出答案代號或逐字答案。"
            "優先參考題庫的解答說明；不足再補充概念或排除法。"
        )
        
        expl = (question.get("Explanation") or "").strip()
        choices_text = "\n".join([f"{lab}. {txt}" for lab, txt in question["Choices"]])
        
        user = f"""
題目: {question['Question']}
選項:
{choices_text}
題庫解答說明（僅供參考、不可爆雷）：{expl if expl else "（無）"}
請用 1-2 句提示重點，不要爆雷。
"""
        
        ck = _hash("HINT|" + question["Question"] + "|" + expl)
        return ck, sys, user
    
    def build_explain_prompt(self, question: dict) -> tuple[str, str, str]:
        """
        建立詳解 Prompt（交卷後的完整解析）
        返回：(cache_key, system_msg, user_msg)
        """
        sys = "你是解題老師，優先引用題庫解答說明，逐項說明正確與錯誤，保持精簡。"
        
        expl = (question.get("Explanation") or "").strip()
        ans_letters = "".join(sorted(list(question.get("Answer", set()))))
        choices_text = "\n".join([f"{lab}. {txt}" for lab, txt in question["Choices"]])
        
        user = f"""
題目: {question['Question']}
選項:
{choices_text}
正解: {ans_letters or "（無）"}
題庫解答說明：{expl if expl else "（無）"}
"""
        
        ck = _hash("EXPL|" + question["Question"] + "|" + ans_letters)
        return ck, sys, user
    
    def build_summary_prompt(self, result_df: pd.DataFrame) -> tuple[str, str, str]:
        """
        建立整體總結 Prompt
        返回：(cache_key, system_msg, user_msg)
        """
        sys = "你是考後診斷教練，請分析弱點與建議。"
        
        mini = result_df[["ID", "Tag", "Question", "Your Answer", "Correct", "Result"]].head(200)
        csv_content = mini.to_csv(index=False)
        
        user = f"""
以下是作答結果（最多 200 題）：
{csv_content}
請輸出：整體表現、弱項主題、3-5點練習建議（條列）。
"""
        
        ck = _hash("SUMM|" + csv_content)
        return ck, sys, user
    
    def build_wrong_review_prompt(self, result_df_wrong: pd.DataFrame) -> tuple[str, str, str]:
        """
        建立錯題復盤 Prompt
        返回：(cache_key, system_msg, user_msg)
        """
        sys = "你是考後復盤教練，聚焦錯題的主題與知識點，指出易錯原因與改進建議。"
        
        mini = result_df_wrong[["ID", "Tag", "Question", "Your Answer", "Correct"]].head(200)
        csv_content = mini.to_csv(index=False)
        
        user = f"""
以下為本次錯題（最多 200 題）：
{csv_content}
請輸出：1) 錯題主題聚類 2) 容易混淆/易錯點 3) 必背觀念 4) 接下來復習建議（條列）。
"""
        
        ck = _hash("WRONG|" + csv_content)
        return ck, sys, user


# 建立全域實例
gemini_service = GeminiService()
