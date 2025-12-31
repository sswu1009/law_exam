from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
BANK_DIR = BASE_DIR / "bank"


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # 轉成字串，避免 NaN 顯示問題
    for col in df.columns:
        df[col] = df[col].astype(str)
    if "章節" not in df.columns:
        df["章節"] = ""
    return df


def _read_excel_file(path: Path) -> pd.DataFrame:
    # xlsw 用 openpyxl 讀取即可（可讀、但不執行巨集）
    df = pd.read_excel(path, engine="openpyxl")
    return _normalize_df(df)


@lru_cache(maxsize=1)
def load_all_banks() -> Dict[str, pd.DataFrame]:
    """
    回傳:
    {
      "人身": df,
      "外幣": df,
      ...
      "_root": df (bank 根目錄若有題庫)
    }
    """
    result: Dict[str, pd.DataFrame] = {}

    if not BANK_DIR.exists():
        return result

    # 1) 子資料夾分類
    for item in BANK_DIR.iterdir():
        if item.is_dir():
            frames = []
            for f in item.glob("*.xlsw"):
                frames.append(_read_excel_file(f))
            if frames:
                result[item.name] = pd.concat(frames, ignore_index=True)

    # 2) bank 根目錄題庫
    root_frames = []
    for f in BANK_DIR.glob("*.xlsw"):
        root_frames.append(_read_excel_file(f))
    if root_frames:
        result["_root"] = pd.concat(root_frames, ignore_index=True)

    return result


def list_categories() -> List[str]:
    banks = load_all_banks()
    return [k for k in banks.keys() if k != "_root"]


def get_bank(category: str) -> Optional[pd.DataFrame]:
    return load_all_banks().get(category)


def list_chapters(category: str) -> List[str]:
    df = get_bank(category)
    if df is None or "章節" not in df.columns:
        return []
    chapters = df["章節"].fillna("").astype(str).tolist()
    chapters = [c.strip() for c in chapters if c.strip() and c.strip().lower() != "nan"]
    return sorted(list(set(chapters)))


def pick_questions(
    category: str,
    chapter: Optional[str] = None,
    limit: Optional[int] = None,
    shuffle: bool = True,
) -> pd.DataFrame:
    df = get_bank(category)
    if df is None:
        return pd.DataFrame()

    if chapter:
        df = df[df["章節"].astype(str) == str(chapter)]

    if shuffle and not df.empty:
        df = df.sample(frac=1).reset_index(drop=True)

    if limit is not None:
        df = df.head(limit)

    return df.reset_index(drop=True)
