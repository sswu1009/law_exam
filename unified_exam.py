# -*- coding: utf-8 -*-
"""
整合版題庫自動處理流程：
1️⃣ 混合模式章節對應（關鍵字 + LLaMA 判斷）
2️⃣ 自動依章節拆分題庫（每章節一個工作表，只保留題目、選項、答案）
"""

import pandas as pd
import requests, json
from docx import Document
from collections import OrderedDict, defaultdict
from tqdm import tqdm
import difflib
import os

# ==============================
# 檔案設定
# ==============================
DOCX_PATH = "/Users/lch/Downloads/JY電子檔筆記-人身保險-(解密 - 複製.docx"
EXCEL_PATH = "/Users/lch/lawbroker/題庫/外幣/題庫_FCI_分章_202411.xlsx"
OUTPUT_PATH_MIXED = "FCI_章節對應結果.xlsx"
OUTPUT_PATH_SPLIT = "FCI_題庫_依章節分頁.xlsx"

QUESTION_COL = "題目"
OPTION_COLS = ["選項一","選項二","選項三","選項四"]
ANSWER_COL = "答案"
OUTPUT_COL = "章節對應(混合)"
RAW_COL = "LLM原始輸出"
TAG_COL = OUTPUT_COL

KEEP_COLS = [QUESTION_COL, "選項一", "選項二", "選項三", "選項四", ANSWER_COL]

# ==============================
# 關鍵字表
# ==============================
CHAPTER_KEYWORDS = OrderedDict({
    "保險契約": ["契約","撤銷","寬限期","催告","停效","復效","保單價值"],
    "保險契約六大原則": ["最大善意","可保利益","損害填補","分攤","代位","告知義務"],
    "保險金與解約金": ["解約金","退保","死亡給付","滿期金","生存給付","自殺","故意"],
    "遺產稅與贈與稅": ["遺產稅","贈與稅","免稅額","扣除額","課稅","分期","申報"],
    "健康保險": ["健康保險","醫療險","實支實付","日額給付","住院","手術","重大疾病","癌症險"],
    "人壽保險": ["終身壽險","定期壽險","生死合險","變額壽險","投資型"],
    "年金保險": ["年金","即期年金","遞延年金","生存年金","退休規劃"],
    "傷害保險": ["傷害保險","意外","外來","突發","非疾病","殘廢","意外醫療"],
})
ALLOWED_CHAPTERS = list(CHAPTER_KEYWORDS.keys())

# ==============================
# 萃取章節內容
# ==============================
def extract_chapters(docx_path):
    doc = Document(docx_path)
    chapters = {}
    current = None
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if t.startswith("第") and "章" in t:
            current = t
            chapters[current] = []
        elif current:
            chapters[current].append(t)
    return {ch: " ".join(txts)[:600] for ch, txts in chapters.items()}

# ==============================
# LLaMA API
# ==============================
def ask_llama(prompt, model="llama3"):
    try:
        url = "http://localhost:11434/api/generate"
        payload = {"model": model, "prompt": prompt}
        resp = requests.post(url, json=payload, stream=True)
        output = ""
        for line in resp.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                output += data.get("response", "")
        return output.strip()
    except Exception as e:
        print(f"⚠️ LLaMA 呼叫失敗：{e}")
        return ""

def classify_with_llama(question_text, chapters):
    chapters_text = "、".join(ALLOWED_CHAPTERS)
    prompt = f"""
你是一個保險考照專家。請根據題目與教材章節內容，判斷題目涉及哪些章節。

【規則】：
1. 只能從以下章節名稱中選，原封不動輸出：
{chapters_text}
2. 可以選多個章節，用逗號分隔。
3. 不要輸出額外解釋。

題目：
{question_text}

請直接輸出章節名稱。
"""
    raw_result = ask_llama(prompt)
    result_clean = []

    for part in raw_result.replace("、", ",").split(","):
        part = part.strip()
        if not part:
            continue
        best_match = difflib.get_close_matches(part, ALLOWED_CHAPTERS, n=1, cutoff=0.5)
        if best_match:
            result_clean.append(best_match[0])

    result_clean = list(OrderedDict.fromkeys(result_clean))
    return "、".join(result_clean), raw_result

# ==============================
# 關鍵字比對
# ==============================
def keyword_match(text):
    hits = []
    for chapter, kws in CHAPTER_KEYWORDS.items():
        if any(kw in text for kw in kws):
            hits.append(chapter)
    return "、".join(OrderedDict.fromkeys(hits))

# ==============================
# (1) 混合模式主流程
# ==============================
def process_excel(input_path, output_path, chapters):
    excel = pd.ExcelFile(input_path)
    writer = pd.ExcelWriter(output_path, engine="xlsxwriter")

    for sheet in excel.sheet_names:
        df = pd.read_excel(input_path, sheet_name=sheet)
        if QUESTION_COL not in df.columns:
            df.to_excel(writer, sheet_name=sheet, index=False)
            continue

        mapped, raw_outputs = [], []
        for _, row in tqdm(df.iterrows(), total=len(df), desc=f"處理 {sheet}"):
            q = str(row.get(QUESTION_COL, ""))
            opts = [str(row.get(c, "")) for c in OPTION_COLS if c in df.columns]
            text = q + " " + " ".join(opts)

            result = keyword_match(text)
            raw_answer = ""

            if not result:
                result, raw_answer = classify_with_llama(text, chapters)

            mapped.append(result)
            raw_outputs.append(raw_answer)

        df[OUTPUT_COL] = mapped
        df[RAW_COL] = raw_outputs
        df.to_excel(writer, sheet_name=sheet, index=False)

    writer.close()
    print(f"✅ 章節對應完成：{output_path}")

# ==============================
# (2) 依章節拆分精簡題庫
# ==============================
def split_excel_by_chapter(input_path, output_path, tag_col=TAG_COL):
    excel = pd.ExcelFile(input_path)
    chapter_dfs = defaultdict(list)

    for sheet in excel.sheet_names:
        df = pd.read_excel(input_path, sheet_name=sheet)
        keep_cols_exist = [c for c in KEEP_COLS if c in df.columns]
        if not keep_cols_exist or tag_col not in df.columns:
            continue

        for _, row in tqdm(df.iterrows(), total=len(df), desc=f"讀取 {sheet}"):
            tags = str(row.get(tag_col, "")).strip()
            if not tags or tags == "nan":
                continue

            chapters = [t.strip() for t in tags.replace(",", "、").split("、") if t.strip()]
            clean_row = row[keep_cols_exist]

            for ch in chapters:
                chapter_dfs[ch].append(clean_row)

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        for ch in sorted(chapter_dfs.keys()):
            out_df = pd.DataFrame(chapter_dfs[ch])
            safe_name = ch.replace("/", "_").replace("\\", "_").replace("*", "_")[:28]
            out_df.to_excel(writer, sheet_name=safe_name, index=False)

    print(f"✅ 已依章節分頁輸出精簡題庫：{output_path}")
    print(f"總章節數：{len(chapter_dfs)}")

# ==============================
# 主執行流程
# ==============================
if __name__ == "__main__":
    print("🚀 開始處理題庫章節對應...")
    chapters = extract_chapters(DOCX_PATH)
    process_excel(EXCEL_PATH, OUTPUT_PATH_MIXED, chapters)

    print("\n📘 開始依章節拆分題庫...")
    split_excel_by_chapter(OUTPUT_PATH_MIXED, OUTPUT_PATH_SPLIT)

    print("\n🎉 全部完成！")
