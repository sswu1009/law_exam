from __future__ import annotations

import streamlit as st

from exam_system.config import settings
from exam_system.services import github_repo


def render_admin_panel():
    with st.sidebar.expander("🛠 題庫管理（管理者）", expanded=False):
        if "admin_ok" not in st.session_state:
            st.session_state.admin_ok = False

        pwd = st.text_input("管理密碼", type="password")
        if st.button("登入"):
            if pwd == settings.ADMIN_PASSWORD:
                st.session_state.admin_ok = True
                st.success("已登入")
            else:
                st.error("密碼錯誤")

        if not st.session_state.admin_ok:
            return

        st.write("### 上傳新題庫")
        up_type = st.selectbox("上傳到哪個類型？", options=settings.BANK_TYPES, index=0)
        up = st.file_uploader("選擇 Excel 題庫（.xlsx）", type=["xlsx"])
        name = st.text_input("儲存檔名（僅檔名，不含資料夾）", value="bank.xlsx")
        set_now = st.checkbox("上傳後設為該類型目前題庫", value=True)

        if st.button("上傳"):
            if up and name:
                dest = f"{settings.type_dir(up_type)}/{name}"
                try:
                    github_repo.put_file(dest, up.getvalue(), f"upload bank {name} -> {up_type}")
                    if set_now:
                        github_repo.set_current_bank_path(up_type, dest)
                    github_repo.clear_download_cache()
                    st.success(f"已上傳：{dest}" + ("，並已切換" if set_now else ""))
                except Exception as e:
                    st.error(f"上傳失敗：{e}")

        st.write("### 切換歷史題庫（依類型）")
        sel_type = st.selectbox("選擇類型", options=settings.BANK_TYPES, index=0, key="sel_type_switch")
        opts = github_repo.list_bank_files(sel_type)

        if opts:
            cur = github_repo.get_current_bank_path(sel_type)
            idx = opts.index(cur) if cur in opts else 0
            pick = st.selectbox("選擇題庫", options=opts, index=idx, key="pick_bank_switch")
            if st.button("套用選擇的題庫"):
                github_repo.set_current_bank_path(sel_type, pick)
                github_repo.clear_download_cache()
                st.success(f"已切換 {sel_type} 類型為：{pick}")
        else:
            st.info(f"{sel_type} 目前沒有 .xlsx。")

        st.divider()
        st.write("### Debug（檢查 GitHub 讀取狀態）")
        dbg_type = st.selectbox("Debug 類型", options=["(不選)"] + settings.BANK_TYPES, index=0, key="dbg_type")
        if st.button("顯示 Debug 資訊"):
            t = None if dbg_type == "(不選)" else dbg_type
            st.json(github_repo.debug_repo_snapshot(t))
