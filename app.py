import os
import streamlit as st
import pandas as pd
import time
from io import BytesIO

st.set_page_config(page_title="模擬考試機器人", layout="wide")
st.title("📘 模擬考試機器人（Excel 題庫）")

with st.expander("錠嵂保險經紀人證照模擬練習", expanded=False):
    st.markdown(
        """
       使用說明
    
       
1. 請點選左上角的箭頭開始設定 
2. 本系統使用固定題庫自動出題（單選/複選自動判斷）。
3. 左側設定完題數與選項後，點 **開始考試** 進入作答。
4. 交卷後會顯示分數與詳細解答，並可下載作答明細（CSV）。

    
        """
    )

# ---- 題庫來源設定 ----
# 預設：使用專案內固定檔案（不讓一般使用者上傳）
# 題庫檔名來源：環境變數 BANK_FILE，預設 exam_bank.xlsx
FIXED_BANK_PATH = os.environ.get("BANK_FILE", "PA_分章_20250731_LIB.xlsx")

# 管理模式切換（?admin=1 或 st.secrets["ADMIN"]=="1"）
qparams = st.query_params
IS_ADMIN = qparams.get("admin", ["0"])[:1][0] == "1" or str(st.secrets.get("ADMIN", "0")) == "1"

uploaded = None
if IS_ADMIN:
    uploaded = st.file_uploader("（管理者）上傳/覆寫 Excel 題庫（.xlsx）", type=["xlsx"])

if "df" not in st.session_state:
    st.session_state.df = None
if "paper" not in st.session_state:
    st.session_state.paper = None
if "start_ts" not in st.session_state:
    st.session_state.start_ts = None
if "time_limit" not in st.session_state:
    st.session_state.time_limit = 0

# 讀取題庫
def load_bank(file):
    try:
        df = pd.read_excel(file)
        # ---- 中文欄位自動對應 ----
        col_map = {
            "編號": "ID",
            "題目": "Question",
            "選項一": "OptionA",
            "選項二": "OptionB",
            "選項三": "OptionC",
            "選項四": "OptionD",
            "解釋說明": "Explanation",
            "修訂備註": "Notes",
            "標籤": "Tag",
            "科目": "Tag",
            "圖片": "Image",
        }
        # 標準化欄名（去空白）
        df.columns = [str(c).strip() for c in df.columns]
        # 中文 -> 英文名稱
        rename_dict = {c: col_map.get(c, c) for c in df.columns}
        df = df.rename(columns=rename_dict)

        # ---- 自動偵測選項欄位 ----
        option_cols = [c for c in df.columns if str(c).lower().startswith("option")]
        if len(option_cols) < 2:
            st.error("題庫至少需要 OptionA 與 OptionB（或中文：選項一、選項二）！")
            return None

        # 必要欄位：ID / Question
        for col in ["ID", "Question"]:
            if col not in df.columns:
                st.error(f"缺少必要欄位：{col}")
                return None

        # 若沒有 Explanation/Tag/Image，補空欄
        for col in ["Explanation", "Tag", "Image"]:
            if col not in df.columns:
                df[col] = ""

        # 填補選項 NaN
        for opt in option_cols:
            df[opt] = df[opt].fillna("").astype(str)

        # ---- 自動推斷 Answer 與 Type（支援 * 標記） ----
        if "Answer" not in df.columns:
            answers = []
            types = []
            for _, r in df.iterrows():
                stars = []  # 收集被 * 標記的選項代號
                for idx, col in enumerate(option_cols):
                    text = str(r[col]).strip()
                    if text.startswith("*"):
                        stars.append(chr(ord('A') + idx))
                        # 直接把 * 去掉
                        df.at[_, col] = text.lstrip("* ")
                if len(stars) == 0:
                    answers.append("")  # 沒標星，留空由使用者後續補
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

        # 若仍無 Type，預設為單選 SC（因應使用者需求）
        if "Type" not in df.columns:
            df["Type"] = "SC"

        # 正規化
        df["Type"] = df["Type"].astype(str).str.upper().str.strip()
        df["Answer"] = df["Answer"].astype(str).str.upper().str.replace(" ", "", regex=False)
        return df
    except Exception as e:
        st.exception(e)
        return None
        for col in ["ID", "Question", "Type", "Answer"]:
            if col not in df.columns:
                st.error(f"缺少必要欄位：{col}")
                return None
        # 填補可選欄位
        for opt in option_cols:
            df[opt] = df[opt].fillna("")
        if "Explanation" not in df.columns:
            df["Explanation"] = ""
        if "Tag" not in df.columns:
            df["Tag"] = ""
        if "Image" not in df.columns:
            df["Image"] = ""
        # 正規化
        df["Type"] = df["Type"].astype(str).str.upper().str.strip()
        df["Answer"] = df["Answer"].astype(str).str.upper().str.replace(" ", "", regex=False)
        return df
    except Exception as e:
        st.exception(e)
        return None

# 載入順序：1) 管理者上傳；2) 固定檔案；3) 提示錯誤
if uploaded is not None:
    st.session_state.df = load_bank(uploaded)
else:
    try:
        with open(FIXED_BANK_PATH, "rb") as f:
            st.session_state.df = load_bank(f)
            st.caption(f"使用固定題庫：{FIXED_BANK_PATH}")
    except Exception:
        st.session_state.df = None

if st.session_state.df is None:
    if IS_ADMIN:
        st.error("找不到題庫。請上傳一份 Excel 作為固定題庫，或把檔案放在專案根目錄並命名為 exam_bank.xlsx。")
    else:
        st.error("目前尚未配置題庫，請聯絡管理者。")
    st.stop()

bank = st.session_state.df
option_cols = [c for c in bank.columns if str(c).lower().startswith("option") and bank[c].astype(str).str.strip().ne("").any()]

# 設定區
with st.sidebar:
    st.header("⚙️ 考試設定")
    # 標籤篩選
    all_tags = sorted({t.strip() for tags in bank["Tag"].dropna().astype(str) for t in tags.split(";") if t.strip()})
    picked_tags = st.multiselect("選擇標籤（可多選，不選=全選）", options=all_tags)

    # 題數
    # 依標籤篩選可用題庫
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

# 產生試卷
import random

def sample_paper(df, n, by_tags):
    if by_tags:
        df = df.copy()
    n = min(n, len(df))
    rows = df.sample(n=n, replace=False, random_state=random.randint(0, 1_000_000)) if n > 0 else df.head(0)
    if random_order:
        rows = rows.sample(frac=1, random_state=random.randint(0, 1_000_000))
    # 重新整理每題可用選項
    questions = []
    for _, r in rows.iterrows():
        opts = []
        letters = []
        for idx, col in enumerate(option_cols):
            val = str(r[col]).strip()
            if val:
                opts.append(val)
                letters.append(chr(ord('A') + idx))
        # 產生 (label, text)
        choices = list(zip(letters, opts))
        if shuffle_options:
            random.shuffle(choices)
        questions.append({
            "ID": r["ID"],
            "Question": r["Question"],
            "Type": r["Type"],
            "Choices": choices,  # list of (letter, text)
            "Answer": set(str(r["Answer"]).upper()),
            "Explanation": r.get("Explanation", ""),
            "Image": r.get("Image", ""),
            "Tag": r.get("Tag", ""),
        })
    return questions

if start_btn or (st.session_state.paper and st.session_state.start_ts is not None):
    if start_btn:
        st.session_state.paper = sample_paper(filtered, int(num_q), bool(picked_tags))
        st.session_state.start_ts = time.time()
        st.rerun()

    paper = st.session_state.paper or []
    if not paper:
        st.warning("題庫不足，請調整題數或篩選條件。")
        st.stop()

    # 倒數顯示
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
                st.image(q["Image"], use_column_width=True)
            except Exception:
                st.info("圖片載入失敗，請確認路徑或網址。")

        labels = [lab for lab, _ in q["Choices"]]
        display = [f"{lab}. {txt}" for lab, txt in q["Choices"]]

        if q["Type"] == "MC":
            picked = st.multiselect(
                f"（複選）選擇所有正確選項：",
                options=display,
                key=f"q_{idx}",
            )
            picked_labels = {opt.split(".", 1)[0] for opt in picked}
        else:
            choice = st.radio(
                "（單選）選擇一個答案：",
                options=display,
                key=f"q_{idx}",
            )
            picked_labels = {choice.split(".", 1)[0]} if choice else set()

        st.session_state[answers_key][q["ID"]] = picked_labels
        st.divider()

    submitted = st.button("📥 交卷並看成績", use_container_width=True)

    if submitted or (st.session_state.time_limit > 0 and time.time() - st.session_state.start_ts >= st.session_state.time_limit):
        # 評分
        records = []
        correct_count = 0
        for q in paper:
            gold = set(q["Answer"])  # e.g., {"A","C"}
            pred = st.session_state[answers_key].get(q["ID"], set())
            is_correct = (pred == gold)
            correct_count += int(is_correct)
            # 還原顯示選項與對應文字
            def render_set(ss):
                mapping = {lab: txt for lab, txt in q["Choices"]}
                ordered = sorted(list(ss))
                return ", ".join([f"{lab}. {mapping.get(lab, '')}" for lab in ordered]) if ss else "(未作答)"

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
        score_pct = round(100 * correct_count / len(paper), 2)

        st.success(f"你的分數：{correct_count} / {len(paper)}（{score_pct}%）")
        result_df = pd.DataFrame.from_records(records)
        st.dataframe(result_df, use_container_width=True)

        # 下載 CSV
        csv_bytes = result_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ 下載作答明細（CSV）",
            data=csv_bytes,
            file_name="exam_results.csv",
            mime="text/csv",
        )

        # 重新開始按鈕
        if st.button("🔁 再考一次", type="secondary"):
            st.session_state.paper = None
            st.session_state.start_ts = None
            st.session_state[answers_key] = {}
            st.rerun()
