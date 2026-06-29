import streamlit as st
import base64
import os
import random
from config import (
    LOGIN_BOX_WIDTH_DESKTOP, 
    LOGIN_BOX_WIDTH_MOBILE,
    BG_IMAGE_PATH,
    THEME_COLOR
)
from utils.ui_utils import login_view_style

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

st.markdown("<style>[data-testid='stSidebar'] {display:none !important;}</style>", unsafe_allow_html=True)

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def show_login_page():

    BG_IMAGES = [
        os.path.join(BASE_DIR, "assets", "bg1.jpg"),
        os.path.join(BASE_DIR, "assets", "bg2.jpeg"),
        os.path.join(BASE_DIR, "assets", "bg3.jpg"),
        os.path.join(BASE_DIR, "assets", "bg4.jpg")
    ]

    if "random_bg" not in st.session_state:
        st.session_state["random_bg"] = random.choice(BG_IMAGES)
    
    current_bg = st.session_state["random_bg"]

    img_base64 = ""
    try:
        if os.path.exists(current_bg):
            img_base64 = get_base64_of_bin_file(current_bg)
        else:
            st.error(f"找不到背景图片: {current_bg}")
    except Exception as e:
            st.error(f"背景加载失败: {e}")

    if img_base64:
        ext = current_bg.split('.')[-1].lower()
        mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
        st.markdown(f"""
            <style>
            /* 强制作用于整个 App 容器 */
            .stApp {{
                background: url("data:{mime_type};base64,{img_base64}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}

            /* 将所有可能遮挡背景的中间层设为透明 */
            [data-testid="stAppViewContainer"], 
            [data-testid="stHeader"], 
            [data-testid="stToolbar"],
            [data-testid="stCanvas"] {{
                background-color: transparent !important;
                background: transparent !important;
            }}
            /* 针对内容容器的透明化 */
            .main .block-container {{
                background-color: transparent;
            }}
            </style>
        """, unsafe_allow_html=True)
    

    # 3. 标题区域 
    st.markdown(f"""
        <div style="text-align: center; margin-top: 8vh; margin-bottom: 3vh;">
            <h1 style="color: white; font-weight: 900; font-size: 3rem; text-shadow: 2px 4px 10px rgba(0,0,0,0.7);">
                基于深度学习的医学影像智能分析与辅助决策平台
            </h1>
            <p style="color: white; font-size: 1.5rem; font-weight: 600; text-shadow: 1px 2px 5px rgba(0,0,0,0.7);">
                208210308 丁梓桓 &nbsp;&nbsp;&nbsp; 指导教师：王丽敏
            </p>
        </div>
    """, unsafe_allow_html=True)

    # 4. 登录组件
    col_l, col_m, col_r = st.columns([1, 1, 1])
    with col_m:
        username = st.text_input("user", placeholder="admin", label_visibility="collapsed")
        password = st.text_input("pass", placeholder="123456", type="password", label_visibility="collapsed")
        
        if st.button("登 录 系 统", use_container_width=True, type="primary"):
            if username == "admin" and password == "123456":
                st.session_state["step"] = "MENU"
                st.session_state["logged_in"] = True 
                st.session_state["username"] = "admin" 
                st.session_state["volume"] = None
                st.rerun()
            else:
                st.error("账户或密码有误")
        st.markdown('</div>', unsafe_allow_html=True)

    # 5. 页脚
    st.markdown("""
        <div style="text-align: center; margin-top: 30px;">
            <p style="color: rgba(255, 255, 255, 0.6); font-size: 1rem; font-weight: 400;">
               知行统一 创业创新
            </p>
        </div>
    """, unsafe_allow_html=True)