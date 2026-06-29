## 项目介绍
此项目为本人的本科毕业设计项目

本项目基于Streamlit框架编写，集成医学图像展示、分割以及简单智能诊断功能

内置模型包含：
1.TotalSegmentator模型 参考项目地址：https://github.com/wasserth/TotalSegmentator.git

2.自主训练器官模型

训练框架：nnUNet 参考项目地址：https://github.com/MIC-DKFZ/nnUNet.git

训练数据集：

https://www.kaggle.com/datasets/nih-chest-xrays/data

http://medicaldecathlon.com/dataaws/

以上数据来源皆公开免费

## 项目架构
```text
Medical_AI_Project_V2/
├── .streamlit/               # Streamlit 局部配置文件目录
├── assets/                   # 静态资源目录（如背景图片、校徽等）
├── fonts/                    # 字体文件目录
├── image_processing/         # 图像处理核心算法模块
│   ├── __init__.py           # 包初始化文件
│   ├── diagnosis_engine.py   # 诊断引擎（计算体积、灰度分布等临床指标）
│   ├── engine.py             # 核心处理引擎
│   ├── processor.py          # 图像预处理器
│   ├── reconstructor.py      # 序列处理与容积重建逻辑
│   └── threed_engine.py      # 3D 渲染与可视化引擎
├── static/                   # 静态文件托管目录
├── tmp_sandbox/              # 临时沙箱/测试数据缓存目录
├── utils/                    # 通用工具函数模块
│   └── ui_utils.py           # 界面样式与前端组件辅助工具
├── views/                    # Streamlit 多页面视图组件（前端界面）
│   ├── __init__.py           # 包初始化文件
│   ├── dashboard_view.py     # 数据看板/总览界面
│   ├── diagnosis_view.py     # 自动化诊断评估界面
│   ├── dicom_view.py         # DICOM 影像序列浏览界面
│   ├── inference_view.py     # AI 模型推理与分割结果展示界面
│   ├── login_view.py         # 用户登录与权限验证界面
│   └── menu_view.py          # 侧边栏/导航菜单界面
├── .gitignore                # Git 忽略文件配置文件
├── app.py                    # 项目主入口（负责多页面路由调度与初始化）
├── config.py                 # 项目全局配置文件（路径、常量等）
├── README.md                 # 项目说明文档
└── requirements.txt          # 项目依赖环境清单
```

## 如何使用：

### 1. 在线演示

您可以直接访问 https://medical-system.streamlit.app 在浏览器中运行。

### 2. 本地部署

**数据与权重放置说明 (关键)**
为了保证图像处理核心 (image_processing/engine.py) 和诊断引擎的正常运转，请确保：

模型权重： 将训练好的 nnU-Net 权重或 SAM 权重文件（如 .pth）放置在配置文件 config.py 中指定的指定模型目录下。

测试数据： 本地测试用的 3D/4D NIfTI (.nii.gz) 影像数据可存放于本地测试目录，项目已配置 .gitignore 策略，严禁将任何包含患者隐私（PHI）的真实临床数据上传至 GitHub。

如果您希望在本地运行，请确保已安装 Python 3.10+，然后执行以下步骤：

**1.打开powershell**

**2.克隆仓库**
```markdown
git clone [https://github.com/2142732618-prog/Medical_AI_Project2.git](https://github.com/2142732618-prog/Medical_AI_Project2.git)

cd Medical_AI_Project_V2
```

**3.安装 uv（若尚未安装）**
macOS / Linux 系统安装
```markdown
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```
Windows 系统 (PowerShell) 安装
```markdown
irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex
```

**4.创建并激活虚拟环境**
创建基于 Python 3.10+ 的虚拟环境
```markdown
uv venv --python 3.10
```
激活虚拟环境 (Linux/macOS)
```markdown
source .venv/bin/activate
```
激活虚拟环境 (Windows CMD)
```markdown
.venv\Scripts\activate.bat
```

**5.安装依赖**
```markdown
pip install -r requirements.txt
```


**6.运行应用**
```markdown
streamlit run app.py
```
启动成功后，终端会输出本地访问地址。打开浏览器访问 http://localhost:8501 即可进入系统主页。
