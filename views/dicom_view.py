import streamlit as st
import os
import numpy as np
import gc 
from PIL import Image
from streamlit_vertical_slider import vertical_slider
import config
from image_processing.engine import get_engine
from utils.ui_utils import dicom_view_style

def get_data_list(path):
    if not os.path.exists(path): return []
    return sorted([f for f in os.listdir(path) if not f.startswith('.')])

@st.cache_data(show_spinner=False, max_entries=300)
def apply_windowing(img_array, window_width, window_level):
    """
    使用缓存避免重复计算。输入转为 float16,减小内存压力。
    """
    lower = window_level - (window_width / 2)
    upper = window_level + (window_width / 2)
    img_weighted = np.clip(img_array, lower, upper)
    img_normalized = (img_weighted - lower) / (upper - lower + 1e-5) * 255
    return img_normalized.astype('uint8')

def show_dicom_page(theme="Dark"):
    dicom_view_style(theme)
    engine = get_engine()
    
    username = st.session_state.get("username", "admin")
    paths = config.get_user_paths(username)

    if "info_expanded" not in st.session_state: st.session_state.info_expanded = True
    if "coord" not in st.session_state: st.session_state.coord = [0, 0, 0]

    # --- 1. 顶部控制栏---
    t_col = st.columns([1, 2, 2, 4, 1, 1])
    
    with t_col[0]:
        if st.button("返回", use_container_width=True):
            st.session_state["step"] = "MENU"
            st.rerun()
            
    with t_col[1]:
        raw_list = get_data_list(paths["raw"])
        selected_file = st.selectbox("selected_file", ["选择影像序列..."] + raw_list, key="top_file", label_visibility="collapsed")
        
    with t_col[2]:
        presets = {
            "自定义": (2000, -1000, (0, 2000), (-1000,500)),
            "软组织": (400, 40, (300, 500), (30, 80)),
            "肺窗": (1500, -600, (1000, 2000), (-600, 400)),
            "骨窗": (2000, 500, (2000, 4000), (200, 600)),
            "脑窗": (80, 40, (70, 100), (30, 50))
        }
        selected_mode = st.selectbox("selected_mode", list(presets.keys()), key="top_mode", label_visibility="collapsed")
        # 预设改变时，重置滑块
        if st.session_state.get("last_mode") != selected_mode:
            target_ww, target_wl, ww_range, wl_range = presets[selected_mode]
            st.session_state["ww_slider"] = target_ww
            st.session_state["wl_slider"] = target_wl
            st.session_state["ww_min"], st.session_state["ww_max"] = ww_range
            st.session_state["wl_min"], st.session_state["wl_max"] = wl_range
            st.session_state["last_mode"] = selected_mode # 记录状态
            st.rerun()

    with t_col[3]:
        wc1, wc2 = st.columns(2)
        ww = wc1.slider("ww_label", 
                        min_value=st.session_state.get("ww_min", 1), 
                        max_value=st.session_state.get("ww_max", 2500), 
                        key="ww_slider",
                        label_visibility="collapsed"
                        )
        wl = wc2.slider("wl_label", 
                        min_value=st.session_state.get("wl_min", -1000), 
                        max_value=st.session_state.get("wl_max", 1000), 
                        key="wl_slider",
                        label_visibility="collapsed"
                        )

    with t_col[4]:
        icon = "✖️" if st.session_state.info_expanded else "详情信息"
        if st.button(icon, use_container_width=True):
            st.session_state.info_expanded = not st.session_state.info_expanded
            st.rerun()

    with t_col[5]:
        if st.button("清除缓存", use_container_width=True, type="secondary"):
            keys_to_reset = ["v_data", "show_case_name", "v_package", "top_file", "dz_v", "dx_v", "dy_v"]
            for key in keys_to_reset:
                if key in st.session_state: del st.session_state[key]
            gc.collect() 
            st.rerun()

    # --- 2. 数据载入 ---
    if selected_file != "选择影像序列...":
        case_id = f"dicom_{selected_file}"
        if st.session_state.get("show_case_name") != case_id:
            if "v_data" in st.session_state:
                del st.session_state.v_data
                gc.collect()

            zip_path = os.path.join(paths["raw"], selected_file)
            data_pack = engine.load_volume(zip_path) 
            if data_pack is not None:
                st.session_state.v_data = data_pack 
                st.session_state.show_case_name = case_id
                vol_temp = data_pack[0]
                st.session_state.coord = [vol_temp.shape[0]//2, vol_temp.shape[1]//2, vol_temp.shape[2]//2]
                st.rerun()

    # --- 3. 视图渲染 ---
    # --- 3. 视图渲染 ---
    v_package = st.session_state.get("v_data")
    if v_package is None:
        st.markdown('<div style="background:#25282C; border:1px dashed #444; padding:40px; border-radius:12px; text-align:center; margin-top:20vh;">'
                    '<h3>DICOM序列阅读</h3><p style="color:#888;">请在上方工具栏加载序列</p></div>', unsafe_allow_html=True)
        st.stop()

    # 数据解析
    vol, spacing = v_package[0], v_package[1]
    meta = v_package[2] if len(v_package) > 2 else {"name": "ANONYMOUS", "id": "P-2026", "sex": "U", "age": "N/A"}
    dx, dy, dz = spacing[:3]
    
    is_exp = st.session_state.info_expanded
    main_col, info_col = st.columns([8.2, 1.8] if is_exp else [9.8, 0.2])

    with main_col:
        v_col1, v_col2, v_col3 = st.columns(3)
        img_kwargs = {"use_container_width": True, "output_format": "JPEG"}

        # Axial (Z) - 横断面
        with v_col1:
            sl, im = st.columns([1, 10])
            with sl:
                # 强制转为 int 防止 ValueError
                z_idx = int(st.session_state.coord[0])
                st.session_state.coord[0] = vertical_slider(
                    label="Z", min_value=0, max_value=vol.shape[0]-1,
                    default_value=z_idx, key="dz_v", height=230, thumb_color="#00D4FF"
                )
            with im:
                slice_a = apply_windowing(vol[st.session_state.coord[0], :, :], ww, wl)
                # 仅执行垂直翻转，解决上下颠倒
                st.image(slice_a[::-1, :], **img_kwargs, caption=f"Axial: {st.session_state.coord[0]}")

        # Sagittal (X) - 侧切面
        with v_col2:
            sl, im = st.columns([1, 10])
            with sl:
                x_idx = int(st.session_state.coord[2])
                st.session_state.coord[2] = vertical_slider(
                    label="X", min_value=0, max_value=vol.shape[2]-1,
                    default_value=x_idx, key="dx_v", height=230
                )
            with im:
                slice_s = apply_windowing(vol[:, :, st.session_state.coord[2]], ww, wl)
                # 侧切面：先垂直翻转，再根据 dz/dy 缩放比例
                pil_s = Image.fromarray(slice_s[::-1, :])
                new_h = int(pil_s.size[1] * (dz / dy))
                st.image(pil_s.resize((pil_s.size[0], new_h), Image.NEAREST), **img_kwargs, caption=f"Sagittal: {st.session_state.coord[2]}")

        # Coronal (Y) - 冠状面
        with v_col3:
            sl, im = st.columns([1, 10])
            with sl:
                y_idx = int(st.session_state.coord[1])
                st.session_state.coord[1] = vertical_slider(
                    label="Y", min_value=0, max_value=vol.shape[1]-1,
                    default_value=y_idx, key="dy_v", height=230
                )
            with im:
                slice_c = apply_windowing(vol[:, st.session_state.coord[1], :], ww, wl)
                # 冠状面：仅垂直翻转 + 比例缩放[cite: 5]
                pil_c = Image.fromarray(slice_c[::-1, :])
                new_h = int(pil_c.size[1] * (dz / dx))
                st.image(pil_c.resize((pil_c.size[0], new_h), Image.NEAREST), **img_kwargs, caption=f"Coronal: {st.session_state.coord[1]}")

    with info_col:
        if is_exp:
            st.markdown(f"""
            <div style="background:#25282C; padding:15px; border-radius:10px; border:1px solid #333;">
                <p style="color:#888; font-size:12px;">PATIENT INFO</p>
                <b>{meta.get('name')}</b><br>
                <small>ID: {meta.get('id')}</small><br>
                <small>{meta.get('sex')}/{meta.get('age')}</small>
                <hr style="margin:10px 0; border-color:#444;">
                <p style="color:#888; font-size:12px;">DIMENSIONS</p>
                <small style="color:#00D4FF;">{vol.shape}</small>
            </div>
            """, unsafe_allow_html=True)