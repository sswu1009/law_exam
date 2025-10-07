import os
import json
import base64
import time
import random
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
st.set_page_config(page_title="錠嵂AI考照", layout="wide")
st.title(" 錠嵂AI考照機器人")
with st.expander("📖 使用說明", expanded=True):
    st.markdown("""
    歡迎使用 **錠嵂保經AI模擬考試機器人** 🎉

    **操作方式：**
    1. 在左側設定抽題數量、是否隨機打亂題目/選項。
    2. 點擊 🚀 開始考試，進入答題畫面。
    3. 答題完成後，按「📥 交卷並看成績」查看分數與詳解。
    4. 若啟用 AI 助教，可使用：
       - 💡 AI 提示：答題時給予思考方向。
       - 🤖 AI 詳解：交卷後提供逐題解析。
       - 📊 AI 總結：**交卷後**提供弱項分析與建議。
    5. 可於結果頁下載作答明細（CSV）。

    ⚠️ 管理者可於側欄 **題庫管理** 上傳或切換題庫。
    """)


# =========================================================
# GitHub 後台設定（放在 Streamlit Secrets）
#   GH_TOKEN：Personal Access Token（需 repo 權限）
#   REPO_OWNER：GitHub 帳號
#   REPO_NAME：repo 名稱
#   REPO_BRANCH：main（預設）
#   BANKS_DIR：題庫資料夾，這裡預設 "bank"（你的實際結構）
#   POINTER_FILE：指標檔，預設 "bank_pointer.json"
#   ADMIN_PASSWORD：管理密碼
#   （可選）BANK_FILE：舊版單題庫 fallback（例如 "bank/exam_bank.xlsx"）
# =========================================================
GH_OWNER     = st.secrets.get("REPO_OWNER")
GH_REPO      = st.secrets.get("REPO_NAME")
GH_BRANCH    = st.secrets.get("REPO_BRANCH", "main")
GH_TOKEN     = st.secrets.get("GH_TOKEN")
BANKS_DIR    = st.secrets.get("BANKS_DIR", "bank")   # ← 已調成 bank
POINTER_FILE = st.secrets.get("POINTER_FILE", "bank_pointer.json")

# 類型清單（符合你的資料夾）
BANK_TYPES   = ["人身", "投資型", "外幣"]


def _type_dir(t: str) -> str:
    # bank/人身、bank/投資型、bank/外幣
    return f"{BANKS_DIR}/{t}"

def _gh_headers():
    h = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        h["Authorization"] = f"Bearer {GH_TOKEN}"
    return h

def _gh_write_ready() -> tuple[bool, str]:
    missing = []
    if not GH_OWNER:  missing.append("REPO_OWNER")
    if not GH_REPO:   missing.append("REPO_NAME")
    if not GH_BRANCH: missing.append("REPO_BRANCH")
    if not GH_TOKEN:  missing.append("GH_TOKEN (需要寫入權限)")
    if missing:
        return False, "缺少 secrets：" + ", ".join(missing)
    return True, ""

def _require_gh_write_or_warn():
    ok, msg = _gh_write_ready()
    if not ok:
        st.warning("GitHub 寫入未啟用——" + msg)
    return ok

def _gh_api(path, method="GET", **kwargs):
    url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/{path}"
    r = requests.request(method, url, headers=_gh_headers(), **kwargs)
    if r.status_code >= 400:
        snippet = r.text[:300].replace("\n"," ")
        raise RuntimeError(f"GitHub API {method} {path} -> {r.status_code}: {snippet}")
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

# ---- 指標檔（新版相容舊版） ----
def _read_pointer():
    try:
        data = _gh_download_bytes(POINTER_FILE)
        return json.loads(data.decode("utf-8"))
    except Exception:
        return {}

def _write_pointer(obj: dict):
    if not _require_gh_write_or_warn():
        return
    _gh_put_file(
        POINTER_FILE,
        json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"),
        "update bank pointers"
    )
    _gh_download_bytes.clear()

def get_current_bank_path(bank_type: str | None = None):
    """
    回傳某類型目前題庫 path。
    - 新格式：{"current": {"人身": "...xlsx", "投資型": "...xlsx", "外幣": "...xlsx"}}
    - 舊格式：{"path": "...xlsx"} 相容（未指定 bank_type 時回舊值）
    - 若該類型未設定，回傳 fallback（Secrets 的 BANK_FILE 或 bank/exam_bank.xlsx）
    """
    conf = _read_pointer()
    current = conf.get("current")
    if isinstance(current, dict):
        if bank_type:
            p = current.get(bank_type)
            if p:
                return p
    legacy = conf.get("path")
    if legacy and not bank_type:
        return legacy
    return st.secrets.get("BANK_FILE", f"{BANKS_DIR}/exam_bank.xlsx")

def set_current_bank_path(bank_type: str, path: str):
    """設定某類型目前題庫路徑（自動補上 bank/<type>/ 前綴）"""
    if not _require_gh_write_or_warn():
        return
    if not path.startswith(f"{BANKS_DIR}/"):
        path = f"{_type_dir(bank_type)}/{path}"
    conf = _read_pointer()
    if "current" not in conf or not isinstance(conf.get("current"), dict):
        conf["current"] = {}
    conf["current"][bank_type] = path
    try:
        _write_pointer(conf)
    except Exception as e:
        st.warning(f"更新 {POINTER_FILE} 失敗：{e}")

def _migrate_pointer_prefix_if_needed():
    """自動將指標檔中的 'banks/' 前綴改為目前的 BANKS_DIR（bank/）。"""
    conf = _read_pointer()
    changed = False

    if isinstance(conf.get("path"), str) and conf["path"].startswith("banks/"):
        conf["path"] = conf["path"].replace("banks/", f"{BANKS_DIR}/", 1)
        changed = True

    cur = conf.get("current")
    if isinstance(cur, dict):
        for k, p in list(cur.items()):
            if isinstance(p, str) and p.startswith("banks/"):
                cur[k] = p.replace("banks/", f"{BANKS_DIR}/", 1)
                changed = True

    if changed:
        try:
            _write_pointer(conf)
        except Exception as e:
            st.warning(f"自動遷移 {POINTER_FILE} 失敗：{e}")

# 啟動時先嘗試遷移
_migrate_pointer_prefix_if_needed()

def list_bank_files(bank_type: str | None = None):
    """列出 bank/ 或 bank/<type>/ 下的 .xlsx 題庫清單"""
    try:
        if bank_type:
            folder = _type_dir(bank_type)
            items = _gh_api(f"contents/{folder}", params={"ref": GH_BRANCH})
            return [it["path"] for it in items if it["type"] == "file" and it["name"].lower().endswith(".xlsx")]
        else:
            items = _gh_api(f"contents/{BANKS_DIR}", params={"ref": GH_BRANCH})
            return [it["path"] for it in items if it["type"] == "file" and it["name"].lower().endswith(".xlsx")]
    except Exception:
        return []


# -----------------------------
# AI 提示詞建構（優先參考題庫「解答說明 / Explanation」）
# -----------------------------
def build_hint_prompt(q: dict):
    sys = (
        "你是考試助教，只能提供方向提示，嚴禁輸出答案代號或逐字答案。"
        "優先參考題庫的解答說明；不足再補充概念或排除法。"
    )
    expl = (q.get("Explanation") or "").strip()
    user = f"""
題目: {q['Question']}
選項:
{chr(10).join([f"{lab}. {txt}" for lab,txt in q['Choices']])}
題庫解答說明（僅供參考、不可爆雷）：{expl if expl else "（無）"}
請用 1-2 句提示重點，不要爆雷。
"""
    ck = _hash("HINT|" + q["Question"] + "|" + expl)
    return ck, sys, user

def build_explain_prompt(q: dict):
    sys = "你是解題老師，優先引用題庫解答說明，逐項說明正確與錯誤，保持精簡。"
    expl = (q.get("Explanation") or "").strip()
    ans_letters = "".join(sorted(list(q.get("Answer", set()))))
    user = f"""
題目: {q['Question']}
選項:
{chr(10).join([f"{lab}. {txt}" for lab,txt in q['Choices']])}
正解: {ans_letters or "（無）"}
題庫解答說明：{expl if expl else "（無）"}
"""
    ck = _hash("EXPL|" + q["Question"] + "|" + ans_letters)
    return ck, sys, user

def build_summary_prompt(result_df):
    sys = "你是考後診斷教練，請分析弱點與建議。"
    mini = result_df[["ID","Tag","Question","Your Answer","Correct","Result"]].head(200)
    user = f"""
以下是作答結果（最多 200 題）：
{mini.to_csv(index=False)}
請輸出：整體表現、弱項主題、3-5點練習建議（條列）。
"""
    ck = _hash("SUMM|" + mini.to_csv(index=False))
    return ck, sys, user


# -----------------------------
# 題庫讀取與正規化（支援多工作表）
# -----------------------------
def normalize_bank_df(df: pd.DataFrame, sheet_name: str | None = None, source_file: str | None = None) -> pd.DataFrame:
    """把單一 DataFrame 正規化成題庫格式；若 Tag 為空則用 sheet_name 補；加上 SourceFile/SourceSheet。"""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_map = {
        "編號": "ID", "題號": "ID",
        "題目": "Question", "題幹": "Question",
        "解答說明": "Explanation", "解釋說明": "Explanation", "詳解": "Explanation",
        "標籤": "Tag", "章節": "Tag", "科目": "Tag",
        "圖片": "Image",
        "選項一": "OptionA", "選項二": "OptionB", "選項三": "OptionC",
        "選項四": "OptionD", "選項五": "OptionE",
        "答案": "Answer",
        "題型": "Type",
    }
    df = df.rename(columns={c: col_map.get(c, c) for c in df.columns})

    option_cols = []
    for c in df.columns:
        lc = str(c).strip()
        if lc.lower().startswith("option"):
            option_cols.append(c)
        elif lc in list("ABCDE"):
            idx = ord(lc) - ord("A")
            std = f"Option{chr(ord('A')+idx)}"
            df = df.rename(columns={c: std})
            option_cols.append(std)
        elif lc in ["Ａ","Ｂ","Ｃ","Ｄ","Ｅ"]:
            idx = ["Ａ","Ｂ","Ｃ","Ｄ","Ｅ"].index(lc)
            std = f"Option{chr(ord('A')+idx)}"
            df = df.rename(columns={c: std})
            option_cols.append(std)

    option_cols = sorted({c for c in df.columns if str(c).lower().startswith("option")})
    if len(option_cols) < 2:
        return pd.DataFrame()

    for col in ["ID", "Question"]:
        if col not in df.columns:
            return pd.DataFrame()

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
                answers.append("")
                types.append("SC")
            elif len(stars) == 1:
                answers.append("".join(stars))
                types.append("SC")
            else:
                answers.append("".join(stars))
                types.append("MC")
        df["Answer"] = answers
        if "Type" not in df.columns:
            df["Type"] = types

    if "Type" not in df.columns:
        df["Type"] = "SC"

    df["Type"] = df["Type"].astype(str).str.upper().str.strip()
    df["Answer"] = df["Answer"].astype(str).str.upper().str.replace(" ", "", regex=False)

    def has_two_options(row):
        cnt = sum(1 for oc in option_cols if str(row.get(oc, "")).strip())
        return cnt >= 2
    df = df[df.apply(has_two_options, axis=1)].reset_index(drop=True)

    # 空 Tag 用 sheet 名補
    if "Tag" not in df.columns:
        df["Tag"] = ""
    if sheet_name:
        df["Tag"] = df["Tag"].astype(str)
        df.loc[df["Tag"].str.strip().eq(""), "Tag"] = sheet_name

    # 來源追蹤
    df["SourceFile"] = (source_file or "").strip()
    df["SourceSheet"] = (sheet_name or "").strip()

    return df

def load_bank(file_like):
    """
    讀取 Excel 題庫。如果有多個工作表，會把每個工作表當成一份題庫讀入並合併。
    - 自動補 Tag＝工作表名稱（若原本 Tag 為空）
    - 會加上 SourceFile / SourceSheet 欄位。
    """
    try:
        xls = pd.ExcelFile(file_like)
        dfs = []
        try:
            source_file = getattr(file_like, "name", None) or ""
        except Exception:
            source_file = ""
        for sh in xls.sheet_names:
            raw = pd.read_excel(xls, sheet_name=sh)
            norm = normalize_bank_df(raw, sheet_name=sh, source_file=source_file)
            if not norm.empty:
                dfs.append(norm)
        if not dfs:
            st.error("題庫載入失敗或為空（所有工作表都不符合格式）。")
            return None
        return pd.concat(dfs, ignore_index=True)
    except Exception as e:
        try:
            df = pd.read_excel(file_like)
            norm = normalize_bank_df(df, sheet_name=None, source_file=getattr(file_like, "name", None) or "")
            if not norm.empty:
                return norm
            st.error("題庫載入失敗或為空。")
            return None
        except Exception:
            st.exception(e)
            return None

def load_banks_from_github(load_bank_fn, paths: list[str]) -> pd.DataFrame | None:
    """一次載入多個 xlsx 並合併（欄位需一致或相容）"""
    dfs = []
    for p in paths:
        try:
            data = _gh_download_bytes(p)
            bio = BytesIO(data)
            try:
                bio.name = p  # 讓 load_bank 寫入 SourceFile
            except Exception:
                pass
            df = load_bank_fn(bio)
            if df is None or df.empty:
                continue
            dfs.append(df)
        except Exception:
            continue
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)

def load_bank_from_github(load_bank_fn, bank_path_or_paths):
    """接受 str（單一檔）或 list[str]（多檔合併）"""
    if isinstance(bank_path_or_paths, list):
        df = load_banks_from_github(load_bank_fn, bank_path_or_paths)
        if df is None:
            st.error("題庫載入失敗或為空，請聯絡管理者。")
            st.stop()
        st.caption(f"使用固定題庫（GitHub 多檔合併）：{len(bank_path_or_paths)} 檔")
        return df
    else:
        bank_path = bank_path_or_paths
        data = _gh_download_bytes(bank_path)
        bio = BytesIO(data)
        try:
            bio.name = bank_path
        except Exception:
            pass
        df = load_bank_fn(bio)
        st.caption(f"使用固定題庫（GitHub）：{bank_path}")
        return df


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
    ("show_results", False),
    ("results_df", None),
    ("score_tuple", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

def is_admin():
    try:
        qp = st.query_params
        is_q = qp.get("admin", ["0"])[0] == "1"
    except Exception:
        is_q = False
    return is_q or (st.secrets.get("ADMIN", "0") == "1")


# -----------------------------
# 考試設定（側欄）
# -----------------------------
with st.sidebar:
    st.header("⚙️ 考試設定")

    
    # 出題模式切換
    exam_mode = st.radio('出題模式', ['練習模式', '模擬考模式'], index=1)
# AI 開關
    use_ai = st.toggle("啟用 AI 助教（Gemini）", value=True)
    if not _gemini_ready():
        use_ai = False
        st.caption("未設定 GEMINI_API_KEY，AI 功能已停用。")

    # 類型與題庫選擇
    st.subheader("題庫來源")
    pick_type = st.selectbox("選擇類型", options=BANK_TYPES, index=0)
    merge_all = st.checkbox("合併載入此類型下所有題庫檔", value=False)

    bank_source = None
    type_files = list_bank_files(pick_type)

    if merge_all:
        bank_source = type_files
        st.caption(f"將合併 {len(type_files)} 檔")
        if not type_files:
            st.warning(f"{pick_type} 類型目前沒有題庫檔")
    else:
        current_path = get_current_bank_path(pick_type)
        idx = type_files.index(current_path) if current_path in type_files and type_files else 0
        pick_file = st.selectbox("選擇題庫檔", options=type_files or ["（尚無檔案）"], index=idx if type_files else 0)
        bank_source = pick_file if type_files else None

    # 載入題庫
    if bank_source:
        st.session_state["df"] = load_bank_from_github(load_bank, bank_source)
    else:
        fallback_path = get_current_bank_path()  # 舊版 path fallback
        st.session_state["df"] = load_bank_from_github(load_bank, fallback_path)

    if st.session_state["df"] is None or st.session_state["df"].empty:
        st.error("題庫載入失敗或為空，請聯絡管理者。")
        st.stop()

    bank = st.session_state["df"]
    option_cols = [c for c in bank.columns if c.lower().startswith("option") and bank[c].astype(str).str.strip().ne("").any()]

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

    st.divider()
    time_limit_min = st.number_input("時間限制（分鐘，0=無限制）", min_value=0, max_value=300, value=0)
    st.session_state.time_limit = int(time_limit_min) * 60

    start_btn = st.button("🚀 開始考試", type="primary")

    # 僅在單檔模式下，把選擇寫回指標檔（避免把 list 當路徑）
    if start_btn and (not merge_all) and isinstance(bank_source, str):
        try:
            set_current_bank_path(pick_type, bank_source)
        except Exception as e:
            st.warning(f"無法寫回指標檔（{POINTER_FILE}），將以當前選擇直接出題。")
            st.info(str(e))


# -----------------------------
# 產生試卷
# -----------------------------
def sample_paper(df, n):
    n = min(n, len(df))
    if n <= 0:
        return []

    # 先抽題、再依需求打亂題目順序
    rows = df.sample(n=n, replace=False, random_state=random.randint(0, 1_000_000))
    if random_order:
        rows = rows.sample(frac=1, random_state=random.randint(0, 1_000_000))

    questions = []
    for _, r in rows.iterrows():
        # 1) 以「原始標籤」建立清單：[(A, txtA), (B, txtB), ...]，只收非空選項
        items = []
        for i, col in enumerate(option_cols):
            txt = str(r.get(col, "")).strip()
            if txt:
                orig_lab = chr(ord('A') + i)  # 原始（未打亂）標籤
                items.append((orig_lab, txt))

        # 2) 如需就地打亂（保留 orig_lab）
        if shuffle_options:
            random.shuffle(items)

        # 3) 產生新選項與映射：原始標籤 -> 新標籤
        choices = []
        orig_to_new = {}
        for idx, (orig_lab, txt) in enumerate(items):
            new_lab = chr(ord('A') + idx)    # 新標籤（展示用）
            choices.append((new_lab, txt))
            orig_to_new[orig_lab] = new_lab

        # 4) 讀取正解（原始字母），同步映射成「新標籤」
        raw_ans = str(r.get("Answer", "")).upper().strip()
        orig_ans_letters = set(raw_ans) if raw_ans else set()
        # 僅保留存在的原始標籤，並轉成新標籤
        new_ans = {orig_to_new[a] for a in orig_ans_letters if a in orig_to_new}

        # 5) 題目型態
        qtype = str(r.get("Type", "SC")).upper()

        # 6) 組裝題目
        questions.append({
            "ID": r["ID"],
            "Question": r["Question"],
            "Type": qtype,
            "Choices": choices,                # [(新標籤, 文字)]
            "Answer": new_ans,                 # {新標籤集合}
            "Explanation": r.get("Explanation", ""),
            "Image": r.get("Image", ""),
            "Tag": r.get("Tag", ""),
            # 若你有用多工作表功能，這兩行能把來源帶到結果表
            "SourceFile": r.get("SourceFile", ""),
            "SourceSheet": r.get("SourceSheet", ""),
        })

    return questions

# ============================================================
# 練習模式（逐題出題 + AI提示 + 即時判分 + 手動下一題）
# ============================================================
def show_practice_mode(paper, use_ai=True, show_image=True):
    import streamlit as st
    import time

    # 初始化進度
    if "practice_idx" not in st.session_state:
        st.session_state.practice_idx = 0
        st.session_state.practice_correct = 0
        st.session_state.practice_answers = {}

    i = st.session_state.practice_idx
    q = paper[i]
    st.markdown(f"### 第 {i+1} / {len(paper)} 題")
    st.markdown(q["Question"])

    # 圖片
    if show_image and str(q.get("Image","")).strip():
        try:
            st.image(q["Image"], use_container_width=True)
        except Exception:
            st.info("圖片載入失敗。")

    # AI 提示（考前提示，非詳解）
    if use_ai:
        if st.button(f"💡 看不懂題目嗎？AI提示（Q{i+1}）", key=f"ai_hint_practice_{i}"):
            ck, sys, usr = build_hint_prompt(q)
            with st.spinner("AI 產生提示中…"):
                hint = _gemini_generate_cached(ck, sys, usr)
            st.session_state.setdefault("hints", {})[q["ID"]] = hint
        if q["ID"] in st.session_state.get("hints", {}):
            st.info(st.session_state["hints"][q["ID"]])

    # 選項
    display = [f"{lab}. {txt}" for lab, txt in q["Choices"]]
    if q["Type"] == "MC":
        picked = st.multiselect("（複選）選擇所有正確選項：", options=display, key=f"practice_pick_{i}")
        picked_labels = {opt.split(".", 1)[0] for opt in picked}
    else:
        choice = st.radio("（單選）選擇一個答案：", options=display, key=f"practice_pick_{i}")
        picked_labels = {choice.split(".", 1)[0]} if choice else set()

    # 提交本題
    if st.button("提交這題", key=f"practice_submit_{i}"):
        gold = set(q["Answer"])
        st.session_state.practice_answers[q["ID"]] = picked_labels
        if picked_labels == gold:
            st.success("✅ 答對了！")
            st.session_state.practice_correct += 1
        else:
            st.error(f"❌ 答錯了。正確：{', '.join(sorted(list(gold))) or '(空)'}")
            if str(q.get("Explanation","")).strip():
                st.caption(f"📖 題庫詳解：{q['Explanation']}")

    # 下一題/完成
    cols = st.columns([1,1])
    with cols[0]:
        if st.button("➡️ 下一題", key=f"practice_next_{i}"):
            if i < len(paper) - 1:
                st.session_state.practice_idx += 1
                st.rerun()
            else:
                st.success(f"🎉 完成練習：{st.session_state.practice_correct}/{len(paper)}")
    with cols[1]:
        if st.button("🔁 重新練習"):
            for k in ["practice_idx","practice_correct","practice_answers"]:
                st.session_state.pop(k, None)
            st.rerun()

# 啟考（建立試卷 & 狀態）
if start_btn:
    st.session_state.paper = sample_paper(filtered, int(num_q))
    st.session_state.start_ts = time.time()
    st.session_state.answers = {}
    st.session_state.started = True
    st.session_state.show_results = False
    st.session_state.results_df = None
    st.session_state.score_tuple = None


# -----------------------------
# 出題頁（依模式分流）
# -----------------------------
if st.session_state.started and st.session_state.paper and not st.session_state.show_results:
    if 'exam_mode' in locals() and exam_mode == '練習模式':
        show_practice_mode(st.session_state.paper, use_ai=use_ai, show_image=show_image)
    else:
    # ===== 出題頁 =====
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

        answers_key = "answers"
        if answers_key not in st.session_state:
            st.session_state[answers_key] = {}

    # 新增：每題 AI 提示的狀態儲存
    hints_key = "hints"
    if hints_key not in st.session_state:
        st.session_state[hints_key] = {}

    for idx, q in enumerate(paper, start=1):
        st.markdown(f"### Q{idx}. {q['Question']}")
        if show_image and str(q["Image"]).strip():
            try:
                st.image(q["Image"], use_container_width=True)
            except Exception:
                st.info("圖片載入失敗，請確認路徑或網址。")

        # === 先顯示提示按鈕與提示（在選項之上）===
        if use_ai:
            # 按一下就寫進 session_state，之後每次重跑都會看到
            if st.button(f"💡 看不懂題目嗎?AI來提示你（Q{idx}）", key=f"ai_hint_{idx}"):
                ck, sys, usr = build_hint_prompt(q)
                with st.spinner("AI 產生提示中…"):
                    hint = _gemini_generate_cached(ck, sys, usr)
                st.session_state[hints_key][q["ID"]] = hint

            # 若已有提示，顯示在題目下、選項上
            if q["ID"] in st.session_state[hints_key]:
                st.info(st.session_state[hints_key][q["ID"]])

        # === 再顯示選項 ===
        display = [f"{lab}. {txt}" for lab, txt in q["Choices"]]

        if q["Type"] == "MC":
            picked = st.multiselect("（複選）選擇所有正確選項：", options=display, key=f"q_{idx}")
            picked_labels = {opt.split(".", 1)[0] for opt in picked}
        else:
            choice = st.radio("（單選）選擇一個答案：", options=display, key=f"q_{idx}")
            picked_labels = {choice.split(".", 1)[0]} if choice else set()

        st.session_state[answers_key][q["ID"]] = picked_labels

        st.divider()

    # 交卷
    submitted = st.button("📥 交卷並看成績", use_container_width=True)
    timeup = (st.session_state.time_limit > 0 and time.time() - st.session_state.start_ts >= st.session_state.time_limit)

    if submitted or timeup:
        # 判卷
        records = []
        correct_count = 0
        for q in paper:
            gold = set(q["Answer"])
            pred = st.session_state[answers_key].get(q["ID"], set())
            is_correct = (pred == gold)
            correct_count += int(is_correct)

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
                "SourceFile": q.get("SourceFile","") if isinstance(q.get("SourceFile",""), str) else "",
                "SourceSheet": q.get("SourceSheet","") if isinstance(q.get("SourceSheet",""), str) else "",
            })

        score_pct = round(100 * correct_count / len(paper), 2)
        st.session_state.results_df = pd.DataFrame.from_records(records)
        st.session_state.score_tuple = (correct_count, len(paper), score_pct)
        st.session_state.show_results = True
        st.rerun()

elif st.session_state.started and st.session_state.paper and st.session_state.show_results:
    # ===== 結果頁 =====
    correct_count, total_q, score_pct = st.session_state.score_tuple
    st.success(f"你的分數：{correct_count} / {total_q}（{score_pct}%）")

    result_df = st.session_state.results_df
    st.dataframe(result_df, use_container_width=True)

    # 下載 CSV
    csv_bytes = result_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ 下載作答明細（CSV）", data=csv_bytes, file_name="exam_results.csv", mime="text/csv")

    # === 題目詳解（依作答結果上色 + 展開詳解） ===
    st.subheader("🧠 AI 詳解（逐題，依作答結果著色）")

    answers_key = "answers"

    def _fmt_letters(letters_set: set[str]) -> str:
        return ", ".join(sorted(list(letters_set))) if letters_set else "(未作答)"

    for i, q in enumerate(st.session_state.paper, start=1):
        gold = set(q["Answer"])
        pred = st.session_state.get(answers_key, {}).get(q["ID"], set())
        is_correct = (pred == gold)

        border = "#34a853" if is_correct else "#d93025"
        glow   = "0 0 12px"
        title  = f"Q{i}｜{'✅ 正確' if is_correct else '❌ 錯誤'}｜你的答案：{_fmt_letters(pred)}"

        st.markdown(
            f"""
            <div style="
                border:2px solid {border};
                box-shadow:{glow} {border};
                background:transparent;
                border-radius:12px;
                padding:12px 16px;
                margin:10px 0;
                font-weight:700;">
                {title}
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander("展開詳解"):
            st.markdown(
                f"<div style='white-space: pre-wrap'><strong>題目：</strong>{q['Question']}</div>",
                unsafe_allow_html=True
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

            if use_ai:
                if st.button(f"🤖 產生 AI 詳解（Q{i}）", key=f"ai_explain_colored_{i}"):
                    ck, sys, usr = build_explain_prompt(q)
                    with st.spinner("AI 產生詳解中…"):
                        expl = _gemini_generate_cached(ck, sys, usr)
                    st.success(expl)

    # === 📊 AI 考後總結（僅結果頁顯示） ===
    if use_ai:
        st.subheader("📊 AI 考後總結")
        if st.button("產出弱項分析與建議", key="ai_summary_btn"):
            ck, sys, usr = build_summary_prompt(result_df)
            with st.spinner("AI 分析中…"):
                summ = _gemini_generate_cached(ck, sys, usr)
            st.write(summ)

    # 再考一次（重置旗標）
    if st.button("🔁 再考一次", type="secondary"):
        st.session_state.paper = None
        st.session_state.start_ts = None
        st.session_state.answers = {}
        st.session_state.started = False
        st.session_state.show_results = False
        st.session_state.results_df = None
        st.session_state.score_tuple = None
        st.rerun()


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
        up_type = st.selectbox("上傳到哪個類型？", options=BANK_TYPES, index=0)
        up = st.file_uploader("選擇 Excel 題庫（.xlsx）", type=["xlsx"])
        name = st.text_input("儲存檔名（僅檔名，不含資料夾）", value="bank.xlsx")
        set_now = st.checkbox("上傳後設為該類型目前題庫", value=True)

        if st.button("上傳"):
            if up and name:
                dest = f"{_type_dir(up_type)}/{name}"
                try:
                    _gh_put_file(dest, up.getvalue(), f"upload bank {name} -> {up_type}")
                    if set_now:
                        set_current_bank_path(up_type, dest)
                    _gh_download_bytes.clear()
                    st.success(f"已上傳：{dest}" + ("，並已切換" if set_now else ""))
                except Exception as e:
                    st.error(f"上傳失敗：{e}")

        st.write("### 切換歷史題庫（依類型）")
        sel_type = st.selectbox("選擇類型", options=BANK_TYPES, index=0, key="sel_type_switch")
        opts = list_bank_files(sel_type)
        if opts:
            cur = get_current_bank_path(sel_type)
            idx = opts.index(cur) if cur in opts else 0
            pick = st.selectbox("選擇題庫", options=opts, index=idx, key="pick_bank_switch")
            if st.button("套用選擇的題庫"):
                set_current_bank_path(sel_type, pick)
                _gh_download_bytes.clear()
                st.success(f"已切換 {sel_type} 類型為：{pick}")
        else:
            st.info(f"{sel_type} 目前沒有 .xlsx。")
