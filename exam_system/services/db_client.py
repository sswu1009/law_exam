import os
import re
import pandas as pd
from pathlib import Path
from config import settings

# 欄位正規化對照表
COLUMN_MAPPING = {
    "題目": "Question", "題幹": "Question", "Question": "Question",
    "答案": "Answer", "Answer": "Answer",
    "解析": "Explanation", "詳解": "Explanation", "Explanation": "Explanation",
    "章節": "Chapter", "Chapter": "Chapter",
    "Tag": "Chapter", "標籤": "Chapter"
}

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    核心邏輯：將各種亂七八糟的 Excel 欄位統一為標準格式
    標準格式: ID, Question, OptionA, OptionB, OptionC, OptionD, Answer, Explanation, Chapter
    """
    df = df.copy()
    
    # 1. 移除欄位前後空白
    df.columns = [str(c).strip() for c in df.columns]
    
    # 2. 重新命名基本欄位
    df = df.rename(columns={k: v for k, v in COLUMN_MAPPING.items() if k in df.columns})
    
    # 3. 動態識別選項欄位 (A, OptionA, 選項A...)
    # 透過 Regex 抓出 A, B, C, D, E
    for col in df.columns:
        # 情況 A: 純字母 "A", "B"...
        if col.upper() in ["A", "B", "C", "D", "E"]:
            df = df.rename(columns={col: f"Option{col.upper()}"})
            continue
            
        # 情況 B: "選項A", "Option A"...
        match = re.match(r"^(選項|Option)\s*([A-Ea-e])$", col, re.IGNORECASE)
        if match:
            letter = match.group(2).upper()
            df = df.rename(columns={col: f"Option{letter}"})

    # 4. 確保必要欄位存在
    required = ["Question", "Answer"]
    if not all(col in df.columns for col in required):
        return pd.DataFrame() # 格式不符，回傳空表

    # 5. 補全缺失的選填欄位
    for col in ["Explanation", "Chapter", "OptionA", "OptionB", "OptionC", "OptionD"]:
        if col not in df.columns:
            df[col] = ""

    # 6. 資料清理
    df["Answer"] = df["Answer"].astype(str).str.upper().str.strip()
    # 處理答案可能包含全形字母的情況
    full_width = str.maketrans("ＡＢＣＤＥ", "ABCDE")
    df["Answer"] = df["Answer"].str.translate(full_width)
    
    # 確保選項是字串
    opt_cols = [c for c in df.columns if c.startswith("Option")]
    for c in opt_cols:
        df[c] = df[c].fillna("").astype(str)
        
    # 產生 ID
    df["ID"] = range(1, len(df) + 1)
    
    return df

def load_all_banks():
    """掃描 bank/ 資料夾下所有 xlsx/xlsw 檔案並合併"""
    bank_root = Path(settings.BANKS_DIR)
    if not bank_root.exists():
        return {}

    data_map = {} # { "分類名稱": DataFrame }

    # 遞迴搜尋
    for file_path in bank_root.rglob("*"):
        if file_path.suffix.lower() in [".xlsx", ".xlsw"] and not file_path.name.startswith("~$"):
            try:
                # 判斷分類 (取父資料夾名稱，若在根目錄則設為 "綜合")
                category = file_path.parent.name if file_path.parent != bank_root else "綜合"
                
                raw_df = pd.read_excel(file_path, dtype=str)
                norm_df = normalize_df(raw_df)
                
                if not norm_df.empty:
                    if category not in data_map:
                        data_map[category] = []
                    data_map[category].append(norm_df)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue

    # 合併每個分類的 DataFrame
    final_banks = {}
    for cat, df_list in data_map.items():
        if df_list:
            final_banks[cat] = pd.concat(df_list, ignore_index=True)
            
    return final_banks

def get_chapters(df: pd.DataFrame):
    if df.empty or "Chapter" not in df.columns:
        return []
    chapters = df["Chapter"].dropna().unique().tolist()
    return sorted([str(c) for c in chapters if str(c).strip()])
