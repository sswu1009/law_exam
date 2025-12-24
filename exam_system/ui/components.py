def render_question_card(
    q_index: int,
    question_text: str,
    options: dict,
    correct_answer: str,
    show_ai_hint: bool = False,
):
    st.markdown(f"### 🧩 第 {q_index + 1} 題")
    st.write(question_text)

    key_prefix = f"q{q_index}"

    # === 清理 options（防止 nan / 空字串） ===
    clean_options = {}
    for k, v in options.items():
        if v and str(v).lower() != "nan":
            clean_options[k] = v.strip()

    if not clean_options:
        st.warning("⚠️ 本題未提供選項內容，請檢查題庫資料格式。")
        return

    selected = st.radio(
        "請選擇答案：",
        options=list(clean_options.keys()),
        format_func=lambda x: f"{x}. {clean_options.get(x, '')}",
        key=f"{key_prefix}_ans",
    )

    if selected:
        if selected == correct_answer:
            st.success(f"✅ 答對了！正確答案是 {correct_answer}")
        else:
            st.error(
                f"❌ 答錯了，你選的是 {selected}，正確答案是 {correct_answer}"
            )

    if show_ai_hint and selected:
        with st.expander("📘 AI 助教解析"):
            from services.ai_client import get_ai_hint
            st.markdown(
                get_ai_hint(
                    question_text=question_text,
                    choices=clean_options,
                    correct=correct_answer,
                )
            )
