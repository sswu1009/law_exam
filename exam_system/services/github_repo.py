from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Optional

import requests
import streamlit as st

from exam_system.config import settings


@dataclass(frozen=True)
class RepoInfo:
    owner: str
    repo: str
    branch: str


def _repo() -> RepoInfo:
    return RepoInfo(
        owner=settings.GH_OWNER or "",
        repo=settings.GH_REPO or "",
        branch=settings.GH_BRANCH or "main",
    )


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json"}
    if settings.GH_TOKEN:
        h["Authorization"] = f"Bearer {settings.GH_TOKEN}"
    return h


def require_write_or_warn() -> bool:
    ok, msg = settings.gh_write_ready()
    if not ok:
        st.warning("GitHub 寫入未啟用——" + msg)
    return ok


def api(path: str, method: str = "GET", **kwargs) -> Any:
    rinfo = _repo()
    if not rinfo.owner or not rinfo.repo:
        raise RuntimeError("GitHub secrets 未設定：REPO_OWNER / REPO_NAME")

    url = f"https://api.github.com/repos/{rinfo.owner}/{rinfo.repo}/{path}"
    resp = requests.request(method, url, headers=_headers(), **kwargs)
    if resp.status_code >= 400:
        snippet = (resp.text or "")[:300].replace("\n", " ")
        raise RuntimeError(f"GitHub API {method} {path} -> {resp.status_code}: {snippet}")
    return resp.json()


def get_sha(path: str) -> Optional[str]:
    try:
        rinfo = _repo()
        j = api(f"contents/{path}", params={"ref": rinfo.branch})
        return j.get("sha")
    except Exception:
        return None


def put_file(path: str, content_bytes: bytes, message: str) -> Any:
    rinfo = _repo()
    b64 = base64.b64encode(content_bytes).decode("ascii")
    payload: dict[str, Any] = {"message": message, "content": b64, "branch": rinfo.branch}
    sha = get_sha(path)
    if sha:
        payload["sha"] = sha
    return api(f"contents/{path}", method="PUT", json=payload)


@st.cache_data(ttl=300, show_spinner=False)
def download_bytes(path: str) -> bytes:
    rinfo = _repo()
    j = api(f"contents/{path}", params={"ref": rinfo.branch})
    if j.get("encoding") == "base64" and "content" in j:
        return base64.b64decode(j["content"])
    raw_url = f"https://raw.githubusercontent.com/{rinfo.owner}/{rinfo.repo}/{rinfo.branch}/{path}"
    return requests.get(raw_url, headers=_headers(), timeout=30).content


def clear_download_cache() -> None:
    download_bytes.clear()


def read_pointer() -> dict:
    try:
        data = download_bytes(settings.POINTER_FILE)
        return json.loads(data.decode("utf-8"))
    except Exception:
        return {}


def write_pointer(obj: dict) -> None:
    if not require_write_or_warn():
        return
    put_file(
        settings.POINTER_FILE,
        json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"),
        "update bank pointers",
    )
    clear_download_cache()


def migrate_pointer_prefix_if_needed() -> None:
    conf = read_pointer()
    changed = False

    # legacy: banks/xxx -> bank/xxx (or your BANKS_DIR)
    if isinstance(conf.get("path"), str) and conf["path"].startswith("banks/"):
        conf["path"] = conf["path"].replace("banks/", f"{settings.BANKS_DIR}/", 1)
        changed = True

    cur = conf.get("current")
    if isinstance(cur, dict):
        for k, p in list(cur.items()):
            if isinstance(p, str) and p.startswith("banks/"):
                cur[k] = p.replace("banks/", f"{settings.BANKS_DIR}/", 1)
                changed = True

    if changed:
        try:
            write_pointer(conf)
        except Exception as e:
            st.warning(f"自動遷移 {settings.POINTER_FILE} 失敗：{e}")


def get_current_bank_path(bank_type: Optional[str] = None) -> str:
    conf = read_pointer()
    current = conf.get("current")

    if isinstance(current, dict):
        if bank_type:
            p = current.get(bank_type)
            if isinstance(p, str) and p:
                return p

    legacy = conf.get("path")
    if isinstance(legacy, str) and legacy and not bank_type:
        return legacy

    # ultimate fallback
    return st.secrets.get("BANK_FILE", f"{settings.BANKS_DIR}/exam_bank.xlsx")


def set_current_bank_path(bank_type: str, path: str) -> None:
    if not require_write_or_warn():
        return

    if not path.startswith(f"{settings.BANKS_DIR}/"):
        path = f"{settings.type_dir(bank_type)}/{path}"

    conf = read_pointer()
    if "current" not in conf or not isinstance(conf.get("current"), dict):
        conf["current"] = {}
    conf["current"][bank_type] = path

    write_pointer(conf)


def list_bank_files(bank_type: Optional[str] = None) -> list[str]:
    """
    只列出「該類型資料夾」內第一層的 .xlsx 檔。
    例如 bank/產險/*.xlsx
    """
    try:
        rinfo = _repo()
        folder = settings.type_dir(bank_type) if bank_type else settings.BANKS_DIR
        items = api(f"contents/{folder}", params={"ref": rinfo.branch})
        out = []
        for it in items:
            if it.get("type") == "file" and str(it.get("name", "")).lower().endswith(".xlsx"):
                out.append(it["path"])
        return out
    except Exception:
        return []


def debug_repo_snapshot(bank_type: Optional[str] = None) -> dict[str, Any]:
    """
    方便你在 UI 上 st.json() 看現在 GitHub 端到底讀到什麼
    """
    return {
        "repo": {"owner": settings.GH_OWNER, "repo": settings.GH_REPO, "branch": settings.GH_BRANCH},
        "BANKS_DIR": settings.BANKS_DIR,
        "POINTER_FILE": settings.POINTER_FILE,
        "current_bank_path": get_current_bank_path(bank_type),
        "files_in_type": list_bank_files(bank_type) if bank_type else list_bank_files(None),
    }
