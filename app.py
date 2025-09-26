
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
# （在 Streamlit Cloud 的 Settings → Secrets 設定以下項目）
#   GH_TOKEN：Personal Access Token（勾 repo）
#   REPO_OWNER：你的 GitHub 帳號
#   REPO_NAME：repo 名稱
#   REPO_BRANCH：main（預設）
#   BANKS_DIR：題庫資料夾，預設 "banks"
#   POINTER_FILE：指標檔，預設 "bank_pointer.json"
#   ADMIN_PASSWORD：管理密碼（任意強密碼）
#   （可選）BANK_FILE：初次啟動的 fallback（例如 "banks/exam_bank.xlsx"）
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
    """取得檔案 SHA（PUT 更新時需要），不存在回 None"""
    try:
        j = _gh_api(f"contents/{path}", params={"ref": GH_BRANCH})
        return j.get("sha")
    except Exception:
        return None

def _gh_put_file(path, content_bytes, message):
    """上傳/更新檔案到 GitHub（自動建資料夾），保留版本歷史"""
    b64 = base64.b64encode(content_bytes).decode("ascii")
    payload = {"message": message, "content": b64, "branch": GH_BRANCH}
    sha = _gh_get_sha(path)
    if sha:
        payload["sha"] = sha
    return _gh_api(f"contents/{path}", method="PUT", json=payload)

@st.cache_data(ttl=300)
def _gh_download_bytes(path):
    """下載檔案內容（用 contents API 的 base64；備援 raw）"""
    j = _gh_api(f"contents/{path}", params={"ref": GH_BRANCH})
    if j.get("encoding") == "base64":
        return base64.b64decode(j["content"])
    raw_url = f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{GH_BRANCH}/{path}"
    return requests.get(raw_url, headers=_gh_headers()).content

def get_current_bank_path():
    """讀取指標檔，取得目前生效題庫路徑"""
    try:
        data = _gh_download_bytes(POINTER_FILE)
        conf = json.loads(data.decode("utf-8"))
        path = conf.get("path")
        if path:
            return path
    except Exception:
        pass
    # fallback：Secrets 指定或預設 banks/exam_bank.xlsx
    return st.secrets.get("BANK_FILE", f"{BANKS_DIR}/exam_bank.xlsx")

def set_current_bank_path(path):
    """更新指標檔，切換目前題庫"""
    if not path.startswith(f"{BANKS_DIR}/"):
        path = f"{BANKS_DIR}/{path}"
    conf = {"path": path}
    _gh_put_file(
        POINTER_FILE,
        json.dumps(conf, ensure_ascii=False, indent=2).encode("utf-8"),
        f"set current bank -> {path}",
    )
    _gh_download_bytes.clear()  # 清快取

def load_bank_from_github(load_bank_fn):
    """下載目前題庫 → 丟進原本的 load_bank(...)"""
    bank_path = get_current_bank_path()
    data = _gh_download_bytes(bank_path)
    df = load_bank_fn(BytesIO(data))
    st.caption(f"使用固定題庫（GitHub）：{bank_path}")
    return df

def list_bank_files():
    """列出 banks/ 下的 .xlsx 題庫清單"""
    try:
        items = _gh_api(f"contents/{BANKS_DIR}", params={"ref": GH_BRANCH})
        return [it["path"] for it in items if it["type"] == "file" and it["name"].lower().endswith(".xlsx")]
    except Exception:
        return []
    
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
    """讀取 Excel 題庫並正規化欄位（支援中文欄名；* 開頭表示正確答案）"""
    try:
        df = pd.read_excel(file_like)
        # 標準化欄名
        df.columns = [str(c).strip() for c in df.columns]

        # 常見中文對應
        col_map = {
            "編號": "ID",
            "題號": "ID",
            "題目": "Question",
            "題幹": "Question",
            "解答說明": "Explanation",
            "詳解": "Explanation",
            "標籤": "Tag",
            "章節": "Tag",
            "科目": "Tag",
            "圖片": "Image",
            "選項一": "OptionA",
            "選項二": "OptionB",
            "選項三": "OptionC",
            "選項四": "OptionD",
            "選項五": "OptionE",
            "答案": "Answer",
            "題型": "Type",
        }
        df = df.rename(columns={c: col_map.get(c, c) for c in df.columns})

        # 偵測選項欄位（OptionA... 或 A/B/C/D/E）
        option_cols = []
        for c in df.columns:
            lc = str(c).strip()
            if lc.lower().startswith("option"):
                option_cols.append(c)
            elif lc in list("ABCDE"):
                # 允許 A/B/C/D/E 當欄名
                idx = ord(lc) - ord("A")
                std = f"Option{chr(ord('A')+idx)}"
                df = df.rename(columns={c: std})
                option_cols.append(std)
            elif lc in ["Ａ","Ｂ","Ｃ","Ｄ","Ｅ"]:
                idx = ["Ａ","Ｂ","Ｃ","Ｄ","Ｅ"].index(lc)
                std = f"Option{chr(ord('A')+idx)}"
                df = df.rename(columns={c: std})
                option_cols.append(std)

        # 若還沒蒐到中文「選項一」等，已於前面 rename 轉為 OptionX
        option_cols = sorted({c for c in df.columns if str(c).lower().startswith("option")})
        if len(option_cols) < 2:
            st.error("題庫至少需要 2 個選項欄位（例如 選項一/選項二 或 OptionA/OptionB）。")
            return None

        # 必要欄位檢查
        for col in ["ID", "Question"]:
            if col not in df.columns:
                st.error(f"缺少必要欄位：{col}")
                return None

        # 補齊可選欄位
        for col in ["Explanation", "Tag", "Image"]:
            if col not in df.columns:
                df[col] = ""

        # NaN → ""，統一字串
        for oc in option_cols:
            df[oc] = df[oc].fillna("").astype(str)

        # 自動從 * 標記推斷 Answer / Type，並把 * 拿掉
        if "Answer" not in df.columns or df["Answer"].astype(str).str.strip().eq("").all():
            answers = []
            types = []
            for ridx, r in df.iterrows():
                stars = []
                for i, oc in enumerate(option_cols):
                    text = str(r[oc]).strip()
                    if text.startswith("*"):
                        stars.append(chr(ord("A") + i))
                        df.at[ridx, oc] = text.lstrip("* ").strip()
                if len(stars) == 0:
                    answers.append("")
                    types.append("SC")  # 預設單選
                elif len(stars) == 1:
                    answers.append("".join(stars))
                    types.append("SC")
                else:
                    answers.append("".join(stars))
                    types.append("MC")
            df["Answer"] = answers
            if "Type" not in df.columns:
                df["Type"] = types

        # 若仍無 Type，預設 SC
        if "Type" not in df.columns:
            df["Type"] = "SC"

        # 正規化
        df["Type"] = df["Type"].astype(str).str.upper().str.strip()
        df["Answer"] = df["Answer"].astype(str).str.upper().str.replace(" ", "", regex=False)

        # 僅保留有至少兩個非空選項的題目
        def has_two_options(row):
            cnt = sum(1 for oc in option_cols if str(row.get(oc, "")).strip())
            return cnt >= 2
        df = df[df.apply(has_two_options, axis=1)].reset_index(drop=True)

        return df
    except Exception as e:
        st.exception(e)
        return None

# -----------------------------
# 初始化 session 狀態
# -----------------------------
for key, default in [
    ("df", None),
    ("paper", None),
    ("start_ts", None),
    ("time_limit", 0),
    ("answers", {}),
    ("started", False),
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
    
    # AI開關
    use_ai = st.sidebar.toggle("啟用 AI 助教（Gemini）", value=True)
    if not _gemini_ready():
        use_ai = False
        st.sidebar.caption("未設定 GEMINI_API_KEY，AI 功能已停用。")


    # 標籤篩選
    all_tags = sorted({t.strip() for tags in bank["Tag"].dropna().astype(str) for t in tags.split(";") if t.strip()})
    picked_tags = st.multiselect("選擇標籤（可多選，不選=全選）", options=all_tags)

    if picked_tags:
        mask = bank["Tag"].astype(str).apply(lambda s: any(t in [x.strip() for x in s.split(";")] for t in picked_tags))
        filtered = bank[mask].copy()
    else:
        filtered = bank.copy()

    max_q = len(filtered)
    num_q = st.number_input("抽題數量", min_value=1, max_value=max(1, max_q), value=min(10, max_q), step=1)
    shuffle_options = st.checkbox("隨機打亂選項順序", value=True)
    random_order = st.checkbox("隨機打亂題目順序", value=True)
    show_image = st.checkbox("顯示圖片（若有）", value=True)

    #出題迴圈中加入提示
    if use_ai:
        if st.button(f"💡 AI 提示（Q{idx}）", key=f"ai_hint_{idx}"):
            ck, sys, usr = build_hint_prompt(q)
            with st.spinner("AI 產生提示中…"):
                hint = _gemini_generate_cached(ck, sys, usr)
            st.info(hint)


    st.divider()
    time_limit_min = st.number_input("時間限制（分鐘，0=無限制）", min_value=0, max_value=300, value=0)
    st.session_state.time_limit = int(time_limit_min) * 60

    start_btn = st.button("🚀 開始考試", type="primary")

# 顯示一些診斷資訊（僅管理者用）
def is_admin():
    try:
        qp = st.query_params
        is_q = qp.get("admin", ["0"])[0] == "1"
    except Exception:
        is_q = False
    return is_q or (st.secrets.get("ADMIN", "0") == "1")

if is_admin():
    st.caption(f"題庫總題數：{len(bank)}；可抽題數（經標籤篩選）：{len(filtered)}；選項欄位：{', '.join(option_cols) or '（無）'}")

# -----------------------------
# 產生試卷
# -----------------------------
import random

def sample_paper(df, n):
    n = min(n, len(df))
    if n <= 0:
        return []

    rows = df.sample(n=n, replace=False, random_state=random.randint(0, 1_000_000))
    if random_order:
        rows = rows.sample(frac=1, random_state=random.randint(0, 1_000_000))

    questions = []
    for _, r in rows.iterrows():
        # 建立 (label, text) 選項
        choices = []
        letters = []
        for idx, col in enumerate(option_cols):
            val = str(r[col]).strip()
            if val:
                lab = chr(ord('A') + idx)
                choices.append((lab, val))
                letters.append(lab)

        if shuffle_options:
            random.shuffle(choices)

        # 正解（集合）
        ans = set(str(r.get("Answer", "")).upper()) if str(r.get("Answer","")).strip() else set()

        questions.append({
            "ID": r["ID"],
            "Question": r["Question"],
            "Type": str(r.get("Type","SC")).upper(),
            "Choices": choices,            # list[(label, text)]
            "Answer": ans,                 # set of letters
            "Explanation": r.get("Explanation", ""),
            "Image": r.get("Image", ""),
            "Tag": r.get("Tag", ""),
        })
    return questions

# 啟考（不用 rerun，改旗標）
if start_btn:
    st.session_state.paper = sample_paper(filtered, int(num_q))
    st.session_state.start_ts = time.time()
    st.session_state.started = True

# 進入考試畫面
if st.session_state.started and st.session_state.paper:
    paper = st.session_state.paper

    col_left, col_right = st.columns([1,1])
    with col_left:
        st.subheader("試卷")
    with col_right:
        if st.session_state.time_limit > 0:
            elapsed = int(time.time() - st.session_state.start_ts)
            remain = max(0, st.session_state.time_limit - elapsed)
            mm, ss = divmod(remain, 60)
            st.metric("剩餘時間", f"{mm:02d}:{ss:02d}")
            if remain == 0:
                st.warning("時間到！請繳卷。")

    # 作答介面
    answers_key = "answers"
    if answers_key not in st.session_state:
        st.session_state[answers_key] = {}

    for idx, q in enumerate(paper, start=1):
        st.markdown(f"### Q{idx}. {q['Question']}")
        if show_image and str(q["Image"]).strip():
            try:
                st.image(q["Image"], use_container_width=True)
            except Exception:
                st.info("圖片載入失敗，請確認路徑或網址。")

        display = [f"{lab}. {txt}" for lab, txt in q["Choices"]]

        if q["Type"] == "MC":
            picked = st.multiselect("（複選）選擇所有正確選項：", options=display, key=f"q_{idx}")
            picked_labels = {opt.split(".", 1)[0] for opt in picked}
        else:
            choice = st.radio("（單選）選擇一個答案：", options=display, key=f"q_{idx}")
            picked_labels = {choice.split(".", 1)[0]} if choice else set()

        st.session_state[answers_key][q["ID"]] = picked_labels
        st.divider()

    submitted = st.button("📥 交卷並看成績", use_container_width=True)

    # 自動判卷（時間到也算）
    # 自動判卷（時間到也算）
    if submitted or (st.session_state.time_limit > 0 and time.time() - st.session_state.start_ts >= st.session_state.time_limit):
        records = []
        correct_count = 0
        for q in paper:
            gold = set(q["Answer"])
            pred = st.session_state[answers_key].get(q["ID"], set())
            is_correct = (pred == gold)
            correct_count += int(is_correct)

            # 顯示友善的「A. 文字」格式
            mapping = {lab: txt for lab, txt in q["Choices"]}
            def render_set(ss):
                if not ss:
                    return "(未作答)"
                ordered = sorted(list(ss))
                return ", ".join([f"{lab}. {mapping.get(lab, '')}" for lab in ordered])

            records.append({
                "ID": q["ID"],
                "Tag": q.get("Tag", ""),
                "Question": q["Question"],
                "Your Answer": "".join(sorted(list(pred))) or "",
                "Your Answer (text)": render_set(pred),
                "Correct": "".join(sorted(list(gold))),
                "Correct (text)": render_set(gold),
                "Result": "✅ 正確" if is_correct else "❌ 錯誤",
                "Explanation": q.get("Explanation", ""),
            })

        # 分數與結果表
        score_pct = round(100 * correct_count / len(paper), 2)
        st.success(f"你的分數：{correct_count} / {len(paper)}（{score_pct}%）")
        result_df = pd.DataFrame.from_records(records)
        st.dataframe(result_df, use_container_width=True)

        # 下載 CSV
        csv_bytes = result_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 下載作答明細（CSV）", data=csv_bytes, file_name="exam_results.csv", mime="text/csv")

        # -----------------------------
        # 🧠 AI 詳解（逐題） + 📊 AI 考後總結（只顯示一次）
        # -----------------------------
        if 'use_ai' in locals() and use_ai:
            st.subheader("🧠 AI 詳解（逐題）")
            for i, q in enumerate(paper, start=1):
                with st.expander(f"Q{i}：{q['Question'][:40]}..."):
                    if st.button(f"產生詳解（Q{i}）", key=f"ai_explain_{i}"):
                        ck, sys, usr = build_explain_prompt(q)  # 會優先參考題庫的「解答說明/Explanation」
                        with st.spinner("AI 產生詳解中…"):
                            expl = _gemini_generate_cached(ck, sys, usr)
                        st.write(expl)

            st.subheader("📊 AI 考後總結")
            if st.button("產出弱項分析與建議"):
                ck, sys, usr = build_summary_prompt(result_df)
                with st.spinner("AI 分析中…"):
                    summ = _gemini_generate_cached(ck, sys, usr)
                st.write(summ)


        # 再考一次（重置旗標）
        if st.button("🔁 再考一次", type="secondary"):
            st.session_state.paper = None
            st.session_state.start_ts = None
            st.session_state[answers_key] = {}
            st.session_state.started = False

# -----------------------------
# 題庫管理（管理者）
# -----------------------------
with st.sidebar.expander("🛠 題庫管理（管理者）", expanded=False):
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    pwd = st.text_input("管理密碼", type="password")
    if st.button("登入"):
        if pwd == st.secrets.get("ADMIN_PASSWORD", ""):
            st.session_state.admin_ok = True
            st.success("已登入")
        else:
            st.error("密碼錯誤")

    if st.session_state.admin_ok:
        st.write("### 上傳新題庫")
        up = st.file_uploader("選擇 Excel 題庫（.xlsx）", type=["xlsx"])
        name = st.text_input("儲存檔名（僅檔名，不含資料夾）", value="law_exam.xlsx")
        set_now = st.checkbox("上傳後設為目前題庫", value=True)

        if st.button("上傳"):
            if up and name:
                dest = f"{BANKS_DIR}/{name}"
                _gh_put_file(dest, up.getvalue(), f"upload bank {name}")
                if set_now:
                    set_current_bank_path(dest)
                _gh_download_bytes.clear()
                st.success(f"已上傳：{dest}" + ("，並已切換" if set_now else ""))

        st.write("### 切換歷史題庫")
        opts = list_bank_files()
        if opts:
            cur = get_current_bank_path()
            idx = opts.index(cur) if cur in opts else 0
            pick = st.selectbox("選擇題庫", options=opts, index=idx)
            if st.button("套用選擇的題庫"):
                set_current_bank_path(pick)
                _gh_download_bytes.clear()
                st.success(f"已切換為：{pick}")
        else:
            st.info("banks/ 資料夾目前沒有 .xlsx。")
