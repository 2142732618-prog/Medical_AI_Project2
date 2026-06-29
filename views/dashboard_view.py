import streamlit as st
import os
import math
import shutil
import time
import threading
import torch
import config
from image_processing.engine import get_engine
from utils.ui_utils import dashboard_view_style

# ==================== 1. 工具函数 ====================

def get_data_list(path):
    if not os.path.exists(path): return []
    return sorted([f for f in os.listdir(path) if not f.startswith('.')])

def render_pagination(page_key, total_pages, label):
    if total_pages <= 1: return
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1: st.caption(f"{label}: {st.session_state[page_key]} / {total_pages}")
    with col2:
        if st.button("上一页", key=f"prev_{page_key}"):
            st.session_state[page_key] = max(1, st.session_state[page_key] - 1); st.rerun()
    with col3:
        if st.button("下一页", key=f"next_{page_key}"):
            st.session_state[page_key] = min(total_pages, st.session_state[page_key] + 1); st.rerun()

def retry_upload(max_retries=3, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries - 1:
                        raise e
                    time.sleep(delay * (i + 1))  
            return None
        return wrapper

# ==================== 2. 弹窗 ====================

@st.dialog("AI 分割任务", width="small")
def run_inference_dialog():
    case_name = st.session_state.get("active_case")
    f_path = st.session_state.get("active_path")
    user = st.session_state.get("username", "admin")
    paths = config.get_user_paths(user)
    
    # 1. 唯一线程名
    target_thread_name = f"AI_Thread_{case_name}"

    if "task_result" not in st.session_state: st.session_state.task_result = None
    if "is_running" not in st.session_state: st.session_state.is_running = False

    # 2. 检查后台线程（增加一层过滤，确保匹配准确）
    all_active_threads = [t.name for t in threading.enumerate()]
    is_alive = any(target_thread_name == name for name in all_active_threads)

    # 3. 启动逻辑
    if not is_alive and st.session_state.task_result is None:
        # 如果还没开始跑，则启动
        if not st.session_state.is_running:
            st.session_state.is_running = True
            
            def worker():
                try:
                    success, msg, res = get_engine().run_full_pipeline(f_path, case_name, paths["output"])
                    st.session_state.task_result = (success, msg, res)
                except Exception as e:
                    st.session_state.task_result = (False, str(e), None)
                finally:
                    st.session_state.is_running = False

            t = threading.Thread(target=worker, name=target_thread_name)
            t.daemon = True
            t.start()
            time.sleep(0.5) 
            st.rerun()

    # 4. 展示逻辑
    if is_alive:
        st.markdown(f"正在处理: **{case_name}**")
        st.spinner("AI 引擎推理中...")
        time.sleep(2)
        st.rerun()
    elif st.session_state.task_result is None:
        st.warning("正在等待后台响应...")
        time.sleep(1)
        st.rerun()

    # 5. 结果展示
    if st.session_state.task_result:
        success, msg, _ = st.session_state.task_result
        if success:
            st.success("✅ 处理完成")
        else:
            st.error(f"❌ 失败: {msg}")
        
        if st.button("关闭", use_container_width=True):
            st.session_state.task_result = None
            st.session_state.is_running = False
            st.rerun()

# ==================== 3. 主页面逻辑 ====================

def show_dashboard_page(theme="Dark"):
    dashboard_view_style(theme)
    user = st.session_state.get("username", "admin")
    paths = config.get_user_paths(user)
    
    # 初始化分页状态
    if "p_raw" not in st.session_state: st.session_state.p_raw = 1
    if "p_out" not in st.session_state: st.session_state.p_out = 1

    # 顶部导航与导入
    c_back, c_upload, _ = st.columns([1.5, 2, 7])
    with c_back:
        if st.button("← 返回菜单", use_container_width=True):
            st.session_state["step"] = "MENU"; 
            st.rerun()
            
    with c_upload:
        with st.popover("📤 影像导入", use_container_width=True):
            up_files = st.file_uploader(
                "支持 ZIP / NIfTI 格式", 
                type=["zip", "nii", "nii.gz"], 
                label_visibility="collapsed", 
                accept_multiple_files=True
            )
            
            if up_files:
                user = st.session_state.get("username", "admin")
                paths = config.get_user_paths(user)
                os.makedirs(paths["raw"], exist_ok=True)
                success_count = 0

                # 3. 定义内部写入逻辑
                def write_file_chunks(file_obj, target_path):
                    chunk_size = 1024 * 1024
                    file_obj.seek(0)
                    with open(target_path, "wb") as f:
                        while True:
                            chunk = file_obj.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                
                for up_file in up_files:

                    orig_name = up_file.name

                    if orig_name.endswith(".nii.gz"):
                        name_prefix = orig_name[:-7] # 去掉 .nii.gz
                        ext = ".nii.gz"
                    elif orig_name.endswith(".nii"):
                        name_prefix = orig_name[:-4] # 去掉 .nii
                        ext = ".nii.gz" # 强制统一转为 .gz 压缩格式节省空间
                    else:
                        name_prefix = os.path.splitext(orig_name)[0]
                        ext = os.path.splitext(orig_name)[1]

                    # 自动补齐 nnU-Net 要求的 _0000 标识符
                    if not name_prefix.endswith("_0000") and ext in [".nii", ".nii.gz"]:
                        final_name = f"{name_prefix}_0000.nii.gz"
                        st.info(f"✨ 已自动规范化命名: `{final_name}`")
                    else:
                        final_name = orig_name
                    
                    save_path = os.path.join(paths["raw"], final_name)
                    
                    try:
                        # 使用分块写入
                        with open(save_path, "wb") as f:
                            f.write(up_file.getbuffer())
                        success_count += 1
                    except Exception as e:
                        st.error(f"❌ 保存失败: {str(e)}")

                # 状态反馈
                if success_count > 0:
                    st.toast(f"✅ 成功导入 {success_count} 个规范化文件")
                    st.rerun()            
    st.divider()


    col_l, col_r = st.columns(2, gap="large")
    # --- 左侧：原始序列---
    with col_l:
        st.subheader("📁 原始序列管理")
        raw_files = get_data_list(paths["raw"])
        if raw_files:
            per = 6
            start = (st.session_state.p_raw - 1) * per
            for f in raw_files[start : start + per]:
                with st.container(border=True):
                    c_txt, c_del, c_act = st.columns([3, 0.6, 0.8])
                    c_txt.markdown(f"<span style='color:#FFFFFF; font-size:14px; white-space:nowrap;'>📄 {f}</span>", unsafe_allow_html=True)
                    
                    with c_del:
                        if st.button("🗑️", key=f"dl_r_{f}"): os.remove(os.path.join(paths["raw"], f)); st.rerun()
                    with c_act:
                        if st.button("✂️", key=f"inf_{f}"):
                            st.session_state.update({"active_case": f.replace(".zip",""), "active_path": os.path.join(paths["raw"], f)})
                            run_inference_dialog()
            render_pagination("p_raw", math.ceil(len(raw_files)/per), "原始页码")
        else:
            st.caption("暂无数据")

    # --- 右侧：结果管理---
    with col_r:
        st.subheader("📁 分割结果")
        out_dirs = get_data_list(paths["output"])
        if out_dirs:
            per = 6
            start = (st.session_state.p_out - 1) * per
            for d in out_dirs[start : start + per]:
                with st.container(border=True):
                    c_txt, c_del = st.columns([4, 0.6])
                    with c_txt.expander(f"📦 {d}"):
                        dp = os.path.join(paths["output"], d)
                        if os.path.isdir(dp):
                            for item in os.listdir(dp): st.caption(f"└ {item}")
                    with c_del:
                        if st.button("🗑️", key=f"dl_o_{d}"):
                            shutil.rmtree(os.path.join(paths["output"], d)); st.rerun()
            render_pagination("p_out", math.ceil(len(out_dirs)/per), "结果页码")