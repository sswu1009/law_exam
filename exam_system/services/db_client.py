from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config.settings import BANK_DIR, SUPPORTED_EXTS


@dataclass
class BankFile:
    category: str           # 例如：人身 / 外幣 / 投資型 / 產險
    path: Path              # 檔案完整路徑
    name: str               # 檔名（含副檔名）


def _list_category_dirs(bank_dir: Path) -> List[Path]:
    if not bank_dir.exists():
        return []
    return sorted([p for p in bank_dir.iterdir() if p.is_dir()])


def load_all_banks(bank_dir: Path = BANK_DIR) -> Dict[str, List[BankFile]]:
    """
    回傳：
    {
      "人身": [BankFile(...), ...],
      "外幣": [...],
      ...
    }
    """
    result: Dict[str, List[BankFile]] = {}
    for cat_dir in _list_category_dirs(bank_dir):
        files = []
        for f in sorted(cat_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
                files.append(BankFile(category=cat_dir.name, path=f, name=f.name))
        result[cat_dir.name] = files
    return result


def read_bank_excel(file_path: Path, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    先用最寬鬆策略讀，讀不到再回傳空 DF 並讓上層顯示錯誤訊息。
    """
    try:
        # pandas 會依副檔名嘗試選 engine
        # .xlsx/.xlsm 通常用 openpyxl
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        # 若 sheet_name=None，read_excel 會回 dict；這裡統一成 DF：取第一張
        if isinstance(df, dict):
            first_key = list(df.keys())[0]
            return df[first_key]
        return df
    except Exception as e:
        # 讓上層 UI 印出錯誤
        raise RuntimeError(f"讀取題庫失敗：{file_path.name}，原因：{e}") from e
