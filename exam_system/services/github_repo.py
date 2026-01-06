"""
GitHub Repository 操作服務
負責所有與 GitHub API 的互動
"""
import json
import base64
import requests
import streamlit as st
from typing import Optional

from exam_system.config import settings


class GitHubRepoService:
    """GitHub 儲存庫服務"""
    
    def __init__(self):
        self.owner = settings.GH_OWNER
        self.repo = settings.GH_REPO
        self.branch = settings.GH_BRANCH
        self.token = settings.GH_TOKEN
        self.banks_dir = settings.BANKS_DIR
        self.pointer_file = settings.POINTER_FILE
        
        # 驗證基本設定
        ok, msg = settings.validate_github_config()
        if not ok:
            st.error(f"GitHub 設定錯誤：{msg}")
            st.stop()
    
    def _headers(self) -> dict:
        """取得 API 請求標頭"""
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h
    
    def _api_request(self, path: str, method: str = "GET", **kwargs):
        """發送 GitHub API 請求"""
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/{path}"
        r = requests.request(method, url, headers=self._headers(), **kwargs)
        
        if r.status_code >= 400:
            snippet = r.text[:300].replace("\n", " ")
            raise RuntimeError(
                f"GitHub API {method} {path} -> {r.status_code}: {snippet}"
            )
        return r.json()
    
    def _get_file_sha(self, path: str) -> Optional[str]:
        """取得檔案的 SHA（用於更新檔案）"""
        try:
            j = self._api_request(f"contents/{path}", params={"ref": self.branch})
            return j.get("sha")
        except Exception:
            return None
    
    @st.cache_data(ttl=300, show_spinner=False)
    def download_file_bytes(_self, path: str) -> bytes:
        """
        從 GitHub 下載檔案（二進位）
        使用 _self 避免 Streamlit cache 序列化問題
        """
        try:
            j = _self._api_request(f"contents/{path}", params={"ref": _self.branch})
            if j.get("encoding") == "base64":
                return base64.b64decode(j["content"])
        except Exception:
            pass
        
        # 降級使用 raw URL
        raw_url = f"https://raw.githubusercontent.com/{_self.owner}/{_self.repo}/{_self.branch}/{path}"
        r = requests.get(raw_url, headers=_self._headers())
        if r.status_code >= 400:
            raise RuntimeError(f"無法下載檔案：{path}")
        return r.content
    
    def upload_file(self, path: str, content_bytes: bytes, message: str):
        """上傳或更新檔案到 GitHub"""
        ok, msg = settings.validate_github_write_config()
        if not ok:
            st.warning(f"GitHub 寫入未啟用：{msg}")
            return False
        
        b64 = base64.b64encode(content_bytes).decode("ascii")
        payload = {
            "message": message,
            "content": b64,
            "branch": self.branch
        }
        
        sha = self._get_file_sha(path)
        if sha:
            payload["sha"] = sha
        
        try:
            self._api_request(f"contents/{path}", method="PUT", json=payload)
            # 清除快取
            self.download_file_bytes.clear()
            return True
        except Exception as e:
            st.error(f"上傳失敗：{e}")
            return False
    
    def list_files_in_folder(self, folder: str) -> list[str]:
        """列出資料夾內的所有 .xlsx 檔案"""
        try:
            items = self._api_request(f"contents/{folder}", params={"ref": self.branch})
            return [
                item["path"]
                for item in items
                if item["type"] == "file" and item["name"].lower().endswith(".xlsx")
            ]
        except Exception:
            return []
    
    def list_bank_files(self, bank_type: Optional[str] = None) -> list[str]:
        """列出題庫檔案"""
        if bank_type:
            folder = settings.get_type_dir(bank_type)
        else:
            folder = self.banks_dir
        return self.list_files_in_folder(folder)
    
    def read_pointer(self) -> dict:
        """讀取題庫指標檔"""
        try:
            data = self.download_file_bytes(self.pointer_file)
            return json.loads(data.decode("utf-8"))
        except Exception:
            return {}
    
    def write_pointer(self, obj: dict) -> bool:
        """寫入題庫指標檔"""
        ok, msg = settings.validate_github_write_config()
        if not ok:
            st.warning(f"GitHub 寫入未啟用：{msg}")
            return False
        
        content = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        return self.upload_file(self.pointer_file, content, "update bank pointers")
    
    def get_current_bank_path(self, bank_type: Optional[str] = None) -> str:
        """取得目前使用的題庫路徑"""
        conf = self.read_pointer()
        current = conf.get("current")
        
        if isinstance(current, dict) and bank_type:
            p = current.get(bank_type)
            if p:
                return p
        
        # 向下相容：舊版單一路徑
        legacy = conf.get("path")
        if legacy and not bank_type:
            return legacy
        
        return settings.DEFAULT_BANK_FILE
    
    def set_current_bank_path(self, bank_type: str, path: str) -> bool:
        """設定目前使用的題庫路徑"""
        # 確保路徑格式正確
        if not path.startswith(f"{self.banks_dir}/"):
            path = f"{settings.get_type_dir(bank_type)}/{path}"
        
        conf = self.read_pointer()
        if "current" not in conf or not isinstance(conf.get("current"), dict):
            conf["current"] = {}
        
        conf["current"][bank_type] = path
        return self.write_pointer(conf)
    
    def migrate_old_pointer_if_needed(self):
        """遷移舊版指標檔格式"""
        conf = self.read_pointer()
        changed = False
        
        # 修正舊的 banks/ 前綴
        if isinstance(conf.get("path"), str) and conf["path"].startswith("banks/"):
            conf["path"] = conf["path"].replace("banks/", f"{self.banks_dir}/", 1)
            changed = True
        
        cur = conf.get("current")
        if isinstance(cur, dict):
            for k, p in list(cur.items()):
                if isinstance(p, str) and p.startswith("banks/"):
                    cur[k] = p.replace("banks/", f"{self.banks_dir}/", 1)
                    changed = True
        
        if changed:
            self.write_pointer(conf)


# 建立全域實例
github_service = GitHubRepoService()

# 執行遷移
github_service.migrate_old_pointer_if_needed()
