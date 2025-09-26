import os
import json
import base64
import time
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# ==== Gemini（Google Generative AI）工具 ====
import hashlib
import google.generativeai as genai

def _gemini_ready():
    return bool(st.secrets.get("GEMINI_API_KEY"))

def _gemini_model():
    return st.secrets.get("GEMINI_MODEL", "gemini-1.5-flash")

def _gemini_client():
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel(_gemini_model())

@st.cache_data(show_spinner=False)
def _gemini_generate_cached(cache_key: str, system_msg: str, user_msg: str) -> str:
    model = _gemini_client()
    prompt = f"[系統指示]\n{system_msg}\n\n[使用者需求]\n{user_msg}".strip()
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()

def _hash(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="模擬考試機器人", layout="wide")
st.title("📘 模擬考試機器人（GitHub 題庫）")

# =========================================================
# GitHub 後台上傳／切換：核心工具
# =========================================================
GH_OWNER     = st.secrets.get("REPO_OWNER")
GH_REPO      = st.secrets.get("REPO_NAME")
GH_BRANCH    = st.secrets.get("REPO_BRANCH", "main")
GH_TOKEN     = st.secrets.get("GH_TOKEN")
BANKS_DIR    = st.secrets.get("BANKS_DIR", "banks")
POINTER_FILE = st.secrets.get("POINTER_FILE", "bank_pointer.json")

def _gh_headers():
    h = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        h["Authorization"] = f"Bearer {GH_TOKEN}"
    return h

def _gh_api(path, method="GET", **kwargs):
    url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/{path}"
    r = requests.request(method, url, headers=_gh_headers(), **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"GitHub API {method} {path} -> {r.status_code}: {r.text}")
    return r.json()

def _gh_get_sha(path):
    try:
        j = _gh_api(f"contents/{path}", params={"ref": GH_BRANCH})
        return j.get("sha")
    except Exception:
        return None

def _gh_put_file(path, content_bytes, message):
    b64 = base64.b64encode(content_bytes).decode("ascii")
    payload = {"message": message, "content": b64, "branch": GH_BRANCH}
    sha = _gh_get_sha(path)
    if sha:
        payload["sha"] = sha
    return _gh_api(f"contents/{path}", method="PUT", json=payload)

@st.cache_data(ttl=300)
def _gh_download_bytes(path):
    j = _gh_api(f"contents/{path}", params={"ref": GH_BRANCH})
    if j.get("encoding") == "base64":
        return base64.b64decode(j["content"])
    raw_url = f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{GH_BRANCH}/{path}"
    return requests.get(raw_url, headers=_gh_headers()).content

def get_current_bank_path():
    try:
        data = _gh_download_bytes(POINTER_FILE)
        conf = json.loads(data.decode("utf-8"))
        path = conf.get("path")
        if path:
            return path
    except Exception:
        pass
    return st.secrets.get("BANK_FILE", f"{BANKS_DIR}/exam_bank.xlsx")

def set_current_bank_path(path):
    if not path.startswith(f"{BANKS_DIR}/"):
        path = f"{BANKS_DIR}/{path}"
    conf = {"path": path}
    _gh_put_file(
        POINTER_FILE,
        json.dumps(conf, ensure_ascii=False, indent=2).encode("utf-8"),
        f"set current bank -> {path}",
    )
    _gh_download_bytes.clear()

def load_bank_from_github(load_bank_fn):
    bank_path = get_current_bank_path()
    data = _gh_download_bytes(bank_path)
    df = load_bank_fn(BytesIO(data))
    st.caption(f"使用固定題庫（GitHub）：{bank_path}")
    return df

def list_bank_files():
    try:
        items = _gh_api(f"contents/{BANKS_DIR}", params={"ref": GH_BRANCH})
        return [it["path"] for it in items if it["type"] == "file" and it["name"].lower().endswith(".xlsx")]
    except Exception:
        return []


# -----------------------------
# AI prompt 建構
# -----------------------------
def build_hint_prompt(q: dict):
    sys = "你是考試助教，只能提供方向提示，嚴禁輸出答案代號或逐字答案。"
    expl = (q.get("Explanation") or "").strip()
    user = f"""
題目: {q['Question']}
選項: 
{chr(10).join([f"{lab}. {txt}" for lab,txt in q['Choices']])}
題庫詳解（僅供參考，不可直接爆雷）：{expl if expl else "（無）"}
請用 1-2 句提示重點，不要爆雷。
"""
    ck = _hash("HINT|" + q["Question"] + "|" + expl)
    return ck, sys, user

def build_explain_prompt(q: dict):
    sys = "你是解題老師，優先引用題庫詳解，逐項說明正確與錯誤。"
    expl = (q.get("Explanation") or "").strip()
    ans_letters = "".join(sorted(list(q.get("Answer", set()))))
    user = f"""
題目: {q['Question']}
選項: 
{chr(10).join([f"{lab}. {txt}" for lab,txt in q['Choices']])}
正解: {ans_letters or "（無）"}
題庫詳解：{expl if expl else "（無）"}
"""
    ck = _hash("EXPL|" + q["Question"] + "|" + ans_letters)
    return ck, sys, user

def build_summary_prompt(result_df):
    sys = "你是考後診斷教練，請分析弱點與建議。"
    mini = result_df[["ID","Tag","Question","Your Answer","Correct","Result"]].head(200)
    user = f"""
以下是作答結果：
{mini.to_csv(index=False)}
請輸出：整體表現、弱項主題、3-5點練習建議。
"""
    ck = _hash("SUMM|" + mini.to_csv(index=False))
    return ck, sys, user


# -----------------------------
# 題庫讀取與正規化
# -----------------------------
def load_bank(file_like):
    try:
        df = pd.read_excel(file_like)
        df.columns = [str(c).strip() for c in df.columns]
        col_map = {
            "編號": "ID", "題號": "ID", "題目": "Question", "題幹": "Question",
            "解答說明": "Explanation", "詳解": "Explanation",
            "標籤": "Tag", "章節": "Tag", "科目": "Tag",
            "圖片": "Image",
            "選項一": "OptionA", "選項二": "OptionB", "選項三": "OptionC",
            "選項四": "OptionD", "選項五": "OptionE",
            "答案": "Answer", "題型": "Type",
        }
        df = df.rename(columns={c: col_map.get(c, c) for c in df.columns})

        option_cols = []
        for c in df.columns:
            lc = str(c).strip()
            if lc.lower().startswith("option"):
                option_cols.append(c)
            elif lc in list("ABCDE"):
                idx = ord(lc) - ord("A")
                df = df.rename(columns={c: f"Option{chr(ord('A')+idx)}"})
                option_cols.append(f"Option{chr(ord('A')+idx)}")

        option_cols = sorted({c for c in df.columns if str(c).lower().startswith("option")})
        if len(option_cols) < 2:
            st.error("題庫至少需要 2 個選項欄位。")
            return None

        for col in ["ID", "Question"]:
            if col not in df.columns:
                st.error(f"缺少必要欄位：{col}")
                return None

        for col in ["Explanation", "Tag", "Image"]:
            if col not in df.columns:
                df[col] = ""

        for oc in option_cols:
            df[oc] = df[oc].fillna("").astype(str)

        if "Answer" not in df.columns or df["Answer"].astype(str).str.strip().eq("").all():
            answers, types = [], []
            for ridx, r in df.iterrows():
                stars = []
                for i, oc in enumerate(option_cols):
                    text = str(r[oc]).strip()
                    if text.startswith("*"):
                        stars.append(chr(ord("A") + i))
                        df.at[ridx, oc] = text.lstrip("* ").strip()
                if len(stars) == 0:
                    answers.append(""); types.append("SC")
                elif len(stars) == 1:
                    answers.append("".join(stars)); types.append("SC")
                else:
                    answers.append("".join(stars)); types.append("MC")
            df["Answer"] = answers
            if "Type" not in df.columns:
                df["Type"] = types

        df["Type"] = df["Type"].astype(str).str.upper().str.strip()
        df["Answer"] = df["Answer"].astype(str).str.upper().str.replace(" ", "", regex=False)

        def has_two_options(row):
            return sum(1 for oc in option_cols if str(row.get(oc, "")).strip()) >= 2
        df = df[df.apply(has_two_options, axis=1)].reset_index(drop=True)

        return df
    except Exception as e:
        st.exception(e)
        return None


# -----------------------------
# 初始化 session 狀態
# -----------------------------
for key, default in [
    ("df", None), ("paper", None), ("start_ts", None), ("time_limit", 0),
    ("answers", {}), ("started", False),
    ("show_results", False), ("results_df", None), ("score_tuple", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# -----------------------------
# 載入題庫（從 GitHub）
# -----------------------------
st.session_state["df"] = load_bank_from_github(load_bank)
if st.session_state["df"] is None or st.session_state["df"].empty:
    st.error("題庫載入失敗或為空，請聯絡管理者。")
    st.stop()

bank = st.session_state["df"]
option_cols = [c for c in bank.columns if c.lower().startswith("option") and bank[c].astype(str).str.strip().ne("").any()]


# -----------------------------
# 考試設定（側欄）
# -----------------------------
with st.sidebar:
    st.header("⚙️ 考試設定")
    use_ai = st.toggle("啟用 AI 助教（Gemini）", value=True)
    if not _gemini_ready():
        use_ai = False
        st.caption("未設定 GEMINI_API_KEY，AI 功能已停用。")

    all_tags = sorted({t.strip() for tags in bank["Tag"].dropna().astype(str) for t in tags.split(";") if t.strip()})
    picked_tags = st.multiselect("選擇標籤", options=all_tags)
    filtered = bank[bank["Tag"].astype(str).apply(lambda s: any(t in [x.strip() for x in s.split(";")] for t in picked_tags))] if picked_tags else bank.copy()

    max_q = len(filtered)
    num_q = st.number_input("抽題數量", min_value=1, max_value=max(1, max_q), value=min(10, max_q), step=1)
    shuffle_options = st.checkbox("隨機打亂選項順序", value=True)
    random_order = st.checkbox("隨機打亂題目順序", value=True)
    show_image = st.checkbox("顯示圖片", value=True)

    time_limit_min = st.number_input("時間限制（分鐘，0=無限制）", min_value=0, max_value=300, value=0)
    st.session_state.time_limit = int(time_limit_min) * 60
    start_btn = st.button("🚀 開始考試", type="primary")


# -----------------------------
# 出題 & 判卷
# -----------------------------
import random

def sample_paper(df, n):
    n = min(n, len(df))
    rows = df.sample(n=n, replace=False, random_state=random.randint(0, 1_000_000))
    if random_order:
        rows = rows.sample(frac=1, random_state=random.randint(0, 1_000_000))

    questions = []
    for _, r in rows.iterrows():
        choices = []
        for idx, col in enumerate(option_cols):
            val = str(r[col]).strip()
            if val:
                lab = chr(ord('A') + idx)
                choices.append((lab, val))
        if shuffle_options:
            random.shuffle(choices)
        ans = set(str(r.get("Answer", "")).upper()) if str(r.get("Answer","")).strip() else set()
        questions.append({
            "ID": r["ID"], "Question": r["Question"],
            "Type": str(r.get("Type","SC")).upper(),
            "Choices": choices, "Answer": ans,
            "Explanation": r.get("Explanation", ""),
            "Image": r.get("Image", ""), "Tag": r.get("Tag", ""),
        })
    return questions

if start_btn:
    st.session_state.paper = sample_paper(filtered, int(num_q))
    st.session_state.start_ts = time.time()
    st.session_state.started = True
    st.session_state.show_results = False


# -----------------------------
# 考試畫面 & 結果畫面
# -----------------------------
if st.session_state.started and st.session_state.paper and not st.session_state.show_results:
    # ===== 出題頁 =====
    paper = st.session_state.paper
    for idx, q in enumerate(paper, start=1):
        st.markdown(f"### Q{idx}. {q['Question']}")
        if show_image and str(q["Image"]).strip():
            st.image(q["Image"], use_container_width=True)

        display = [f"{lab}. {txt}" for lab, txt in q["Choices"]]
        if q["Type"] == "MC":
            picked = st.multiselect("（複選）", options=display, key=f"q_{idx}")
            picked_labels = {opt.split(".", 1)[0] for opt in picked}
        else:
            choice = st.radio("（單選）", options=display, key=f"q_{idx}")
            picked_labels = {choice.split(".", 1)[0]} if choice else set()

        st.session_state["answers"][q["ID"]] = picked_labels

        if use_ai:
            if st.button(f"💡 AI 提示（Q{idx}）", key=f"ai_hint_{idx}"):
                ck, sys, usr = build_hint_prompt(q)
                with st.spinner("AI 產生提示中…"):
                    hint = _gemini_generate_cached(ck, sys, usr)
                st.info(hint)
        st.divider()

    submitted = st.button("📥 交卷並看成績", use_container_width=True)
    timeup = (st.session_state.time_limit > 0 and time.time() - st.session_state.start_ts >= st.session_state.time_limit)

    if submitted or timeup:
        records = []
        correct_count = 0
        for q in paper:
            gold = set(q["Answer"])
            pred = st.session_state["answers"].get(q["ID"], set())
            is_correct = (pred == gold)
            correct_count += int(is_correct)

            mapping = {lab: txt for lab, txt in q["Choices"]}
            def render_set(ss):
                return ", ".join([f"{lab}. {mapping.get(lab,'')}" for lab in sorted(ss)]) if ss else "(未作答)"

            records.append({
                "ID": q["ID"], "Tag": q.get("Tag", ""), "Question": q["Question"],
                "Your Answer": "".join(sorted(list(pred))) or "",
                "Your Answer (text)": render_set(pred),
                "Correct": "".join(sorted(list(gold))),
                "Correct (text)": render_set(gold),
                "Result": "✅ 正確" if is_correct else "❌ 錯誤",
                "Explanation": q.get("Explanation", ""),
            })

        st.session_state.results_df = pd.DataFrame.from_records(records)
        st.session_state.score_tuple = (correct_count, len(paper), round(100 * correct_count / len(paper), 2))
        st.session_state.show_results = True
        st.rerun()

elif st.session_state.started and st.session_state.paper and st.session_state.show_results:
    # ===== 結果頁 =====
    correct_count, total_q, score_pct = st.session_state.score_tuple
    st.success(f"你的分數：{correct_count} / {total_q}（{score_pct}%）")

    result_df = st.session_state.results_df
    st.dataframe(result_df, use_container_width=True)

    csv_bytes = result_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ 下載作答明細（CSV）", data=csv_bytes, file_name="exam_results.csv", mime="text/csv")

    if use_ai:
        st.subheader("🧠 AI 詳解（逐題）")
        for i, q in enumerate(st.session_state.paper, start=1):
            with st.expander
