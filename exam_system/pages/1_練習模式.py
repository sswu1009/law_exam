import streamlit as st

from ui.layout import render_header
from services.db_client import load_all_banks, read_bank_excel

render_header("🧠 練習模式")

banks = load_all_banks()
if not banks or all(len(v) == 0 for v in banks.values()):
    st.warning("⚠️ 尚未偵測到題庫，請檢查 exam_system/bank/ 資料夾與檔案副檔名。")
    st.stop()

with st.sidebar:
    st.subheader("📚 題庫類別")
    category = st.selectbox("選擇題庫類別", options=list(banks.keys()))

files = banks.get(category, [])
if not files:
    st.warning(f"⚠️ {category} 類別底下沒有可讀取的 Excel 檔。")
    st.stop()

file_names = [f.name for f in files]
chosen = st.selectbox("選擇題庫檔案", options=file_names)
chosen_file = next(f for f in files if f.name == chosen)

st.info(f"目前選擇：{chosen_file.category} / {chosen_file.name}")

try:
    df = read_bank_excel(chosen_file.path)
    st.success(f"✅ 讀取成功：共 {len(df)} 筆、{len(df.columns)} 欄")
    st.dataframe(df.head(20), use_container_width=True)
except Exception as e:
    st.error(str(e))
    st.stop()
