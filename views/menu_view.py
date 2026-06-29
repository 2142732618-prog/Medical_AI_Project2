import os
import config
import torch
import streamlit as st
from utils.ui_utils import menu_view_style

# --- 指示灯 ---
def get_gpu_status():
    """检测 GPU 是否可用并返回状态颜色和文字"""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        return "#00FF00", f"已连接: {gpu_name}"  # 绿色
    else:
        return "#FF0000", "未检测到显卡"  # 红色

def draw_gpu_light(color, text):
    """指示灯"""
    html = f"""
        <div style="display:flex; flex-direction:row; align-items:center;">
            <div style="width:10px; height:10px; background-color:{color}; border-radius:50%; 
                        margin-right:8px; box-shadow:0 0 8px {color}; animation:blink 2s infinite; flex-shrink:0;">
            </div>
            <div style="color:#ccc; font-size:14px; white-space:nowrap; line-height:10px;">
                {text}
            </div>
        </div>
        <style>
            @keyframes blink {{ 0%{{opacity:1;}} 50%{{opacity:0.4;}} 100%{{opacity:1;}} }}
        </style>
    """.replace('\n', '').replace('  ', '') 
    return html

# --- 定义弹窗组件 ---
@st.dialog("系统使用注意事项", width="medium")
def show_notice_dialog(pref_file_path):
    st.markdown("""
    ### 使用说明
    1. **数据隐私**：本平台仅供辅助诊断研究使用。
    2. **结果参考**：分割结果仅供参考，最终诊断请以执业医师签字报告为准。
    3. **注意事项**：确保已接入显卡，否则部分功能无法使用。
    4. **使用说明**：在文件中心上传或处理文件之后才可使用其他功能。
    """)
    
    st.write("---")
    
    # 选择框：永远不再弹出
    never_show = st.checkbox("不再显示此提示")
    
    if st.button("关闭", use_container_width=True, type="primary"):
        if never_show:
            # 确保目录存在
            os.makedirs(os.path.dirname(pref_file_path), exist_ok=True)
            # 写入标记文件
            with open(pref_file_path, "w", encoding="utf-8") as f:
                f.write("hide_notice")
        st.rerun()

# --- 主页面逻辑 ---
def show_menu_page(theme="Dark"):
    status_color, status_text = get_gpu_status()
    menu_view_style(theme)
    # 获取 admin 用户的路径配置
    username = st.session_state.get("username", "admin")
    user_paths = config.get_user_paths(username)
    # 获取用户根目录并拼接配置文件路径
    user_root_dir = os.path.dirname(user_paths["raw"]) 
    pref_file = os.path.join(user_root_dir, "pref.txt")

    # --- 弹窗触发逻辑 ---
    # 如果本地不存在 pref.txt 文件
    if not os.path.exists(pref_file):
        # 且本次会话还没弹出过
        if "notice_session_shown" not in st.session_state:
            # 标记为已弹出并执行弹窗
            st.session_state["notice_session_shown"] = True
            show_notice_dialog(pref_file)
    
    st.markdown("""
        <style>
            [data-testid="stHorizontalBlock"]:has(h1) {
            align-items: center !important;
        }
        </style>
    """, unsafe_allow_html=True)
    

    col_status, col_title, col_space  = st.columns([1, 2, 1])

    with col_status:
        # 呼吸灯效果的指示灯
        st.markdown(draw_gpu_light(status_color, status_text), unsafe_allow_html=True)

    with col_title:
        st.markdown("<h1 style='text-align: center; color: #00D4FF; padding: 40px 0;'>请选择功能模块</h1>", unsafe_allow_html=True)
    
    with col_space:
        st.empty()


    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="feature-card"><h3>文件中心</h3><p>数据管理与样本库</p></div>', unsafe_allow_html=True)
        if st.button("进入数据中心", use_container_width=True, key="nav_dashboard"):
            st.session_state["step"] = "DASHBOARD"
            st.rerun()

    with col2:
        st.markdown('<div class="feature-card"><h3>展示中心</h3><p>阅读DICOM序列</p></div>', unsafe_allow_html=True)
        if st.button("进入序列展示", use_container_width=True, key="nav_dicom"):
            st.session_state["step"] = "DICOM_VIEW"
            st.rerun()

    with col3:
        st.markdown('<div class="feature-card"><h3>分割重建中心</h3><p>查看AI分割重建效果</p></div>', unsafe_allow_html=True)
        if st.button("进入效果展示", use_container_width=True, key="nav_inference"):
            st.session_state["step"] = "INFERENCE_VIEW"
            st.rerun()

    with col4:
        st.markdown('<div class="feature-card"><h3>分割诊断中心</h3><p>特定器官分割与智能诊断</p></div>', unsafe_allow_html=True)
        if st.button("进入诊断中心", use_container_width=True, key="nav_diagnosis"):
            st.session_state["step"] = "DIAGNOSIS_VIEW"
            st.rerun()
    

    st.write("---")
    if st.button("退出系统", key="exit_sys"):
        st.session_state["step"] = "LOGIN"
        st.rerun()