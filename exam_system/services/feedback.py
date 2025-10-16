import pandas as pd
import os
import datetime
import streamlit as st

FEEDBACK_FILE = "data/feedback_records.csv"

def save_feedback(question_id: str, is_good: bool, comment: str = ""):
    """儲存使用者回饋紀錄"""
    os.makedirs("data", exist_ok=True)
    df = pd.DataFrame([{
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question_id": question_id,
        "feedback": "👍" if is_good else "👎",
        "comment": comment
    }])

    if os.path.exists(FEEDBACK_FILE):
        old = pd.read_csv(FEEDBACK_FILE)
        df = pd.concat([old, df], ignore_index=True)

    df.to_csv(FEEDBACK_FILE, index=False, encoding="utf-8-sig")
    st.success("✅ 已送出回饋，感謝你的意見！")


@st.cache_data(show_spinner=False)
def load_feedback():
    """讀取歷史回饋"""
    if os.path.exists(FEEDBACK_FILE):
        return pd.read_csv(FEEDBACK_FILE)
    else:
        return pd.DataFrame(columns=["timestamp", "question_id", "feedback", "comment"])
