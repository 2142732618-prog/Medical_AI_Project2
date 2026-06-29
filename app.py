import os
import torch
import streamlit as st

# 环境变量补丁
os.environ["TORCH_CUDA_ARCH_LIST"] = "9.0"
os.environ["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = "1024"
os.environ["nnUNet_n_proc_final_preprocess"] = "1"

# 基础配置
st.set_page_config(page_title="Medical_AI_Project", layout="wide", initial_sidebar_state="expanded")

# 统一初始化状态
if "initialized" not in st.session_state:
    # --- 开发调试开关 ---
    DEBUG_MODE = False
    
    if DEBUG_MODE:
        st.session_state["logged_in"] = True
        st.session_state["username"] = "admin"
        st.session_state["step"] = "MENU" # 初始进入菜单，之后通过点击跳转
    else:
        st.session_state["logged_in"] = False
        st.session_state["step"] = "LOGIN"
    st.session_state["initialized"] = True

# 导入视图
from views.login_view import show_login_page
from views.menu_view import show_menu_page
from views.dashboard_view import show_dashboard_page
from views.inference_view import show_inference_page
from views.dicom_view import show_dicom_page
from views.diagnosis_view import show_diagnosis_page

# 路由分发逻辑与主题切换
def main():
    # 1. 初始化全局主题状态
    if "theme" not in st.session_state:
        st.session_state.theme = "Dark"
    
    current_step = st.session_state.get("step", "LOGIN")
    theme = st.session_state.theme

    # 2. 登录状态判断
    if current_step != "LOGIN" and st.session_state.get("logged_in"):
        t_col1, t_col2 = st.columns([9, 1])
        with t_col2:
            is_light = st.toggle("☀", value=(theme == "Light"), key="global_theme_toggle")
            new_theme = "Light" if is_light else "Dark"
            if new_theme != theme:
                st.session_state.theme = new_theme
                st.rerun()

    if current_step == "LOGIN":
        show_login_page()
    elif current_step == "MENU":
        show_menu_page(theme)
    elif current_step == "DICOM_VIEW": 
        show_dicom_page(theme)
    elif current_step == "INFERENCE_VIEW": 
        show_inference_page(theme)
    elif current_step == "DIAGNOSIS_VIEW": 
        show_diagnosis_page(theme)
    elif current_step == "DASHBOARD":
        show_dashboard_page(theme)
    else:
        st.session_state["step"] = "LOGIN"
        st.rerun()

if __name__ == "__main__":
    main()