# exam_system/ui/exam_render.py
import time
import random
import streamlit as st
import pandas as pd
from exam_system.services import gemini_client

def sample_paper(df, n, random_order=True, shuffle_opts=True):
    n = min(int(n), len(df))
    rows = df.sample(n=n) if random_order else df.head(n)
    if random_order:
        rows = rows.sample(frac=1)
    
    questions = []
    option_cols = [c for c in df.columns if c.startswith("Option") and df[c].astype(str).str.strip().ne("").any()]
    
    for _, r in rows.iterrows():
        items = []
        for i, col in enumerate(option_cols):
            txt = str(r.get(col, "")).strip()
            if txt:
                orig_lab = chr(ord('A') + i)
                items.append((orig_lab, txt))
        
        if shuffle_opts:
            random.shuffle(items)
        
        choices = []
        orig_to_new = {}
        for idx, (orig_lab, txt) in enumerate(items):
            new_lab = chr(ord('A') + idx)
            choices.append((new_lab, txt))
            orig_to_new[orig_lab] = new_lab
            
        raw_ans = str(r.get("Answer", "")).upper().strip()
        orig_ans_set = set(raw_ans)
        new_ans_set = {orig_to_new[a] for a in orig_ans_set if a in orig_to_new}
        
        questions.append({
            "ID": r["ID"],
            "Question": r["Question"],
            "Type": str(r.get("Type", "SC")).upper(),
            "Choices": choices,
            "Answer": new_ans_set,
            "Explanation": r.get("Explanation", ""),
            "Image": r.get("Image", ""),
            "Tag": r.get("Tag", ""),
        })
    return questions

def render_practice_mode(paper, show_image=True):
    if "practice_idx" not in st.session_state:
        st.session_state.practice_idx = 0
        st.session_state.practice_correct = 0
    
    i = st.session_state.practice_idx
    if i >= len(paper):
        st.success(f"🎉 練習結束！得分：{st.session_state.practice_correct}/{len(paper)}")
        if st.button("重新練習"):
            st.session_state.practice_idx = 0
            st.session_state.practice_correct = 0
            st.rerun()
        return

    q = paper[i]
    st.markdown(f"### Q{i+1} / {len(paper)}")
    st.write(q["Question"])
    
    if show_image and str(q.get("Image", "")).strip():
        try:
            st.image(q["Image"])
        except: pass

    # AI Hint
    if gemini_client.is_ready():
        if st.button("💡 AI 提示", key=f"hint_{i}"):
            ck, sys, usr = gemini_client.build_hint_prompt(q)
            with st.spinner("思考中..."):
                st.info(gemini_client.generate_cached(ck, sys, usr))

    # Options
    opts = [f"{lab}. {txt}" for lab, txt in q["Choices"]]
    user_pick = set()
    
    if q["Type"] == "MC":
        sel = st.multiselect("選擇答案", opts, key=f"p_multi_{i}")
        user_pick = {s.split(".")[0] for s in sel}
    else:
        sel = st.radio("選擇答案", opts, key=f"p_radio_{i}")
        if sel: user_pick = {sel.split(".")[0]}
        
    if st.button("提交"):
        gold = q["Answer"]
        if user_pick == gold:
            st.success("✅ 答對！")
            st.session_state.practice_correct += 1
        else:
            st.error(f"❌ 錯誤。答案：{','.join(sorted(gold))}")
            if q["Explanation"]:
                st.caption(f"詳解：{q['Explanation']}")
            
            # 錯題 AI 詳解
            if gemini_client.is_ready():
                ck, sys, usr = gemini_client.build_explain_prompt(q)
                with st.expander("🤖 看 AI 詳解"):
                     st.write(gemini_client.generate_cached(ck, sys, usr))
        
        if st.button("下一題"):
            st.session_state.practice_idx += 1
            st.rerun()

def render_mock_exam_questions(paper, show_image=True):
    # Timer
    if st.session_state.time_limit > 0:
        elapsed = int(time.time() - st.session_state.start_ts)
        remain = max(0, st.session_state.time_limit - elapsed)
        st.metric("剩餘時間", f"{remain//60:02d}:{remain%60:02d}")
        if remain == 0:
            st.warning("時間到！")
            
    answers = st.session_state.setdefault("answers", {})
    
    for idx, q in enumerate(paper, 1):
        st.markdown(f"**Q{idx}. {q['Question']}**")
        if show_image and q.get("Image"):
            st.image(q["Image"])
            
        opts = [f"{lab}. {txt}" for lab, txt in q["Choices"]]
        if q["Type"] == "MC":
            sel = st.multiselect(f"Q{idx} 選項", opts, key=f"m_q_{idx}", label_visibility="collapsed")
            answers[q["ID"]] = {s.split(".")[0] for s in sel}
        else:
            sel = st.radio(f"Q{idx} 選項", opts, key=f"m_q_{idx}", label_visibility="collapsed")
            answers[q["ID"]] = {sel.split(".")[0]} if sel else set()
        st.divider()

def calculate_results(paper, answers):
    records = []
    correct = 0
    for q in paper:
        gold = q["Answer"]
        pred = answers.get(q["ID"], set())
        is_correct = (gold == pred)
        correct += int(is_correct)
        
        records.append({
            "ID": q["ID"],
            "Question": q["Question"],
            "Tag": q["Tag"],
            "Your Answer": "".join(sorted(pred)),
            "Correct": "".join(sorted(gold)),
            "Result": "✅" if is_correct else "❌",
            "Explanation": q["Explanation"],
            "RawQuestion": q # for AI usage
        })
    return pd.DataFrame(records), correct

def render_result_page(df_res, correct_count, total):
    st.balloons()
    score = round(100*correct_count/total, 1)
    st.success(f"成績：{correct_count} / {total} ({score}%)")
    
    st.dataframe(df_res.drop(columns=["RawQuestion"]), use_container_width=True)
    
    csv = df_res.drop(columns=["RawQuestion"]).to_csv(index=False).encode("utf-8-sig")
    st.download_button("下載 CSV", csv, "result.csv", "text/csv")
    
    # Wrong Review
    wrongs = df_res[df_res["Result"] == "❌"]
    if not wrongs.empty:
        st.subheader("❌ 錯題檢討")
        for _, row in wrongs.iterrows():
            q = row["RawQuestion"]
            with st.expander(f"{row['Question']}"):
                st.error(f"你的答案：{row['Your Answer']} | 正解：{row['Correct']}")
                st.write(f"詳解：{row['Explanation']}")
                
                if gemini_client.is_ready():
                    if st.button(f"🤖 AI 解析此題 ({row['ID']})"):
                        ck, sys, usr = gemini_client.build_explain_prompt(q)
                        st.write(gemini_client.generate_cached(ck, sys, usr))
        
        if gemini_client.is_ready():
            if st.button("📊 生成錯題總結報告"):
                ck, sys, usr = gemini_client.build_weak_wrong_prompt(wrongs)
                st.write(gemini_client.generate_cached(ck, sys, usr))
