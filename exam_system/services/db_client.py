import os
import pandas as pd
import streamlit as st

# ------------------------------
# 題庫自動載入設定
# ------------------------------
BANK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bank")

@st.cache_data(show_spinner=False)
def load_question_bank():
    """從 bank 資料夾自動載入所有題庫分類（人身、外幣、投資型、產險）"""
    data = {}
    if not os.path.exists(BANK_DIR):
        st.error(f"❌ 找不到題庫資料夾：{BANK_DIR}")
        return data

    for domain in os.listdir(BANK_DIR):
        domain_path = os.path.join(BANK_DIR, domain)
        if not os.path.isdir(domain_path):
            continue  # 跳過不是資料夾的項目

        # 找該分類底下的第一個 Excel 檔
        excel_files = [f for f in os.listdir(domain_path) if f.endswith((".xlsx", ".xls"))]
        if not excel_files:
            st.warning(f"⚠️ 找不到 {domain} 題庫檔案")
            continue

        file_path = os.path.join(domain_path, excel_files[0])
        try:
            df = pd.read_excel(file_path)
            if "題目" in df.columns:
                data[domain] = df
                st.info(f"📘 已載入 {domain} 題庫：{excel_files[0]}")
            else:
                st.warning(f"⚠️ {domain} 題庫格式不符（缺少「題目」欄位）")
        except Exception as e:
            st.error(f"❌ 載入 {domain} 題庫時發生錯誤：{e}")

    return data


def get_questions_by_domain(domain: str):
    data = load_question_bank()
    return data.get(domain, pd.DataFrame())
