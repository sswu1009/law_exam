from pathlib import Path
from functools import lru_cache
import pandas as pd
from typing import Dict

from config.settings import BANK_DIR


VALID_EXTS = (".xlsx", ".xls")


def _read_excel(path: Path) -> pd.DataFrame:
    return pd.read_excel(path)


@lru_cache(maxsize=1)
def load_all_banks() -> Dict[str, pd.DataFrame]:
    banks: Dict[str, pd.DataFrame] = {}

    if not BANK_DIR.exists():
        return banks

    for category_dir in BANK_DIR.iterdir():
        if not category_dir.is_dir():
            continue

        frames = []
        for file in category_dir.iterdir():
            if file.suffix.lower() in VALID_EXTS:
                try:
                    df = _read_excel(file)
                    df["__source_file"] = file.name
                    frames.append(df)
                except Exception as e:
                    print(f"[WARN] 無法讀取 {file}: {e}")

        if frames:
            banks[category_dir.name] = pd.concat(frames, ignore_index=True)

    return banks


def list_categories():
    return list(load_all_banks().keys())
