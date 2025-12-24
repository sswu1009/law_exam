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
    st.markdown(f"### 🧩 第 {q_index + 1} 題")
    st.write(question_text)

    key_prefix = f"q{q_index}"

    clean_options = {
        k: v for k, v in options.items()
        if v and str(v).lower() != "nan"
    }

    if not clean_options:
        st.warning("⚠️ 本題未提供選項內容")
        return

    selected = st.radio(
        "請選擇答案：",
        options=list(clean_options.keys()),
        format_func=lambda x: f"{x}. {clean_options[x]}",
        key=f"{key_prefix}_ans",
    )

    if selected:
        if selected == correct_answer:
            st.success("✅ 答對了")
        else:
            st.error(f"❌ 答錯了，正確答案是 {correct_answer}")

    if show_ai_hint and selected:
        with st.expander("📘 AI 助教解析"):
            st.markdown(
                get_ai_hint(
                    question_text=question_text,
                    choices=clean_options,
                    correct=correct_answer,
                )
            )


def render_question_summary(total: int, correct: int):
    st.divider()
    st.subheader("📊 答題統計")
    st.write(f"總題數：{total}")
    st.write(f"答對題數：{correct}")


def render_category_selector(categories: list) -> Optional[str]:
    st.sidebar.markdown("## 📚 題庫類別")
    if not categories:
        return None
    return st.sidebar.selectbox("選擇題庫類別：", categories)


def render_chapter_selector(chapters: list) -> Optional[str]:
    if not chapters:
        st.info("此類別未提供章節分類")
        return None
    chapter = st.sidebar.selectbox("選擇章節：", ["全部"] + chapters)
    return None if chapter == "全部" else chapter
