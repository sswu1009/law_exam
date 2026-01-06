"""
題庫載入服務
負責 Excel 讀取、正規化、多工作表支援
"""
import pandas as pd
import streamlit as st
from io import BytesIO
from typing import Optional

from exam_system.services.github_repo import github_service


def normalize_bank_df(
    df: pd.DataFrame,
    sheet_name: Optional[str] = None,
    source_file: Optional[str] = None
) -> pd.DataFrame:
    """
    正規化題庫 DataFrame
    - 統一欄位名稱
    - 處理選項（支援 OptionA-E、A-E、Ａ-Ｅ、選項一-五）
    - 自動偵測答案（支援 * 標記）
    - 過濾無效題目
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    
    # 欄位名稱對應
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
    
    # 處理選項欄位（支援多種格式）
    option_cols = []
    for c in df.columns:
        lc = str(c).strip()
        if lc.lower().startswith("option"):
            option_cols.append(c)
        elif lc in list("ABCDE"):
            idx = ord(lc) - ord("A")
            std = f"Option{chr(ord('A') + idx)}"
            df = df.rename(columns={c: std})
            option_cols.append(std)
        elif lc in ["Ａ", "Ｂ", "Ｃ", "Ｄ", "Ｅ"]:
            idx = ["Ａ", "Ｂ", "Ｃ", "Ｄ", "Ｅ"].index(lc)
            std = f"Option{chr(ord('A') + idx)}"
            df = df.rename(columns={c: std})
            option_cols.append(std)
    
    option_cols = sorted({c for c in df.columns if str(c).lower().startswith("option")})
    
    # 檢查必要欄位
    if len(option_cols) < 2:
        return pd.DataFrame()
    
    for col in ["ID", "Question"]:
        if col not in df.columns:
            return pd.DataFrame()
    
    # 補充可選欄位
    for col in ["Explanation", "Tag", "Image"]:
        if col not in df.columns:
            df[col] = ""
    
    # 填充選項空值
    for oc in option_cols:
        df[oc] = df[oc].fillna("").astype(str)
    
    # 自動偵測答案（從 * 標記）
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
    
    # 預設題型
    if "Type" not in df.columns:
        df["Type"] = "SC"
    
    # 正規化答案與題型
    df["Type"] = df["Type"].astype(str).str.upper().str.strip()
    df["Answer"] = df["Answer"].astype(str).str.upper().str.replace(" ", "", regex=False)
    
    # 過濾至少有兩個選項的題目
    def has_two_options(row):
        cnt = sum(1 for oc in option_cols if str(row.get(oc, "")).strip())
        return cnt >= 2
    
    df = df[df.apply(has_two_options, axis=1)].reset_index(drop=True)
    
    # 補充標籤（使用工作表名稱）
    if "Tag" not in df.columns:
        df["Tag"] = ""
    if sheet_name:
        df["Tag"] = df["Tag"].astype(str)
        df.loc[df["Tag"].str.strip().eq(""), "Tag"] = sheet_name
    
    # 記錄來源
    df["SourceFile"] = (source_file or "").strip()
    df["SourceSheet"] = (sheet_name or "").strip()
    
    return df


def load_bank_from_excel(file_like) -> Optional[pd.DataFrame]:
    """
    從 Excel 檔案載入題庫（支援多工作表）
    file_like: BytesIO 或檔案物件
    """
    try:
        xls = pd.ExcelFile(file_like)
        dfs = []
        
        try:
            source_file = getattr(file_like, "name", None) or ""
        except Exception:
            source_file = ""
        
        # 讀取所有工作表
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
        # 降級：嘗試單一工作表
        try:
            df = pd.read_excel(file_like)
            norm = normalize_bank_df(
                df,
                sheet_name=None,
                source_file=getattr(file_like, "name", None) or ""
            )
            if not norm.empty:
                return norm
            st.error("題庫載入失敗或為空。")
            return None
        except Exception:
            st.exception(e)
            return None


def load_banks_from_github(paths: list[str]) -> Optional[pd.DataFrame]:
    """從 GitHub 載入多個題庫檔並合併"""
    dfs = []
    
    for p in paths:
        try:
            data = github_service.download_file_bytes(p)
            bio = BytesIO(data)
            try:
                bio.name = p
            except Exception:
                pass
            
            df = load_bank_from_excel(bio)
            if df is not None and not df.empty:
                dfs.append(df)
        except Exception:
            continue
    
    if not dfs:
        return None
    
    return pd.concat(dfs, ignore_index=True)


def load_bank_from_github(bank_path_or_paths) -> pd.DataFrame:
    """
    從 GitHub 載入題庫
    bank_path_or_paths: 單一路徑或路徑列表
    """
    if isinstance(bank_path_or_paths, list):
        df = load_banks_from_github(bank_path_or_paths)
        if df is None:
            st.error("題庫載入失敗或為空，請聯絡管理者。")
            st.stop()
        st.caption(f"✅ 使用題庫（GitHub 多檔合併）：{len(bank_path_or_paths)} 檔")
        return df
    else:
        bank_path = bank_path_or_paths
        try:
            data = github_service.download_file_bytes(bank_path)
            bio = BytesIO(data)
            try:
                bio.name = bank_path
            except Exception:
                pass
            
            df = load_bank_from_excel(bio)
            if df is None:
                st.error(f"題庫載入失敗：{bank_path}")
                st.stop()
            
            st.caption(f"✅ 使用題庫（GitHub）：{bank_path}")
            return df
        except Exception as e:
            st.error(f"無法載入題庫：{bank_path}\n錯誤：{e}")
            st.stop()
