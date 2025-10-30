# services/ai_client.py
import os
from typing import Optional

import streamlit as st

# 若你要用 google.generativeai
try:
    import google.generativeai as genai
    _HAS_GEMINI = True
except ImportError:
    _HAS_GEMINI = False

import requests  # 給 Ollama 用


# === 環境設定 ===
DEFAULT_MODEL = "gemini"  # "gemini" or "ollama"
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5")


def _gemini_ready() -> bool:
    return _HAS_GEMINI and ("GEMINI_API_KEY" in st.secrets or os.getenv("GEMINI_API_KEY"))


def _gemini_generate(system_msg: str, user_msg: str) -> str:
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    prompt = f"[系統指示]\n{system_msg}\n\n[使用者題目]\n{user_msg}".strip()
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    return text


def _ollama_ready() -> bool:
    # 預設你本機有跑 ollama http://localhost:11434
    return True


def _ollama_generate(system_msg: str, user_msg: str) -> str:
    url = "http://localhost:11434/api/generate"
    prompt = f"{system_msg}\n\n{user_msg}"
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()
    except Exception as e:
        return f"無法取得 Ollama 回應：{e}"


def get_ai_hint(question_text: str, choices: Optional[dict] = None, correct: Optional[str] = None) -> str:
    """
    統一對外的 AI 解析介面。
    傳入題目文字、選項、正解（可選），回傳 AI 解析文字。
    最後一行會附上 [Powered by Gemini] 做除錯。
    """
    system_msg = (
        "你是一位台灣保險相關證照考試的解析助教，請用精簡條列說明為何正確答案正確，並說明其他選項錯在哪裡。"
        "必要時引用法規條文名稱，但不要捏造不存在的法條。"
    )

    user_parts = [f"題目：{question_text}"]
    if choices:
        for key, val in choices.items():
            user_parts.append(f"{key}. {val}")
    if correct:
        user_parts.append(f"正確答案：{correct}")

    user_msg = "\n".join(user_parts)

    # 優先 Gemini
    if _gemini_ready():
        ans = _gemini_generate(system_msg, user_msg)
        # 標註來源
        return ans + "\n\n[Powered by Gemini]"
    else:
        # 改走 Ollama
        ans = _ollama_generate(system_msg, user_msg)
        # 若你也想標註，可改成 Ollama
        return ans + "\n\n[Powered by Ollama]"
