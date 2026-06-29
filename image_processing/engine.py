import streamlit as st
import os
import torch
import nibabel as nib
import numpy as np
import trimesh
import skimage.measure as measure
from image_processing.processor import MedicalProcessor
from image_processing.reconstructor import Reconstructor

class InferenceEngine:
    def __init__(self):
        """
        初始化 AI 调度引擎，增加硬件自适应逻辑
        """
        if "medical_processor" not in st.session_state:
            st.session_state.medical_processor = MedicalProcessor()
        if "reconstructor" not in st.session_state:
            st.session_state.reconstructor = Reconstructor()
            
        self.proc = st.session_state.medical_processor
        self.recon = st.session_state.reconstructor
        
        # --- 硬件探测与自适应优化 ---
        self.device_info = self._get_gpu_spec()

    def _get_gpu_spec(self):
        """探测 GPU 规格"""
        if not torch.cuda.is_available():
            return {"name": "CPU", "vram": 0, "is_blackwell": False}
        
        prop = torch.cuda.get_device_properties(0)
        vram_gb = prop.total_memory / 1024**3
        is_blackwell = "5090" in prop.name or prop.major >= 10
        
        return {
            "name": prop.name,
            "vram": vram_gb,
            "is_blackwell": is_blackwell,
            # 5090开启高性能模式，4090 保持标准模式
            "batch_size": 4 if vram_gb > 30 else 2 
        }

    def load_volume(self, path):
        """使用内存映射和半精度，防止 Killed 报错"""
        import SimpleITK as sitk
        try:
            if not os.path.exists(path): return None, None
            
            # --- 处理 DICOM ZIP ---
            if path.endswith('.zip'):
                dicom_dir = self.proc.unzip_and_find_dicom(path)
                if dicom_dir:
                    reader = sitk.ImageSeriesReader()
                    names = reader.GetGDCMSeriesFileNames(dicom_dir)
                    reader.SetFileNames(names)
                    itk_img = reader.Execute()
                    spacing = itk_img.GetSpacing()
                    #转为 float16 减少一半内存占用
                    volume = sitk.GetArrayFromImage(itk_img).astype('float16')
                    return volume, spacing
            
            # --- 处理 NIfTI ---
            if path.endswith(('.nii', '.nii.gz')):
                img = nib.load(path)
                spacing = img.header.get_zooms()[:3]
                # 使用 mmap='r' 模式：数据留在硬盘上，只有读取切片时才进内存
                data = img.get_fdata(dtype=np.float32, caching='fill')
                # 再次转换为 float16 降低后续渲染压力
                return data, spacing
                
            return None, None
        except Exception as e:
            print(f"❌ 影像解析失败: {e}")
            return None, None

    def run_full_pipeline(self, zip_path, case_name, output_root):
        """
        流程：解压 -> 分割 -> 导出 NIfTI -> 3D 重建
        """
        try:
            # 1. 解压并定位 DICOM
            dicom_dir = self.proc.unzip_and_find_dicom(zip_path)
            if not dicom_dir:
                return False, "❌ 找不到有效的 DICOM 序列", None

            # 2. 执行推理
            with torch.amp.autocast(device_type='cuda', enabled=self.device_info["is_blackwell"]):
                mask_path = self.proc.process_case(dicom_dir, case_name)
            
            if not mask_path or not os.path.exists(mask_path):
                return False, "❌ AI 推理未生成有效的掩膜文件", None

            # 3. 路径定位
            case_work_dir = os.path.dirname(mask_path)
            # 确保 processor 把原始影像存为 {case_name}_raw.nii.gz
            raw_nii_path = os.path.join(case_work_dir, f"{case_name}_raw.nii.gz")
            glb_path = os.path.join(case_work_dir, f"{case_name}.glb")
            
            # 4. 执行 3D 重建
            success_3d = self.recon.nifti_to_glb(mask_path, glb_path)
            
            # 5. 清理临时解压缓存
            self.proc.cleanup(case_name)

            if success_3d:
                return True, "✅ 重建完成", {
                    "mask": mask_path,
                    "raw": raw_nii_path if os.path.exists(raw_nii_path) else mask_path,
                    "glb": glb_path,
                    "dir": case_work_dir,
                    "gpu": self.device_info["name"]
                }
            else:
                return False, "⚠️ 分割成功但 3D 重建失败", {"mask": mask_path}

        except Exception as e:
            return False, f"❌ 引擎执行崩溃: {str(e)}", None

def get_engine():
    """获取单例引擎"""
    return InferenceEngine()

def export_auto_colored_glb(mask_data, spacing, save_path):

        dz, dy, dx = spacing[:3] 
        actual_spacing = (dz, dy, dx)

        int_mask = np.round(mask_data).astype(np.uint8)


        # 预定义一个高对比度的颜色调色板 (RGBA)
        # 如果器官超过 8 个，会自动循环使用
        label_color_map = {
            1:  {"name": "脾脏 (Spleen)", "color": [153, 102, 255, 255]},
            2:  {"name": "左肾 (Kidney_L)", "color": [75, 192, 192, 255]},
            3:  {"name": "右肾 (Kidney_R)", "color": [54, 162, 235, 255]},
            5:  {"name": "肝脏 (Liver)", "color": [255, 99, 132, 255]},
            17: {"name": "骨骼 (Skeleton)", "color": [240, 240, 240, 255]},
            6:  {"name": "主动脉 (Aorta)", "color": [255, 205, 86, 255]}
        }
        palette = [
            [255, 206, 86, 255], [255, 159, 64, 255], [46, 204, 113, 255]
        ]

        scene = trimesh.Scene()
        labels = np.unique(mask_data)
        labels = labels[labels != 0]
        volume_stats = {}# 用于存储体积数据
        # 遍历每个器官独立建模
        for i, label in enumerate(labels):
            # 1. 提取当前器官的二值掩码并统计
            binary_mask = (mask_data == label).astype(np.uint8)
            voxel_count = np.sum(binary_mask)
        
            # 2. 过滤掉像素太少的无效区域 (防止生成空网格报错)
            if voxel_count < 20: 
                continue

            # 3. 计算体积 (ml)
            organ_volume = (voxel_count * dx * dy * dz) / 1000.0

            try:
                # 4. 生成网格
                verts, faces, normals, _ = measure.marching_cubes(
                    binary_mask, level=0.5, spacing=actual_spacing
                )
            
                # 5. 创建 Mesh
                mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)
            
                # 6. 平滑处理
                mesh = mesh.filter_laplacian(iterations=10)
            
                # 7. 颜色注入修正
                info = label_color_map.get(int(label), {"name": f"Organ_{label}", "color": palette[i % len(palette)]})
                raw_color = info["color"] # 这里的格式是 [R, G, B, A]
            
                # 关键：创建一个和面数一样多的颜色矩阵
                # Trimesh 在导出 GLB 时，显式地给每个面指定颜色是最稳定的
                face_colors = np.tile(raw_color, (len(mesh.faces), 1)).astype(np.uint8)
                mesh.visual.face_colors = face_colors
            
                # 8. 记录统计并加入场景
                volume_stats[info["name"]] = f"{organ_volume:.2f} ml"
                scene.add_geometry(mesh, node_name=f"Organ_{label}")
            
            except Exception as e:
                print(f"器官 {label} ({info.get('name', 'Unknown')}) 建模失败: {e}")
                continue

        if not scene.is_empty:
            scene.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
            scene.export(save_path)
            return volume_stats
        else:
            print("❌ 场景为空，未生成任何模型")