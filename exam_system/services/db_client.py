import pandas as pd
import re
from pathlib import Path
from functools import lru_cache
from config.settings import BANK_DIR

# 欄位對照表 (正規化用)
COLUMN_MAP = {
    "題目": "Question", "題幹": "Question", "Question": "Question",
    "答案": "Answer", "Answer": "Answer", "ANSWER": "Answer",
    "解析": "Explanation", "詳解": "Explanation", "Explanation": "Explanation",
    "章節": "Chapter", "Chapter": "Chapter", "Tag": "Chapter"
}

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    核心清洗邏輯：
    1. 統一欄位名稱 (Question, Answer, Explanation, Chapter)
    2. 動態識別選項 (OptionA, OptionB...)
    """
    df = df.copy()
    
    # 1. 清除欄位空白
    df.columns = [str(c).strip() for c in df.columns]
    
    # 2. 重新命名基礎欄位
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    
    # 3. 動態識別選項 (A, B, C, D, OptionA, 選項A...)
    for col in df.columns:
        # 情況 1: 純字母 "A", "B", "C", "D"
        if col.upper() in ["A", "B", "C", "D", "E"]:
            df = df.rename(columns={col: f"Option{col.upper()}"})
            continue
        
        # 情況 2: Regex 抓取 "選項A", "Option A"
        match = re.match(r"^(選項|Option)\s*([A-Ea-e])$", col, re.IGNORECASE)
        if match:
            letter = match.group(2).upper()
            df = df.rename(columns={col: f"Option{letter}"})

    # 4. 確保必要欄位存在
    if "Question" not in df.columns:
        return pd.DataFrame() # 無效的 sheet

    # 5. 補全缺失欄位
    for col in ["Answer", "Explanation", "Chapter", "OptionA", "OptionB", "OptionC", "OptionD"]:
        if col not in df.columns:
            df[col] = ""

    # 6. 資料轉型與清理
    df["Answer"] = df["Answer"].astype(str).str.upper().str.strip()
    # 處理全形轉半形 (Ａ -> A)
    trans_table = str.maketrans("ＡＢＣＤＥ", "ABCDE")
    df["Answer"] = df["Answer"].str.translate(trans_table)
    
    # 確保選項內容為字串且處理 NaN
    opt_cols = [c for c in df.columns if c.startswith("Option")]
    for c in opt_cols:
        df[c] = df[c].fillna("").astype(str)

    # 產生唯一 ID (方便 UI key 使用)
    df["ID"] = range(1, len(df) + 1)
    
    return df

@lru_cache(maxsize=1)
def load_all_banks() -> dict:
    """
    掃描 bank/ 下所有 xlsx 檔案
    回傳: { "人身": DataFrame, "外幣": DataFrame, ... }
    """
    banks = {}
    if not BANK_DIR.exists():
        return banks

    # 遞迴搜尋所有 Excel
    for file_path in BANK_DIR.rglob("*"):
        if file_path.suffix.lower() in [".xlsx", ".xlsw"] and not file_path.name.startswith("~$"):
            try:
                # 判斷分類：如果檔案在子資料夾，用資料夾名；如果在根目錄，用檔名
                if file_path.parent != BANK_DIR:
                    category = file_path.parent.name
                else:
                    category = file_path.stem

                # 讀取 Excel (皆轉為字串避免 float 問題)
                raw_df = pd.read_excel(file_path, dtype=str)
                norm_df = _normalize_df(raw_df)
                
                if not norm_df.empty:
                    if category in banks:
                        banks[category] = pd.concat([banks[category], norm_df], ignore_index=True)
                    else:
                        banks[category] = norm_df
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                continue
    
    # 重新產生連續 ID (合併後 ID 會重複，故重算)
    for cat in banks:
        banks[cat]["ID"] = range(1, len(banks[cat]) + 1)
        
    return banks

def get_questions_by_domain(domain: str) -> pd.DataFrame:
    all_data = load_all_banks()
    return all_data.get(domain, pd.DataFrame())

def list_chapters(df: pd.DataFrame) -> list:
    if df.empty or "Chapter" not in df.columns:
        return []
    chapters = df["Chapter"].unique().tolist()
    return sorted([str(c) for c in chapters if str(c).strip()])
