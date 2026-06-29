import streamlit as st
import os
import gc
import base64
import nibabel as nib
import numpy as np
from PIL import Image
from streamlit_vertical_slider import vertical_slider
import config
from image_processing.engine import get_engine
from utils.ui_utils import inference_view_style
from image_processing.engine import export_auto_colored_glb
from image_processing.diagnosis_engine import DiagnosisEngine
from image_processing.threed_engine import Simple3DEngine
import streamlit_vtkjs as st_vtk

def get_data_list(path):
    """获取指定目录下的文件列表，排除隐藏文件"""
    if not os.path.exists(path):
        return []
    items = [f for f in os.listdir(path) if not f.startswith('.')]
    return sorted(items)

def init_inference_states():
    """状态变量"""
    defaults = {
        "expander_state": True,
        "in_coord": [0, 0, 0],
        "v_spacing": [1, 1, 1],
        "show_overlay": True,
        "gui_show_3d": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- 图像处理核心---
def get_slice_mpr(volume, mask, axis, slice_idx, show_mask, alpha, spacing=None):
    if volume is None: return None
    try:
        # 1. 提取切片数据
        slice_idx = int(np.clip(slice_idx, 0, volume.shape[axis] - 1))
        v = np.take(volume, slice_idx, axis=axis)
        
        # 2. 窗宽窗位渲染
        ww, wl = 400, 40
        lower = wl - ww/2
        upper = wl + ww/2
        v = np.clip(v, lower, upper)
        v = (v - lower) / (upper - lower + 1e-5) * 255
        pil_img = Image.fromarray(v.astype('uint8')).convert("RGB")
        pil_img = pil_img.transpose(Image.FLIP_TOP_BOTTOM)
        # 3. 比例校正
        if spacing is not None:
            dx, dy, dz = spacing
            if axis == 2: # Sagittal
                new_h = int(pil_img.size[1] * (dz / dy))
                pil_img = pil_img.resize((pil_img.size[0], new_h), Image.NEAREST)
            elif axis == 1: # Coronal
                new_h = int(pil_img.size[1] * (dz / dx))
                pil_img = pil_img.resize((pil_img.size[0], new_h), Image.NEAREST)
        
        # 4. 掩码叠加逻辑
        if show_mask and mask is not None:
            m = np.take(mask, slice_idx, axis=axis)
            if m.max() > 0:
                # 针对不同器官筛选
                display_labels = st.session_state.get("display_labels")
                if display_labels is not None:
                    m = np.where(np.isin(np.round(m).astype(int), display_labels), m, 0)
                
                if m.max() > 0:
                    mask_alpha = (m > 0).astype('uint8') * int(255 * alpha)
                    m_pil = Image.fromarray(mask_alpha).convert("L")
                    m_pil = m_pil.transpose(Image.FLIP_TOP_BOTTOM)
                    m_pil = m_pil.resize(pil_img.size, Image.NEAREST)
                    red_layer = Image.new("RGB", pil_img.size, (255, 0, 0))
                    pil_img.paste(red_layer, (0, 0), m_pil)
            
        return pil_img 

    except Exception as e:
        print(f"Render Error: {e}")
        return None

if "expander_state" not in st.session_state:
    st.session_state.expander_state = False

# --- 主页面入口 ---
def show_inference_page(theme="Dark"):
    # 状态变量
    init_inference_states()
    # 获取引擎
    engine = get_engine()
    diag_engine = DiagnosisEngine()
    threed_engine = Simple3DEngine()

    inference_view_style(theme)
    
    username = st.session_state.get("username", "admin")
    paths = config.get_user_paths(username)

    # --- 顶部导航与控制区 ---
    nav_col1, nav_col2 = st.columns([1, 8])
    with nav_col1:
        if st.button("⬅返回", use_container_width=True):
            st.session_state["step"] = "MENU"
            st.rerun()
    with nav_col2:
        with st.expander("文件与设置", expanded=st.session_state.expander_state):
            c1, c2, c3 = st.columns([3, 3, 4])
            
            with c1:
                st.markdown("##### 📁 选择Output文件")
                out_list = get_data_list(paths["output"])
                selected_out = st.selectbox("查看结果", ["无选择"] + out_list, key="inf_select_out",label_visibility="collapsed")

                if selected_out != "无选择":
                    case_path = os.path.join(paths["output"], selected_out)
                    prefix = selected_out.split('_')[0] if '_' in selected_out else selected_out
                    raw_nii = os.path.join(case_path, f"{prefix}_raw.nii.gz")
                    mask_nii = os.path.join(case_path, f"{prefix}_mask.nii.gz")
                    
                    # 只有真正改变了选项才加载
                    if st.session_state.get("current_loaded_case") != selected_out:
                        res_r = engine.load_volume(raw_nii)
                        if res_r:
                            vol_data = res_r[0]
                            vol_data = np.transpose(vol_data, (2, 1, 0))
                            st.session_state.v_data = vol_data
                            st.session_state.v_spacing = res_r[1]
                            
                            if os.path.exists(mask_nii):
                                m_res = engine.load_volume(mask_nii)
                                if m_res:
                                    mask_data = m_res[0]
                                    # 存入 session_state，后面渲染才能拿到
                                    mask_data = np.transpose(mask_data, (2, 1, 0))
                                    st.session_state.m_data = mask_data.astype('uint8')
                            
                            st.session_state.coord = [vol_data.shape[0]//2, vol_data.shape[1]//2, vol_data.shape[2]//2]
                            st.session_state.current_loaded_case = selected_out
                            st.session_state.show_case_name = selected_out # 同步 ID
                            st.rerun()
                
                st.markdown("##### 3D展示")
                show , close = st.columns([1,1])
                with show:
                    if st.button("显示3D模型", use_container_width=True):
                        st.session_state.gui_show_3d = True
                
                with close:
                    if st.button("隐藏", use_container_width=True):
                        st.session_state.gui_show_3d = False
                        st.rerun()

            with c2:
                st.markdown("##### 器官切换与展示")
    
                # 动态识别：直接扫描文件夹里的 .nii.gz 文件
                if selected_out != "无选择":
                    case_path = os.path.join(paths["output"], selected_out)
        
                    # 获取该目录下所有的器官文件（排除 raw 原始图）
                    all_files = os.listdir(case_path)
                    organ_files = [f for f in all_files if f.endswith('.nii.gz') and 'raw' not in f and 'mask' not in f]
        
                    # 提取器官名称（去掉 .nii.gz）用于显示
                    available_organs = [f.replace('.nii.gz', '') for f in organ_files]
        
                    # 渲染多选框
                    selected_organ_names = st.multiselect(
                        "选择要加载的解剖结构",
                        options=["显示全部"] + sorted(available_organs),
                        default=["显示全部"],
                        key="organ_filter_v2"
                    )

                    # 根据选择，动态合并这些独立文件
                    if st.button("更新视图", use_container_width=True, type="primary"):
                        with st.spinner("正在重新提取目标组织..."):
                            # 确定要加载的文件列表
                            target_files = organ_files if "显示全部" in selected_organ_names else [f"{n}.nii.gz" for n in selected_organ_names]

                            # --- 物理合并逻辑 ---
                            combined_mask = None
                
                            for i, f_name in enumerate(target_files):
                                f_p = os.path.join(case_path, f_name)
                                # 只读取选中的文件
                                temp_img = nib.load(f_p)
                                temp_data = temp_img.get_fdata()
                    
                                if combined_mask is None:
                                    # 以第一个选中的器官为模板创建全黑矩阵
                                    combined_mask = np.zeros_like(temp_data)
                    
                                # 物理覆盖：将该器官的像素填入 combined_mask
                                # 赋予不同的 Label ID (i+1) 方便渲染器上色
                                combined_mask[temp_data > 0] = (i + 1)
                
                            # --- 4. 强制覆盖渲染状态 ---
                            # 这一步最关键：它把原本那个“全身 mask”彻底替换成了“仅含选中器官”的 mask
                            if combined_mask is not None:
                                # 转换轴向以适配你的渲染器 (之前代码里有 transpose)
                                render_data = np.transpose(combined_mask, (2, 1, 0))
                                st.session_state.m_data = render_data.astype('uint8')
                                # 告诉渲染器：现在只需要渲染这几个 ID
                                st.session_state["display_labels"] = list(range(1, len(target_files) + 1))
                    
                                st.toast(f"已成功隔离 {len(target_files)} 个解剖目标")
                                st.rerun() # 刷新模型刷新

                else:
                    st.info("请先在左侧选择病例。")
            
            with c3:
                d1, d2, space = st.columns([0.4, 0.4, 0.2])
                with d1:
                    st.markdown("##### 叠加控制")
                with d2:
                    st.session_state.show_overlay = st.checkbox("显示 Mask", value=True)
                alpha = st.slider("透明度", 0.0, 1.0, 0.5, key="inf_alpha_slider")
                st.markdown("<div style='margin-top:21px;'></div>", unsafe_allow_html=True)
                st.markdown("<div style='margin-bottom:5px;'></div>", unsafe_allow_html=True)

                if st.button("🔄 重置所有视图", use_container_width=True):
                    keys = ["v_data", "m_data", "show_case_name"]
                    for k in keys: 
                        if k in st.session_state: del st.session_state[k]
                    st.rerun()
        
        # 基础路径准备 
        case_name = st.session_state.get("show_case_name")
        case_path = os.path.join(paths["output"], case_name) if case_name else None
        
        # 路径探测逻辑
        target_glb = None
        if case_path:
            prefix = case_name.split('_')[0]
            possible_names = [f"{prefix}.glb", f"{prefix}_colored.glb", "series-00001.glb"]
            for name in possible_names:
                test_path = os.path.join(case_path, name)
                if os.path.exists(test_path):
                    target_glb = test_path
                    break

        # 3D 渲染与自动生成逻辑
        # --- 核心渲染逻辑 ---
        if st.session_state.get("gui_show_3d") and selected_out != "无选择":
            try:
                # 只有需要重建时才生成
                if st.session_state.get("needs_reconstruct", True) or "v_final_html" not in st.session_state:
                    with st.spinner("🔧 正在生成3D模型..."):
                        # 生成 HTML
                        html_content = threed_engine.generate_html(
                            st.session_state.m_data, 
                            st.session_state.v_spacing
                        )
                        # 存入 session 防止重复生成
                        st.session_state.v_final_html = html_content
                        st.session_state.needs_reconstruct = False

                # 最终渲染（一定有值）
                st.components.v1.html(st.session_state.v_final_html, height=680, scrolling=False)

            except Exception as e:
                st.error(f"3D渲染出错：{str(e)}")
                st.session_state.v_final_html = "<div style='color:white'>3D加载失败</div>"
    # --- B. 主界面布局渲染 ---
    package = st.session_state.get("v_data")
    spacing = st.session_state.get("v_spacing", [1, 1, 1])
    m_data = st.session_state.get("m_data")
    alpha = st.session_state.get("inf_alpha_slider", 0.5)

    show_mask_val = st.session_state.get("show_overlay", True)


    if package is None:
        st.markdown("""
            <div style="background:#25282C; border:1px dashed #00D4FF; border-radius:15px; padding:60px; text-align:center; margin-top:10vh;">
                <h2 style="color:#00D4FF;">请点击选择文件进行展示</h2>
                <p style="color:#888;">加载DICOM序列或分割结果以开启多视图预览</p>
            </div>
        """, unsafe_allow_html=True)
        st.stop()

    if isinstance(package, tuple):
        v_data = package[0]
    else:
        v_data = package
    
    dims = v_data.shape

    # 三等分布局
    v_col1, v_col2, v_col3 = st.columns(3)

    # 渲染开始前，重新抓取
    v_vol = st.session_state.get("v_data")[0] if isinstance(st.session_state.get("v_data"), tuple) else st.session_state.get("v_data")
    m_vol = st.session_state.get("m_data") # 拿到 Mask 数组
    s_mask = st.session_state.get("show_overlay", True) # 对应 Checkbox 的状态
    s_alpha = st.session_state.get("inf_alpha_slider", 0.5) # 对应 Slider 的状态

    # 调用 get_slice_mpr
    img = get_slice_mpr(v_vol, m_vol, 0, st.session_state.coord[0], s_mask, s_alpha, spacing)

    # --- Axial (Z) ---
    with v_col1:
        slider, image = st.columns([1, 15])
        with slider: 
            st.session_state.coord[0] = vertical_slider(
                label="Z", 
                min_value=0, 
                max_value=dims[0]-1, 
                default_value=st.session_state.coord[0], 
                key="inf_z", 
                height=240
            )
        with image:
            img = get_slice_mpr(v_data, m_data, 0, st.session_state.coord[0], s_mask, s_alpha, spacing=spacing)
            #st.write(f"Mask状态: {m_vol is not None}, 开关: {s_mask}, 透明度: {s_alpha}")
            if img: st.image(img, use_container_width=True, output_format="JPEG", caption=f"Axial (Z): {st.session_state.coord[0]}")

    # --- Sagittal (X) ---
    with v_col2:
        slider, image = st.columns([1, 15])
        with slider: 
            st.session_state.coord[2] = vertical_slider(
                label="X",
                min_value=0, 
                max_value=dims[2]-1, 
                default_value=st.session_state.coord[2], 
                key="inf_x", 
                height=240
            )
        with image:
            img = get_slice_mpr(v_data, m_data, 2, st.session_state.coord[2], s_mask,s_alpha, spacing=spacing)
            if img: st.image(img, use_container_width=True, output_format="JPEG", caption=f"Sagittal (X): {st.session_state.coord[2]}")

    # --- Coronal (Y) ---
    with v_col3:
        slider, image = st.columns([1, 15])
        with slider: 
            st.session_state.coord[1] = vertical_slider(
                label="Y", 
                min_value=0, 
                max_value=dims[1]-1, 
                default_value=st.session_state.coord[1], 
                key="inf_y", 
                height=240
            )
        with image:
            img = get_slice_mpr(v_data, m_data, 1, st.session_state.coord[1], s_mask, s_alpha, spacing=spacing)
            if img: st.image(img, use_container_width=True, output_format="JPEG", caption=f"Coronal (Y): {st.session_state.coord[1]}")
