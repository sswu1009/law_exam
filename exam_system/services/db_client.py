import pandas as pd
import streamlit as st
from config.settings import QUESTION_PATH, SHEET_NAMES

@st.cache_data(show_spinner=False)
def load_question_bank():
    """載入題庫（多工作表）"""
    data = {}
    try:
        xls = pd.ExcelFile(QUESTION_PATH)
        for sheet in SHEET_NAMES:
            data[sheet] = pd.read_excel(xls, sheet)
    except Exception as e:
        st.error(f"❌ 題庫載入失敗：{e}")
    return data


def get_questions_by_domain(domain: str):
    """依照領域（人身/外幣/投資型）回傳題庫"""
    data = load_question_bank()
    return data.get(domain, pd.DataFrame())
