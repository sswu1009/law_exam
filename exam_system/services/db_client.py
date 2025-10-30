# services/db_client.py
import os
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Any, Optional

import pandas as pd

# === 動態載入 bank/ 下的所有 xlsx 題庫 ===

BASE_DIR = Path(__file__).resolve().parent.parent  # exam_system/
BANK_DIR = BASE_DIR / "bank"

# 可視需要調整：哪些欄位是你題庫一定會有的
DEFAULT_COLUMNS = ["題目", "選項A", "選項B", "選項C", "選項D", "答案", "章節"]


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """統一欄位名稱，缺的補空欄位，不多做邏輯，維持原本題庫結構。"""
    # 轉成字串欄位避免後面 st 顯示出現 float
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].astype(str)

    # 若沒有章節欄位也不要報錯，補空白，後面頁面可用 .get() 取
    if "章節" not in df.columns:
        df["章節"] = ""

    return df


def _read_excel_file(path: Path) -> pd.DataFrame:
    # 只處理 xlsx
    df = pd.read_excel(path)
    df = _normalize_df(df)
    return df


@lru_cache(maxsize=1)
def load_all_banks() -> Dict[str, pd.DataFrame]:
    """
    掃描 bank/ 下所有子資料夾與 .xlsx
    回傳格式：
    {
        "人身": DataFrame,
        "外幣": DataFrame,
        ...
    }
    """
    result: Dict[str, pd.DataFrame] = {}

    if not BANK_DIR.exists():
        return result

    # 1. 先掃子資料夾
    for item in BANK_DIR.iterdir():
        if item.is_dir():
            category_name = item.name  # 例如 人身/外幣/投資型/產險
            frames = []
            for f in item.glob("*.xlsx"):
                frames.append(_read_excel_file(f))
            if frames:
                result[category_name] = pd.concat(frames, ignore_index=True)

    # 2. bank 根目錄底下如果也有 .xlsx，就放一個特別名稱
    root_frames = []
    for f in BANK_DIR.glob("*.xlsx"):
        root_frames.append(_read_excel_file(f))
    if root_frames:
        result["_root"] = pd.concat(root_frames, ignore_index=True)

    return result


def list_categories() -> List[str]:
    """
    回傳目前可用的題庫分類名稱，供 UI 下拉使用
    """
    banks = load_all_banks()
    # 不一定要把 _root 顯示出來，看你要不要
    return [k for k in banks.keys() if k != "_root"]


def get_bank(category: str) -> Optional[pd.DataFrame]:
    """
    取得指定類別的題庫 DataFrame
    """
    banks = load_all_banks()
    return banks.get(category)


def list_chapters(category: str) -> List[str]:
    """
    列出該類別所有章節名稱（去重、去空白）
    """
    df = get_bank(category)
    if df is None or "章節" not in df.columns:
        return []
    chapters = df["章節"].fillna("").astype(str).tolist()
    # 去掉空字串
    chapters = [c.strip() for c in chapters if c.strip()]
    return sorted(list(set(chapters)))


def pick_questions(
    category: str,
    chapter: Optional[str] = None,
    limit: Optional[int] = None,
    shuffle: bool = True,
) -> pd.DataFrame:
    """
    依類別與章節取題
    - category: 類別，如「人身」
    - chapter: 若指定章節則過濾
    - limit: 取幾題
    """
    df = get_bank(category)
    if df is None:
        return pd.DataFrame()

    if chapter:
        df = df[df["章節"].astype(str) == str(chapter)]

    if shuffle:
        df = df.sample(frac=1).reset_index(drop=True)

    if limit is not None:
        df = df.head(limit)

    return df.reset_index(drop=True)
