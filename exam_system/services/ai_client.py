import os
import requests
import google.generativeai as genai
import streamlit as st
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_ENDPOINT, OLLAMA_MODEL


# ======================
# AI 客戶端初始化
# ======================
def use_ollama():
    """確認是否啟用 Ollama"""
    try:
        resp = requests.get(f"{OLLAMA_ENDPOINT}/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


# ----------------------
# Gemini 設定
# ----------------------
def _gemini_ready():
    return bool(GEMINI_API_KEY)


def _gemini_client():
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(GEMINI_MODEL)


# ----------------------
# Ollama 回答
# ----------------------
def query_ollama(prompt: str) -> str:
    payload = {"model": OLLAMA_MODEL, "prompt": prompt}
    try:
        r = requests.post(f"{OLLAMA_ENDPOINT}/api/generate", json=payload, stream=False, timeout=60)
        if r.status_code == 200:
            result = r.json()
            return result.get("response", "").strip()
        else:
            return f"Ollama 伺服器錯誤: {r.text}"
    except Exception as e:
        return f"Ollama 連線失敗: {e}"


# ----------------------
# Gemini 回答
# ----------------------
def query_gemini(prompt: str) -> str:
    try:
        model = _gemini_client()
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        return f"Gemini 發生錯誤: {e}"


# ----------------------
# 統一呼叫介面
# ----------------------
def ai_answer(system_msg: str, user_msg: str) -> str:
    """根據環境自動選擇 Ollama 或 Gemini"""
    prompt = f"[系統指示]\n{system_msg}\n\n[使用者問題]\n{user_msg}".strip()

    if use_ollama():
        result = query_ollama(prompt)
        if "Ollama" not in result:
            return result
    if _gemini_ready():
        return query_gemini(prompt)
    return "⚠️ 目前無可用的 AI 模型，請檢查 Ollama 或 Gemini 設定。"
