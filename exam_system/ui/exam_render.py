from __future__ import annotations

import random
import time
from typing import Any

import pandas as pd
import streamlit as st

from exam_system.ui.layout import powered_by_gemini_caption
from exam_system.services.gemini_client import (
    gemini_ready,
    gemini_generate_cached,
    build_hint_prompt,
    build_explain_prompt,
    build_summary_prompt,
    build_weak_wrong_prompt,
)


def ensure_session_defaults():
    for key, default in [
        ("df", None),
        ("paper", None),
        ("start_ts", None),
        ("time_limit", 0),
        ("answers", {}),
        ("started", False),
        ("show_results", False),
        ("results_df", None),
        ("score_tuple", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def build_option_cols(bank: pd.DataFrame) -> list[str]:
    return [
        c for c in bank.columns
        if str(c).lower().startswith("option") and bank[c].astype(str).str.strip().ne("").any()
    ]


def sample_paper(df: pd.DataFrame, option_cols: list[str], n: int,
                 shuffle_options: bool, random_order: bool) -> list[dict[str, Any]]:
    n = min(n, len(df))
    if n <= 0:
        return []

    rows = df.sample(n=n, replace=False, random_state=random.randint(0, 1_000_000))
    if random_order:
        rows = rows.sample(frac=1, random_state=random.randint(0, 1_000_000))

    questions: list[dict[str, Any]] = []
    for _, r in rows.iterrows():
        items = []
        for i, col in enumerate(option_cols):
            txt = str(r.get(col, "")).strip()
            if txt:
                orig_lab = chr(ord("A") + i)
                items.append((orig_lab, txt))

        if shuffle_options:
            random.shuffle(items)

        choices = []
        orig_to_new = {}
        for idx, (orig_lab, txt) in enumerate(items):
            new_lab = chr(ord("A") + idx)
            choices.append((new_lab, txt))
            orig_to_new[orig_lab] = new_lab

        raw_ans = str(r.get("Answer", "")).upper().strip()
        orig_ans_letters = set(raw_ans) if raw_ans else set()
        new_ans = {orig_to_new[a] for a in orig_ans_letters if a in orig_to_new}

        qtype = str(r.get("Type", "SC")).upper()
        questions.append(
            {
                "ID": r["ID"],
                "Question": r["Question"],
                "Type": qtype,
                "Choices": choices,
                "Answer": new_ans,
                "Explanation": r.get("Explanation", ""),
                "Image": r.get("Image", ""),
                "Tag": r.get("Tag", ""),
                "SourceFile": r.get("SourceFile", ""),
                "SourceSheet": r.get("SourceSheet", ""),
            }
        )
    return questions


def render_question_choices(q: dict, idx: int, mode: str):
    display = [f"{lab}. {txt}" for lab, txt in q["Choices"]]
    if q["Type"] == "MC":
        picked = st.multiselect("（複選）選擇所有正確選項：", options=display, key=f"{mode}_pick_{idx}")
        picked_labels = {opt.split(".", 1)[0] for opt in picked}
    else:
        choice = st.radio("（單選）選擇一個答案：", options=display, key=f"{mode}_pick_{idx}")
        picked_labels = {choice.split(".", 1)[0]} if choice else set()
    return picked_labels


def render_practice_mode(paper: list[dict], show_image: bool = True):
    if "practice_idx" not in st.session_state:
        st.session_state.practice_idx = 0
        st.session_state.practice_correct = 0
        st.session_state.practice_answers = {}

    i = st.session_state.practice_idx
    q = paper[i]

    st.markdown(f"### 第 {i+1} / {len(paper)} 題")
    st.markdown(q["Question"])

    if show_image and str(q.get("Image", "")).strip():
        try:
            st.image(q["Image"], use_container_width=True)
        except Exception:
            st.info("圖片載入失敗。")

    # 練習模式：提示
    if gemini_ready():
        if st.button(f"💡 看不懂題目嗎？AI 提示（Q{i+1}）", key=f"ai_hint_practice_{i}"):
            ck, sys, usr = build_hint_prompt(q)
            with st.spinner("AI 產生提示中…"):
                hint = gemini_generate_cached(ck, sys, usr)
            st.session_state.setdefault("hints", {})[q["ID"]] = hint

        if q["ID"] in st.session_state.get("hints", {}):
            st.info(st.session_state["hints"][q["ID"]])
            powered_by_gemini_caption()

    picked_labels = render_question_choices(q, i, mode="practice")

    if st.button("提交這題", key=f"practice_submit_{i}"):
        gold = set(q["Answer"])
        st.session_state.practice_answers[q["ID"]] = picked_labels
        if picked_labels == gold:
            st.success("✅ 答對了！")
            st.session_state.practice_correct += 1
        else:
            st.error(f"❌ 答錯了。正確：{', '.join(sorted(list(gold))) or '(空)'}")
            if str(q.get("Explanation", "")).strip():
                st.caption(f"📖 題庫詳解：{q['Explanation']}")

    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("➡️ 下一題", key=f"practice_next_{i}"):
            if i < len(paper) - 1:
                st.session_state.practice_idx += 1
                st.rerun()
            else:
                st.success(f"🎉 完成練習：{st.session_state.practice_correct}/{len(paper)}")
    with cols[1]:
        if st.button("🔁 重新練習", key="practice_restart"):
            for k in ["practice_idx", "practice_correct", "practice_answers", "hints"]:
                st.session_state.pop(k, None)
            st.rerun()


def render_mock_exam(paper: list[dict], show_image: bool, time_limit_sec: int):
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("試卷")
    with col_right:
        if time_limit_sec > 0:
            elapsed = int(time.time() - st.session_state.start_ts)
            remain = max(0, time_limit_sec - elapsed)
            mm, ss = divmod(remain, 60)
            st.metric("剩餘時間", f"{mm:02d}:{ss:02d}")
            if remain == 0:
                st.warning("時間到！請繳卷。")

    answers_key = "answers"
    if answers_key not in st.session_state:
        st.session_state[answers_key] = {}

    for idx, q in enumerate(paper, start=1):
        st.markdown(f"### Q{idx}. {q['Question']}")
        if show_image and str(q.get("Image", "")).strip():
            try:
                st.image(q["Image"], use_container_width=True)
            except Exception:
                st.info("圖片載入失敗，請確認路徑或網址。")

        picked_labels = render_question_choices(q, idx, mode="mock")
        st.session_state[answers_key][q["ID"]] = picked_labels
        st.divider()

    submitted = st.button("📥 交卷並看成績", use_container_width=True)
    timeup = (time_limit_sec > 0 and time.time() - st.session_state.start_ts >= time_limit_sec)

    if submitted or timeup:
        _compute_results_and_show(paper)


def _compute_results_and_show(paper: list[dict]):
    answers_key = "answers"
    records = []
    correct_count = 0

    for q in paper:
        gold = set(q["Answer"])
        pred = st.session_state.get(answers_key, {}).get(q["ID"], set())
        is_correct = (pred == gold)
        correct_count += int(is_correct)

        mapping = {lab: txt for lab, txt in q["Choices"]}

        def render_set(ss):
            if not ss:
                return "(未作答)"
            ordered = sorted(list(ss))
            return ", ".join([f"{lab}. {mapping.get(lab, '')}" for lab in ordered])

        records.append(
            {
                "ID": q["ID"],
                "Tag": q.get("Tag", ""),
                "Question": q["Question"],
                "Your Answer": "".join(sorted(list(pred))) or "",
                "Your Answer (text)": render_set(pred),
                "Correct": "".join(sorted(list(gold))),
                "Correct (text)": render_set(gold),
                "Result": "✅ 正確" if is_correct else "❌ 錯誤",
                "Explanation": q.get("Explanation", ""),
                "SourceFile": q.get("SourceFile", ""),
                "SourceSheet": q.get("SourceSheet", ""),
            }
        )

    score_pct = round(100 * correct_count / len(paper), 2)
    st.session_state.results_df = pd.DataFrame.from_records(records)
    st.session_state.score_tuple = (correct_count, len(paper), score_pct)
    st.session_state.show_results = True
    st.rerun()


def render_results(exam_mode: str, paper: list[dict]):
    correct_count, total_q, score_pct = st.session_state.score_tuple
    st.success(f"你的分數：{correct_count} / {total_q}（{score_pct}%）")

    result_df: pd.DataFrame = st.session_state.results_df
    st.dataframe(result_df, use_container_width=True)

    csv_bytes = result_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ 下載作答明細（CSV）",
        data=csv_bytes,
        file_name="exam_results.csv",
        mime="text/csv",
    )

    st.subheader("🧠 AI 詳解 / 復盤")
    answers_key = "answers"

    def _fmt_letters(letters_set: set[str]) -> str:
        return ", ".join(sorted(list(letters_set))) if letters_set else "(未作答)"

    df_wrong = result_df[result_df["Result"].str.contains("錯")]

    for i, q in enumerate(paper, start=1):
        gold = set(q["Answer"])
        pred = st.session_state.get(answers_key, {}).get(q["ID"], set())
        is_correct = (pred == gold)

        title = f"Q{i}｜{'✅ 正確' if is_correct else '❌ 錯誤'}｜你的答案：{_fmt_letters(pred)}"
        st.markdown(
            f"""
            <div style="
                border:2px solid {'#34a853' if is_correct else '#d93025'};
                background:transparent;
                border-radius:12px;
                padding:12px 16px;
                margin:10px 0;
                font-weight:700;">
                {title}
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("展開詳解 / 選項"):
            st.markdown(
                f"<div style='white-space: pre-wrap'><strong>題目：</strong>{q['Question']}</div>",
                unsafe_allow_html=True,
            )
            mapping = {lab: txt for lab, txt in q["Choices"]}
            st.markdown("**選項：**")
            for lab, txt in q["Choices"]:
                tag = ""
                if lab in pred:
                    tag += "（你的選擇）"
                if lab in gold:
                    tag += " ✅"
                st.markdown(f"- **{lab}**. {txt} {tag}")
            st.markdown(f"**正解：** {_fmt_letters(gold)}")
            if str(q.get("Explanation", "")).strip():
                st.info(f"📖 題庫詳解：{q['Explanation']}")

            show_ai_button = (exam_mode == "模擬考模式") or (exam_mode == "練習模式" and not is_correct)
            if gemini_ready() and show_ai_button:
                if st.button(f"🤖 顯示 AI 詳解（Q{i}）", key=f"ai_explain_{exam_mode}_{i}"):
                    ck, sys, usr = build_explain_prompt(q)
                    with st.spinner("AI 產生詳解中…"):
                        expl = gemini_generate_cached(ck, sys, usr)
                    st.success(expl)
                    powered_by_gemini_caption()

    if gemini_ready() and not df_wrong.empty:
        if exam_mode == "練習模式":
            st.subheader("📊 錯題 AI 分析（練習模式）")
            if st.button("產生錯題分析/復盤", key="ai_wrong_review_practice"):
                ck, sys, usr = build_weak_wrong_prompt(df_wrong)
                with st.spinner("AI 分析中…"):
                    summ = gemini_generate_cached(ck, sys, usr)
                st.write(summ)
                powered_by_gemini_caption()
        else:
            st.subheader("📊 錯題 AI 復盤（模擬考模式）")
            if st.button("產生錯題復盤與建議", key="ai_wrong_review_mock"):
                ck, sys, usr = build_weak_wrong_prompt(df_wrong)
                with st.spinner("AI 分析中…"):
                    summ = gemini_generate_cached(ck, sys, usr)
                st.write(summ)
                powered_by_gemini_caption()

    if gemini_ready():
        st.subheader("📌 整體 AI 總結（可選）")
        if st.button("產出弱項分析與建議（整體）", key="ai_summary_btn"):
            ck, sys, usr = build_summary_prompt(result_df)
            with st.spinner("AI 分析中…"):
                summ = gemini_generate_cached(ck, sys, usr)
            st.write(summ)
            powered_by_gemini_caption()

    if st.button("🔁 再考一次", type="secondary"):
        for k in ["paper", "start_ts", "answers", "started", "show_results", "results_df", "score_tuple"]:
            st.session_state.pop(k, None)
        st.rerun()
