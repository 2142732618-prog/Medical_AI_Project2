# /root/Medical_AI_Project_V2/config.py
import os
import platform

# --- 1. 环境识别 ---
IS_SERVER = platform.system() == "Linux"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 2. 核心路径---
if IS_SERVER:
    # 适配 AutoDL 数据盘，解决系统盘空间不足导致的 Killed 问题
    DATA_ROOT = "/root/autodl-tmp/Project_Data"
    # 定义临时解压路径，同样放在数据盘
    TEMP_EXTRACT_DIR = "/root/autodl-tmp/temp_extract"
else:
    # 本地开发测试环境
    DATA_ROOT = os.path.join(BASE_DIR, "Local_Project_Data")
    TEMP_EXTRACT_DIR = os.path.join(BASE_DIR, "temp_extract")

# 确保全局根目录和临时目录存在
os.makedirs(DATA_ROOT, exist_ok=True)
os.makedirs(TEMP_EXTRACT_DIR, exist_ok=True)

# --- 3. 动态路径获取函数 ---
def get_user_paths(username):
    """
    根据用户名在数据盘生成对应的私有文件夹结构。
    """
    user_base = os.path.join(DATA_ROOT, username)
    
    paths = {
        "root": user_base,
        "raw": os.path.join(user_base, "raw_data"),   # 存放上传的原始 ZIP/DICOM
        "output": os.path.join(user_base, "output"), # 存放 AI 推理结果 (raw.nii.gz + mask.nii.gz)
        "temp": os.path.join(DATA_ROOT, username, "temp_extract") # 改为用户私有临时目录                   
    }
    
    # 自动创建用户目录及子目录
    for p in paths.values():
        os.makedirs(p, exist_ok=True)
        
    return paths

# --- 4. 医疗影像标准配置 ---
WINDOW_LEVELS = {
    "软组织": (400, 40, (300, 500), (30, 80)),
    "肺窗": (1500, -600, (1000, 2000), (-600, 400)),
    "骨窗": (2000, 500, (2000, 4000), (200, 600)),
    "脑窗": (80, 40, (70, 100), (30, 50))
}

# --- 5. UI 与 主题配置 ---
THEME_COLOR = "#007AFF"  
BG_COLOR = "#0E1117"     

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
BG_IMAGE_PATH = os.path.join(ASSETS_DIR, "school_bg.jpg")

# 登录框宽度适配
LOGIN_BOX_WIDTH_DESKTOP = "35vw"
LOGIN_BOX_WIDTH_MOBILE = "85vw"

# --- 启动自检输出 ---
print(f"[Config] 当前运行环境: {'AutoDL 远程服务器' if IS_SERVER else '本地开发模式'}")
print(f"[Config] 数据存储中心: {DATA_ROOT}")
if IS_SERVER:
    print(f"[Config] 临时解压区已定向至数据盘，有效防止内存溢出。")