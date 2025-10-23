import os
import pandas as pd
import streamlit as st

BANK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bank")

@st.cache_data(show_spinner=False)
def load_question_bank():
    """靜默載入題庫"""
    data = {}
    if not os.path.exists(BANK_DIR):
        st.error(f"❌ 找不到題庫資料夾：{BANK_DIR}")
        return data

    for domain in os.listdir(BANK_DIR):
        domain_path = os.path.join(BANK_DIR, domain)
        if not os.path.isdir(domain_path):
            continue

        excel_files = [f for f in os.listdir(domain_path) if f.endswith((".xlsx", ".xls"))]
        if not excel_files:
            continue

        file_path = os.path.join(domain_path, excel_files[0])
        try:
            df = pd.read_excel(file_path)
            if "題目" in df.columns:
                data[domain] = df
        except Exception as e:
            st.error(f"❌ 載入 {domain} 題庫錯誤：{e}")
    return data


def get_questions_by_domain(domain: str):
    data = load_question_bank()
    return data.get(domain, pd.DataFrame())
