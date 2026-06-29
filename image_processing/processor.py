import os
import zipfile
import shutil
import time
from pathlib import Path
import gc
import torch
import SimpleITK as sitk
import numpy as np

# 导入自定义配置
import config

# --- 环境补丁---
os.environ["TORCH_CUDA_ARCH_LIST"] = "9.0"
os.environ["nnUNet_n_proc_final_preprocess"] = "1"

# 安全导入 TotalSegmentator
try:
    from totalsegmentator.python_api import totalsegmentator
    TS_AVAILABLE = True
except ImportError:
    TS_AVAILABLE = False
    totalsegmentator = None

class MedicalProcessor:
    def __init__(self):
        """
        初始化处理器，加载全局配置
        """
        self.work_dir = config.DATA_ROOT
        self.output_root = os.path.join(config.DATA_ROOT, "admin", "output")
        
        # 确保基础目录存在
        os.makedirs(self.work_dir, exist_ok=True)
        os.makedirs(self.output_root, exist_ok=True)

    def unzip_and_find_dicom(self, zip_path):
        """
        解压 ZIP 压缩包并定位 DICOM 目录
        """
        case_id = Path(zip_path).stem
        extract_to = os.path.join(self.work_dir, "temp_extract", case_id)
        
        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)
        os.makedirs(extract_to, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            
            # 自动递归查找包含 .dcm 的文件夹
            for root, dirs, files in os.walk(extract_to):
                if any(f.lower().endswith('.dcm') for f in files):
                    print(f"✅ 找到 DICOM 序列目录: {root}")
                    return root
            return None
        except Exception as e:
            print(f"❌ 解压缩或查找失败: {e}")
            return None

    def dicom_to_nifti(self, dicom_dir, nifti_save_path):
        """
        几何校正：将 DICOM 序列转换为单个 NIfTI 文件
        """
        try:
            reader = sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
            reader.SetFileNames(dicom_names)
            image = reader.Execute()
            sitk.WriteImage(image, nifti_save_path)
            
            # 显式释放内存，防止大体积 CT 撑爆内存
            del image
            gc.collect()
            return True
        except Exception as e:
            print(f"❌ 几何校正失败: {e}")
            return False

    def process_case(self, dicom_dir, case_name, task="total"):
        """
        核心 AI 推理流水线：几何校正 -> AI 推理 -> 结果合并
        """
        # 1. 准备输出目录
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        case_output_dir = os.path.join(self.output_root, f"{case_name}_{timestamp}")
        os.makedirs(case_output_dir, exist_ok=True)
        
        # 2. 转换 NIfTI
        nifti_path = os.path.join(case_output_dir, f"{case_name}_raw.nii.gz")
        if not self.dicom_to_nifti(dicom_dir, nifti_path):
            return None

        # 3. 运行 TotalSegmentator
        mask_final_path = os.path.join(case_output_dir, f"{case_name}_mask.nii.gz")
        
        if not TS_AVAILABLE:
            print("❌ TotalSegmentator 未安装")
            return None

        try:
            # 释放显存碎片
            torch.cuda.empty_cache()
            
            # 调用 API
            # fast=True 保证在 4090 上能够实现秒级推理
            totalsegmentator(nifti_path, case_output_dir, task=task, fast=True, ml=False, verbose=False)
            
            # 4. 碎片合并逻辑
            return self._merge_mask_fragments(case_output_dir, case_name, mask_final_path)

        except Exception as e:
            print(f"❌ AI 推理异常: {e}")
            return None

    def _merge_mask_fragments(self, output_dir, case_name, final_path):
        """
        内部方法：扫描目录下的所有器官掩膜并合体
        """
        all_masks = []
        for root, _, files in os.walk(output_dir):
            for f in files:
                # 排除原始文件和已存在的合并文件
                if f.endswith(".nii.gz") and "_raw" not in f and "_mask" not in f:
                    all_masks.append(os.path.join(root, f))

        if not all_masks:
            print("⚠️ 未找到生成的掩膜文件")
            return None

        print(f"🧬 正在合并 {len(all_masks)} 个器官模型...")
        try:
            first_mask = sitk.ReadImage(all_masks[0])
            combined_arr = sitk.GetArrayFromImage(first_mask)
            
            for i in range(1, len(all_masks)):
                sub_mask = sitk.ReadImage(all_masks[i])
                combined_arr = np.maximum(combined_arr, sitk.GetArrayFromImage(sub_mask))
            
            final_img = sitk.GetImageFromArray(combined_arr)
            final_img.CopyInformation(first_mask)
            sitk.WriteImage(final_img, final_path)
            
            print(f"✅ 合并完成: {final_path}")
            return final_path
        except Exception as e:
            print(f"❌ 合并阶段报错: {e}")
            return None

    def cleanup(self, case_name):
        """清理缓存"""
        temp_dir = os.path.join(self.work_dir, "temp_extract", case_name)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)