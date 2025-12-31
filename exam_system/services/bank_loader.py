from __future__ import annotations

from io import BytesIO
from typing import Optional

import pandas as pd
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
        elif lc in ["Ａ", "Ｂ", "Ｃ", "Ｄ", "Ｅ"]:
            idx = ["Ａ", "Ｂ", "Ｃ", "Ｄ", "Ｅ"].index(lc)
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

    # 若 Answer 欄空，支援 * 代表正解
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

    def has_two_options(row) -> bool:
        cnt = sum(1 for oc in option_cols if str(row.get(oc, "")).strip())
        return cnt >= 2

    df = df[df.apply(has_two_options, axis=1)].reset_index(drop=True)

    if sheet_name:
        df["Tag"] = df["Tag"].astype(str)
        df.loc[df["Tag"].str.strip().eq(""), "Tag"] = sheet_name

    df["SourceFile"] = (source_file or "").strip()
    df["SourceSheet"] = (sheet_name or "").strip()
    return df


def load_bank(file_like) -> Optional[pd.DataFrame]:
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
            return None
        return pd.concat(dfs, ignore_index=True)

    except Exception as e:
        # fallback: 單 sheet
        try:
            df = pd.read_excel(file_like)
            norm = normalize_bank_df(df, sheet_name=None, source_file=getattr(file_like, "name", None) or "")
            return norm if (norm is not None and not norm.empty) else None
        except Exception:
            st.exception(e)
            return None


def load_banks_from_github(paths: list[str]) -> Optional[pd.DataFrame]:
    dfs = []
    for p in paths:
        try:
            data = github_repo.download_bytes(p)
            bio = BytesIO(data)
            try:
                bio.name = p
            except Exception:
                pass
            df = load_bank(bio)
            if df is None or df.empty:
                continue
            dfs.append(df)
        except Exception:
            continue
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)


def load_bank_from_github(bank_path_or_paths) -> pd.DataFrame:
    if isinstance(bank_path_or_paths, list):
        df = load_banks_from_github(bank_path_or_paths)
        if df is None or df.empty:
            st.error("題庫載入失敗或為空（GitHub 多檔合併）。")
            st.stop()
        st.caption(f"使用固定題庫（GitHub 多檔合併）：{len(bank_path_or_paths)} 檔")
        return df

    bank_path = bank_path_or_paths
    data = github_repo.download_bytes(bank_path)
    bio = BytesIO(data)
    try:
        bio.name = bank_path
    except Exception:
        pass

    df = load_bank(bio)
    if df is None or df.empty:
        st.error(f"題庫載入失敗或為空：{bank_path}")
        st.stop()

    st.caption(f"使用固定題庫（GitHub）：{bank_path}")
    return df
