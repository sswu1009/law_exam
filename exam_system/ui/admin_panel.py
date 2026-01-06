# exam_system/ui/admin_panel.py
import streamlit as st
from exam_system.config import settings
from exam_system.services import github_repo

def render_admin_panel():
    with st.expander("🛠 題庫管理（管理者）", expanded=False):
        if "admin_ok" not in st.session_state:
            st.session_state.admin_ok = False

        pwd = st.text_input("管理密碼", type="password")
        if st.button("登入"):
            if pwd == settings.ADMIN_PASSWORD:
                st.session_state.admin_ok = True
                st.success("已登入")
            else:
                st.error("密碼錯誤")

        if st.session_state.admin_ok:
            st.write("### 上傳新題庫")
            ok, msg = github_repo.check_write_permission()
            if not ok:
                st.warning(msg)
            else:
                up_type = st.selectbox("類型", options=settings.BANK_TYPES)
                up = st.file_uploader("選擇 Excel", type=["xlsx"])
                name = st.text_input("檔名 (例如 bank_v2.xlsx)", value="new_bank.xlsx")
                set_now = st.checkbox("上傳後立即設為預設", value=True)

                if st.button("上傳"):
                    if up and name:
                        dest = f"{settings.get_type_dir(up_type)}/{name}"
                        try:
                            github_repo.put_file(dest, up.getvalue(), f"Admin upload {name}")
                            if set_now:
                                github_repo.set_current_bank_path(up_type, dest)
                            st.success(f"成功上傳：{dest}")
                        except Exception as e:
                            st.error(f"失敗：{e}")

            st.write("### 切換預設題庫")
            s_type = st.selectbox("類型", options=settings.BANK_TYPES, key="adm_sw_type")
            files = github_repo.list_files(settings.get_type_dir(s_type))
            if files:
                cur = github_repo.get_current_bank_path(s_type)
                idx = files.index(cur) if cur in files else 0
                pick = st.selectbox("選擇檔案", options=files, index=idx, key="adm_sw_file")
                if st.button("套用變更"):
                    github_repo.set_current_bank_path(s_type, pick)
                    st.success(f"已更新預設：{pick}")
            else:
                st.info("無檔案")
