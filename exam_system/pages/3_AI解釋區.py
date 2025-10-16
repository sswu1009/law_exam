import streamlit as st
from ui.layout import render_header
from services.feedback import load_feedback

def main():
    render_header("💬 AI 解釋與回饋區")

    df = load_feedback()
    if df.empty:
        st.info("尚無任何 AI 解釋或回饋紀錄。")
        return

    st.write("以下為歷史 AI 解釋回饋紀錄：")
    st.dataframe(df, use_container_width=True)

    # 回饋統計
    good = len(df[df["feedback"] == "👍"])
    bad = len(df[df["feedback"] == "👎"])
    total = len(df)
    if total > 0:
        st.success(f"👍 好評率：{(good/total)*100:.1f}%　👎 差評率：{(bad/total)*100:.1f}%")

if __name__ == "__main__":
    main()
