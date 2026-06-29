import streamlit as st

def base_style(theme="Dark"):
    """
    基础样式：根据 theme 切换配色
    """
    # 定义颜色字典
    colors = {
        "Dark": {
            "bg": "#0e1117",
            "main_text": "#00D4FF",
            "sub_text": "#888888",
            "card_bg": "#25282C",
            "card_border": "#3A3F45"
        },
        "Light": {
            "bg": "#E5E7EB",          
            "main_text": "#000000",  
            "sub_text": "#4B5563",    
            "card_bg": "#F9FAFB",     
            "card_border": "#9CA3AF" 
        }
    }
    c = colors.get(theme, colors["Dark"])

    st.markdown(f"""
        <style>
            /* 全局背景 */
            .stApp {{ 
                background-color: {c['bg']} !important; 
                color: {c['sub_text']} !important;
            }}
            
            /* 标题与文字 */
            h1, h2, h3, .main-title, b, span, label {{ 
                color: {c['main_text']} !important; 
                font-family: "Microsoft YaHei", sans-serif;
            }}

            /* 隐藏顶部白色页眉 */
            [data-testid="stHeader"] {{ background: transparent !important; display: none !important; }}
            header {{ visibility: hidden; }}

            /* 内容容器 */
            .block-container {{ padding-top: 2rem !important; max-width: 98% !important; }}
            
            /* 针对 Light 模式的特殊处理：输入框边框 */
            {"input { border: 1px solid #CCC !important; }" if theme == "Light" else ""}
        </style>
    """, unsafe_allow_html=True)

def login_view_style(img_base64, box_width_mobile, box_width_desktop, theme_color):

    base_style(theme="Dark")
    
    st.markdown(f"""
        <style>
        /* 强制隐藏侧边栏 */
        [data-testid="stSidebar"] {{ display: none !important; }}
        [data-testid="stSidebarNav"] {{ display: none !important; }}

        /* 全屏背景图注入 */
        .stApp {{
            background-image: url("data:image/png;base64,{img_base64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        
        /* 磨砂玻璃登录容器 */
        .login-box {{ 
            background: rgba(14, 17, 23, 0.7); /* 深色半透明 */
            backdrop-filter: blur(15px);
            padding: 40px;
            border-radius: 20px;
            border: 1px solid rgba(0, 212, 255, 0.2); /* 科技蓝边框 */
            box-shadow: 0 15px 35px rgba(0,0,0,0.5);
            margin: 0 auto; 
            width: {box_width_mobile} !important; 
        }}
        
        @media (min-width: 1024px) {{
            .login-box {{ width: {box_width_desktop} !important; }}
        }}

        /* 登录按钮配色对齐 */
        button[kind="primary"] {{ 
            background-color: #DCDCDC !important; 
            border: none !important;
            box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
        }}
        
        /* 输入框焦点颜色 */
        input:focus {{
            border-color: #00D4FF !important;
        }}
        </style>
        """, unsafe_allow_html=True)

def menu_view_style(theme="Dark"):
    base_style(theme)
    card_bg = "#25282C" if theme == "Dark" else "#FFFFFF"
    card_border = "#3A3F45" if theme == "Dark" else "#D1D5DB"
    text_main = "#00D4FF" if theme == "Dark" else "#1E3A8A"
    btn_bg = "#31353B" if theme == "Dark" else "#F8F9FA"
    btn_text = "white" if theme == "Dark" else "#1E3A8A"
    shadow = "rgba(0,0,0,0.5)" if theme == "Dark" else "rgba(0,0,0,0.1)"

    st.markdown(f"""
        <style>
            /* --- 弹窗 --- */
            div[data-testid="stDialog"] {{
                background-color: {card_bg} !important;
                border: 1px solid {text_main} !important;
                border-radius: 15px !important;
            }}
            /* --- 功能卡片样式 --- */
            .feature-card {{
                background: {card_bg};
                border: 1px solid {card_border};
                border-radius: 12px;
                padding: 30px 15px;
                text-align: center;
                margin-bottom: 15px;
                box-shadow: 0 4px 15px {shadow};
                transition: transform 0.2s, border-color 0.2s;
            }}
            .feature-card:hover {{
                transform: translateY(-5px);
                border-color: {text_main};
            }}
            .feature-card h3 {{ 
                color: {text_main} !important; 
                margin: 0; 
            }}
            .feature-card p {{ 
                color: {"#888" if theme == "Dark" else "#4B5563"} !important; 
                font-size: 0.9rem; 
                margin-top: 8px; 
            }}

            /* --- 导航按钮样式 --- */
            .stButton button {{
                background-color: {btn_bg} !important;
                color: {btn_text} !important;
                border: 1px solid {card_border} !important;
                border-radius: 8px !important;
            }}
            .stButton button:hover {{
                border-color: {text_main} !important;
                color: {text_main} !important;
            }}
        </style>
    """, unsafe_allow_html=True)

def dicom_view_style(theme="Dark"):
    base_style(theme)
    is_dark = (theme == "Dark")
    panel_bg = "#25282C" if is_dark else "#F2F0E9"
    panel_border = "#3A3F45" if is_dark else "#D1D5DB"
    img_bg = "#000000" if is_dark else "#E9ECEF"
    # 白天模式文字改用深医疗蓝
    text_main = "#00D4FF" if is_dark else "#1E3A8A"
    text_sub = "#888888" if is_dark else "#495057"
    shadow = "rgba(0,0,0,0.3)" if is_dark else "rgba(0,0,0,0.08)"

    st.markdown(f"""
        <style>
            /* 顶部工具栏适配 */
            div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {{
                background: {panel_bg}; 
                border: 1px solid {panel_border}; 
                border-radius: 12px;
                padding: 12px; 
                margin-bottom: 5px; 
                box-shadow: 0 4px 10px {shadow};
            }}

            /* 影像容器适配*/
            [data-testid="stImage"] {{
                background: {img_bg} ;
                border: 1px solid {panel_border};
                border-radius: 8px;
                padding: 4px;
                display: flex;
                justify-content: center;
                height: 60vh !important;
            }}

            /* 右侧/中间面板文本适配 */
            [data-testid="column"]:last-child div[data-testid="stVerticalBlock"],
            .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
                color: {text_main} !important;
            }}

            /* 右侧面板主体适配 */
            [data-testid="column"]:last-child div[data-testid="stVerticalBlock"] {{
                background: {panel_bg} !important; 
                border: 1px solid {panel_border};
                border-radius: 12px; 
                padding: 20px !important; 
                min-height: 85vh;
            }}

            /* 针对“DICOM序列阅读”这种大提示框的文字颜色 */
            .stMarkdown p {{ color: {text_sub} !important; }}
            
            /* 修正 Slider 和 Label 在白底下的可见性 */
            label {{ color: {text_main} !important; }}
            .stCaption {{ text-align: center; color: {text_sub} !important; margin-top: 5px; }}
        </style>
    """, unsafe_allow_html=True)

def inference_view_style(theme="Dark"):
    base_style(theme)
    bg_box = "#000000" if theme == "Dark" else "#E5E7EB"
    border_color = "#333" if theme == "Dark" else "#CCC"
    
    st.markdown(f"""
        <style>
            .view-box, [data-testid="stImage"] {{
                background: {bg_box} !important;
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            /* 侧边栏适配 */
            [data-testid="stSidebar"] {{
                background-color: {"#16191E" if theme == "Dark" else "#FFFFFF"} !important;
                border-right: 1px solid {border_color};
            }}
        </style>
    """, unsafe_allow_html=True)

def diagnosis_view_style(theme="Dark"):
    base_style(theme)
    card_bg = "rgba(255, 255, 255, 0.05)" if theme == "Dark" else "rgba(0, 0, 0, 0.03)"
    card_border = "rgba(255, 255, 255, 0.1)" if theme == "Dark" else "rgba(0, 0, 0, 0.1)"
    title_color = "#5eead4" if theme == "Dark" else "#0D9488"

def dashboard_view_style(theme="Dark"):
    base_style(theme)
    card_bg = "rgba(255, 255, 255, 0.05)" if theme == "Dark" else "rgba(0, 0, 0, 0.03)"
    card_border = "rgba(255, 255, 255, 0.1)" if theme == "Dark" else "rgba(0, 0, 0, 0.1)"
    title_color = "#5eead4" if theme == "Dark" else "#0D9488"

    st.markdown("""
        <style>
            /* 1. 状态统计卡片 (Status Cards) */
            .status-card {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 12px 18px;
                margin-bottom: 10px;
            }
            .status-label { color: #888; font-size: 0.85rem; margin-bottom: 2px; }
            .status-value { color: #5eead4; font-weight: bold; font-size: 1.2rem; }

            /* 2. 文件上传区 (File Uploader) */
            [data-testid="stFileUploadDropzone"] {
                background: rgba(255, 255, 255, 0.03) !important;
                border: 2px dashed rgba(255, 255, 255, 0.1) !important;
                border-radius: 15px !important;
                padding: 10px !important;
            }

            /* 3. 按钮样式优化 (彻底解决文字折行与遮挡) */
            [data-testid="stButton"] button {
                border-radius: 6px;
                white-space: nowrap !important;
                overflow: visible !important;
                height: auto !important;
                padding: 0.5rem 1rem !important;
                transition: all 0.2s ease;
            }

            [data-testid="stButton"] button:hover {
                border-color: #5eead4 !important;
                color: #5eead4 !important;
                background: rgba(94, 234, 212, 0.08) !important;
            }

            /* 4. 文件列表项 (File List Items) */
            .file-item-row {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 10px 15px;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                transition: border-color 0.3s;
            }
            .file-item-row:hover {
                border-color: #5eead4;
                background: rgba(255, 255, 255, 0.07);
            }

            /* 5. 弹出窗口 (Popover) 统一样式 */
            .stPopover button {
                height: 44px !important;
                line-height: 44px !important;
            }
            
            /* 特色标题颜色覆盖 */
            h1, h2, h3 { color: #5eead4 !important; }
        </style>
    """, unsafe_allow_html=True)