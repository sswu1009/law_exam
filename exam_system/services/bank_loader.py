# exam_system/services/bank_loader.py
import pandas as pd
from io import BytesIO
import streamlit as st
from exam_system.services import github_repo

def normalize_bank_df(df: pd.DataFrame, sheet_name: str | None = None, source_file: str | None = None) -> pd.DataFrame:
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
        "答案": "Answer", "題型": "Type",
    }
    df = df.rename(columns={c: col_map.get(c, c) for c in df.columns})

    # 標準化選項欄位 OptionA, OptionB...
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

    if len(option_cols) < 2 or "Question" not in df.columns:
        return pd.DataFrame() # 無法識別的格式

    # 補齊必要欄位
    for col in ["Explanation", "Tag", "Image"]:
        if col not in df.columns: df[col] = ""

    # 處理答案
    for oc in option_cols:
        df[oc] = df[oc].fillna("").astype(str)

    if "Answer" not in df.columns or df["Answer"].astype(str).str.strip().eq("").all():
        # 嘗試從 * 解析答案
        answers, types = [], []
        for ridx, r in df.iterrows():
            stars = []
            for i, oc in enumerate(option_cols):
                text = str(r[oc]).strip()
                if text.startswith("*"):
                    stars.append(chr(ord("A") + i))
                    df.at[ridx, oc] = text.lstrip("* ").strip()
            if len(stars) == 1:
                answers.append("".join(stars))
                types.append("SC")
            else:
                answers.append("".join(stars))
                types.append("MC")
        df["Answer"] = answers
        if "Type" not in df.columns: df["Type"] = types

    if "Type" not in df.columns: df["Type"] = "SC"

    df["Type"] = df["Type"].astype(str).str.upper().str.strip()
    df["Answer"] = df["Answer"].astype(str).str.upper().str.replace(" ", "", regex=False)
    
    # 移除空選項行
    def has_two_options(row):
        cnt = sum(1 for oc in option_cols if str(row.get(oc, "")).strip())
        return cnt >= 2
    df = df[df.apply(has_two_options, axis=1)].reset_index(drop=True)

    if sheet_name:
        df["Tag"] = df["Tag"].astype(str)
        df.loc[df["Tag"].str.strip().eq(""), "Tag"] = sheet_name

    df["SourceFile"] = (source_file or "").strip()
    df["SourceSheet"] = (sheet_name or "").strip()
    return df

def _load_excel_bytes(data: bytes, filename: str):
    bio = BytesIO(data)
    bio.name = filename
    try:
        xls = pd.ExcelFile(bio)
        dfs = []
        for sh in xls.sheet_names:
            raw = pd.read_excel(xls, sheet_name=sh)
            norm = normalize_bank_df(raw, sheet_name=sh, source_file=filename)
            if not norm.empty:
                dfs.append(norm)
        if dfs:
            return pd.concat(dfs, ignore_index=True)
    except Exception:
        # Fallback single sheet
        bio.seek(0)
        try:
            df = pd.read_excel(bio)
            norm = normalize_bank_df(df, sheet_name=None, source_file=filename)
            return norm
        except Exception:
            pass
    return None

def load_banks(paths: list[str]) -> pd.DataFrame:
    dfs = []
    with st.spinner(f"正在載入 {len(paths)} 個題庫檔..."):
        for p in paths:
            data = github_repo.download_bytes(p)
            if data is None:
                st.warning(f"無法下載題庫：{p}")
                continue
            df = _load_excel_bytes(data, p)
            if df is not None and not df.empty:
                dfs.append(df)
    
    if not dfs:
        st.error("所有題庫載入失敗或內容為空。")
        st.stop()
        
    return pd.concat(dfs, ignore_index=True)
