# exam_system/services/github_repo.py
import json
import base64
import requests
import streamlit as st
from exam_system.config import settings

def _gh_headers():
    h = {"Accept": "application/vnd.github+json"}
    if settings.GH_TOKEN:
        h["Authorization"] = f"Bearer {settings.GH_TOKEN}"
    return h

def _gh_api(path, method="GET", **kwargs):
    url = f"https://api.github.com/repos/{settings.GH_OWNER}/{settings.GH_REPO}/{path}"
    try:
        r = requests.request(method, url, headers=_gh_headers(), **kwargs)
        if r.status_code >= 400:
            snippet = r.text[:300].replace("\n", " ")
            raise RuntimeError(f"GitHub API {method} {path} -> {r.status_code}: {snippet}")
        return r.json()
    except Exception as e:
        st.error(f"GitHub 連線錯誤: {e}")
        st.stop()

def get_sha(path):
    try:
        j = _gh_api(f"contents/{path}", params={"ref": settings.GH_BRANCH})
        return j.get("sha")
    except Exception:
        return None

def put_file(path, content_bytes, message):
    b64 = base64.b64encode(content_bytes).decode("ascii")
    payload = {"message": message, "content": b64, "branch": settings.GH_BRANCH}
    sha = get_sha(path)
    if sha:
        payload["sha"] = sha
    return _gh_api(f"contents/{path}", method="PUT", json=payload)

@st.cache_data(ttl=300, show_spinner=False)
def download_bytes(path):
    """從 GitHub 下載檔案 Bytes，並快取 5 分鐘"""
    try:
        j = _gh_api(f"contents/{path}", params={"ref": settings.GH_BRANCH})
        if j.get("encoding") == "base64":
            return base64.b64decode(j["content"])
        # Fallback for large files if GH returns download_url
        raw_url = f"https://raw.githubusercontent.com/{settings.GH_OWNER}/{settings.GH_REPO}/{settings.GH_BRANCH}/{path}"
        return requests.get(raw_url, headers=_gh_headers()).content
    except Exception as e:
        # 若下載失敗回傳 None，讓呼叫端決定是否報錯
        return None

def list_files(folder_path):
    try:
        items = _gh_api(f"contents/{folder_path}", params={"ref": settings.GH_BRANCH})
        return [it["path"] for it in items if it["type"] == "file" and it["name"].lower().endswith(".xlsx")]
    except Exception:
        return []

def read_pointer():
    try:
        data = download_bytes(settings.POINTER_FILE)
        if data:
            return json.loads(data.decode("utf-8"))
        return {}
    except Exception:
        return {}

def write_pointer(obj: dict):
    if not settings.GH_TOKEN:
        st.warning("GH_TOKEN 未設定，無法寫入指標檔。")
        return
    put_file(
        settings.POINTER_FILE,
        json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"),
        "update bank pointers"
    )
    download_bytes.clear() # 清除快取

def get_current_bank_path(bank_type: str | None = None):
    conf = read_pointer()
    current = conf.get("current")
    if isinstance(current, dict):
        if bank_type:
            p = current.get(bank_type)
            if p: return p
    # Legacy support
    legacy = conf.get("path")
    if legacy and not bank_type:
        return legacy
    # Default fallback
    return st.secrets.get("BANK_FILE", f"{settings.BANKS_DIR}/exam_bank.xlsx")

def set_current_bank_path(bank_type: str, path: str):
    if not path.startswith(f"{settings.BANKS_DIR}/"):
        path = f"{settings.get_type_dir(bank_type)}/{path}"
    
    conf = read_pointer()
    if "current" not in conf or not isinstance(conf.get("current"), dict):
        conf["current"] = {}
    conf["current"][bank_type] = path
    try:
        write_pointer(conf)
    except Exception as e:
        st.warning(f"更新 {settings.POINTER_FILE} 失敗：{e}")

def check_write_permission():
    missing = []
    if not settings.GH_OWNER: missing.append("REPO_OWNER")
    if not settings.GH_REPO: missing.append("REPO_NAME")
    if not settings.GH_TOKEN: missing.append("GH_TOKEN")
    if missing:
        return False, "缺少 Secrets: " + ", ".join(missing)
    return True, ""
