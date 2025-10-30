# ui/components.py
import streamlit as st
from typing import Dict, Optional
from services.ai_client import get_ai_hint


def render_question_card(
    q_index: int,
    question_text: str,
    options: Dict[str, str],
    correct_answer: str,
    show_ai_hint: bool = False,
):
    """
    顯示單一題目卡，包含：
    - 題號
    - 題目文字
    - 四個選項 (A~D)
    - 選擇答案後顯示正確與否
    - AI 助教提示 (可選)
    """

    st.markdown(f"### 🧩 第 {q_index + 1} 題")
    st.write(question_text)

    # === 建立唯一 key，避免不同題目互相干擾 ===
    key_prefix = f"q{q_index}"

    # === 顯示選項 ===
    selected = st.radio(
        "請選擇答案：",
        options=list(options.keys()),
        format_func=lambda x: f"{x}. {options[x]}",
        key=f"{key_prefix}_ans",
        horizontal=False,
    )

    # === 作答結果顯示 ===
    if selected:
        if selected == correct_answer:
            st.success(f"✅ 答對了！正確答案是 {correct_answer}：{options[correct_answer]}")
        else:
            st.error(
                f"❌ 答錯了。你的答案是 {selected}：{options[selected]}，"
                f"正確答案是 {correct_answer}：{options[correct_answer]}"
            )

    # === 顯示 AI 助教提示 ===
    if show_ai_hint and selected:
        with st.expander("📘 顯示 AI 助教解析", expanded=False):
            with st.spinner("AI 助教正在解析中..."):
                try:
                    ai_text = get_ai_hint(
                        question_text=question_text,
                        choices=options,
                        correct=correct_answer,
                    )
                    st.markdown(ai_text)
                except Exception as e:
                    st.warning(f"AI 助教回覆失敗：{e}")


def render_question_summary(total: int, correct: int):
    """
    顯示答題總結。
    """
    st.divider()
    st.subheader("📊 答題統計")
    st.write(f"總題數：{total}")
    st.write(f"答對題數：{correct}")
    accuracy = (correct / total * 100) if total > 0 else 0
    st.write(f"正確率：{accuracy:.1f}%")

    if accuracy >= 80:
        st.success("表現優秀，繼續保持！")
    elif accuracy >= 60:
        st.info("尚可，但仍有進步空間。")
    else:
        st.warning("建議多加練習。")


def render_category_selector(categories: list) -> Optional[str]:
    """
    類別下拉選單
    """
    st.sidebar.markdown("## 📚 題庫類別")
    if not categories:
        st.warning("未偵測到題庫資料。請確認 bank 資料夾結構。")
        return None
    category = st.sidebar.selectbox("選擇題庫類別：", categories)
    return category


def render_chapter_selector(chapters: list) -> Optional[str]:
    """
    章節下拉選單
    """
    if not chapters:
        st.info("此類別未提供章節分類。")
        return None
    chapter = st.sidebar.selectbox("選擇章節：", ["全部"] + chapters)
    if chapter == "全部":
        return None
    return chapter
