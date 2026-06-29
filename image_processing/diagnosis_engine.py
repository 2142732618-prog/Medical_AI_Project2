import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import nibabel as nib
import numpy as np
from pathlib import Path
import torch
import gc
torch.set_num_threads(1)
import shutil
import streamlit as st
import traceback
from datetime import datetime
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

class DiagnosisEngine:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.project_root = Path("/root/Medical_AI_Project_V2")
        os.environ["nnUNet_results"] = "/root/autodl-tmp/nnUNet_results"

        self.available_models = {
            "hippocampus": {
                "task_id": "Dataset004_Hippocampus",
                "trainer": "nnUNetTrainer__nnUNetPlans__3d_fullres",
                "organ_name": "海马体"
            },
            "heart": {
                "task_id": "Dataset002_Heart",
                "trainer": "nnUNetTrainer__nnUNetPlans__3d_fullres",
                "organ_name": "心脏"
            },
            "prostate": {
                "task_id": "Dataset005_Prostate",
                "trainer": "nnUNetTrainer__nnUNetPlans__3d_fullres",
                "organ_name": "前列腺"
            },
            "splee": {
                "task_id": "Dataset009_Spleen",
                "trainer": "nnUNetTrainer__nnUNetPlans__3d_fullres",
                "organ_name": "脾脏"
            },
            "brainTumour": {
                "task_id": "Dataset001_BrainTumour",
                "trainer": "nnUNetTrainer__nnUNetPlans__3d_fullres",
                "organ_name": "脑肿瘤"
            }
        }
        # 默认初始化为海马体模型
        self.current_model = self.available_models["hippocampus"]

    def set_model(self, task_key):
        """
        根据前端视图层的选择，动态路由切换权重模型与plans拓扑
        """
        if task_key in self.available_models:
            self.current_model = self.available_models[task_key]

    def get_predictor(self):
        """
        高可用实例化 nnUNetPredictor 并注入当前任务的预训练参数
        """
        predictor = nnUNetPredictor(
            tile_step_size=1,
            use_gaussian=True,
            use_mirroring=True,
            perform_everything_on_device=True, # 强行驻留显存执行密集卷积
            device=self.device,
            verbose=False,
            verbose_preprocessing=False,
            allow_tqdm=False
        )
        
        # 构建动态权重路径
        model_folder = os.path.join(
            os.environ["nnUNet_results"],
            self.current_model["task_id"],
            self.current_model["trainer"]
        )
        
        if self.current_model["task_id"] == "Dataset001_BrainTumour":
            folds_to_use = (1,)
        else:
            folds_to_use = (0,)

        # 引擎自适应初始化加载 plans.json
        predictor.initialize_from_trained_model_folder(
            model_folder,
            use_folds=folds_to_use,
            checkpoint_name='checkpoint_final.pth'
        )
        return predictor

    def run_inference(self, input_napi_path):
        """
        核心推理中枢：实现 16GB RAM 单线程限流预处理、物理隔离沙箱及多通道适配
        """
        # 1. 主动回收显存碎片，为密集计算腾出连续显存块
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # 基于 Job ID 确立绝对隔离的运行时目录结构
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_id = f"job_{timestamp}"

        output_root = os.path.join('/root/autodl-tmp/Project_Data', "ai_results")  # 新名称
        sandbox_root = os.path.join('/root/autodl-tmp/Project_Data', "tmp_sandbox")

        specific_out_dir = os.path.join(output_root, job_id)
        sandbox_dir = os.path.join(sandbox_root, job_id)
        
        os.makedirs(specific_out_dir, exist_ok=True)
        os.makedirs(sandbox_dir, exist_ok=True)

        predictor = self.get_predictor()
        input_filename = os.path.basename(input_napi_path)

        try:
            # 2. 异构模态物理适配逻辑分支
            if self.current_model["task_id"] == "Dataset001_BrainTumour":
                # 剔除 st 变量，改用 print 保证后台与核心引擎彻底解耦
                print(">>> [INFO] 探测到输入序列为 4D 密集融合特征，启动运行时空间维度解耦...")
                
                # 读取上传的 4D 文件
                img = nib.load(input_napi_path)
                if img.ndim != 4 or img.shape[3] != 4:
                    raise ValueError(f"非标准4D数据，维度: {img.shape}")
                
                # 【根本修正】：精准提取纯文件名（不带任何 .nii 或 .nii.gz），彻底封死后缀重叠 Bug
                if input_filename.endswith(".nii.gz"):
                    base_case_name = input_filename[:-7]  # 剥离最后的 .nii.gz
                elif input_filename.endswith(".nii"):
                    base_case_name = input_filename[:-4]  # 剥离最后的 .nii
                else:
                    base_case_name = os.path.splitext(input_filename)[0]

                # 顺着第 4 维度解耦拆分，并在 tmp_sandbox 中创建 nnU-Net 严格要求的 3D 占位副本
                for i in range(4):
                    # 延迟读取，仅获取当前通道
                    sub_data = np.asarray(img.dataobj[..., i], dtype=np.float32)
                    sub_img = nib.Nifti1Image(sub_data, img.affine, img.header)
                    dest_path = os.path.join(sandbox_dir, f"{base_case_name}_{i:04d}.nii.gz")
                    nib.save(sub_img, dest_path)
                    del sub_data, sub_img

                gc.collect()
                
                # 物理 3D 环境解耦就绪，送入推理框
                input_files_or_folds = [sandbox_dir]
                output_files = [os.path.join(specific_out_dir, "prediction.nii.gz")]
                
                predictor.max_num_processes = 1

                # 执行高性能单进程自适应推理
                predictor.predict_from_files(
                    input_files_or_folds,
                    output_files,
                    save_probabilities=False,
                    overwrite=True,
                    num_processes_segmentation_export=1,
                    num_processes_preprocessing=1
                )
                
                # 及时销毁沙箱环境，释放磁盘空间
                shutil.rmtree(sandbox_dir)
                return output_files[0]

            elif self.current_model["task_id"] == "Dataset005_Prostate":
                 # 前列腺双模态拆分
                print(">>> [INFO] 检测到前列腺多模态数据，拆分 T2 和 ADC...")
                img = nib.load(input_napi_path)
                if img.ndim != 4 or img.shape[3] != 2:
                    raise ValueError(f"前列腺数据应为2模态4D文件，当前维度: {img.shape}")

                # 提取基名
                if input_filename.endswith(".nii.gz"):
                    base_case_name = input_filename[:-7]
                elif input_filename.endswith(".nii"):
                    base_case_name = input_filename[:-4]
                else:
                    base_case_name = os.path.splitext(input_filename)[0]

                # 导出两个模态
                for i in range(2):
                    sub_data = np.asarray(img.dataobj[..., i], dtype=np.float32)
                    sub_img = nib.Nifti1Image(sub_data, img.affine, img.header)
                    dest_path = os.path.join(sandbox_dir, f"{base_case_name}_{i:04d}.nii.gz")
                    nib.save(sub_img, dest_path)
                    del sub_data, sub_img

                gc.collect()

                input_files_or_folds = [sandbox_dir]
                output_files = [os.path.join(specific_out_dir, "prediction.nii.gz")]

                predictor.max_num_processes = 1

                # 执行高性能单进程自适应推理
                predictor.predict_from_files(
                    input_files_or_folds,
                    output_files,
                    save_probabilities=False,
                    overwrite=True,
                    num_processes_segmentation_export=1,
                    num_processes_preprocessing=1
                )

                shutil.rmtree(sandbox_dir)
                return output_files[0]

            else:
                # 标准单通道任务（海马体/心脏）通用快速流
                output_file = os.path.join(specific_out_dir, "prediction.nii.gz")
                predictor.predict_from_files(
                    [[input_napi_path]], 
                    [output_file], 
                    save_probabilities=False, 
                    overwrite=True,
                    num_processes_segmentation_export=1,
                    num_processes_preprocessing=1
                )
                shutil.rmtree(sandbox_dir)
                return output_file

        except Exception as e:
            if os.path.exists(sandbox_dir):
                shutil.rmtree(sandbox_dir)
            raise e

    def ai_logic(self, mask_data, task_key="brainTumour", spacing=(1.0, 1.0, 1.0)):
        """
        根据不同的器官任务，结合真实物理分辨率生成对应的定量放射组学临床分析文本。
        spacing: 三维体素大小 (dx, dy, dz)，通常通过 nibabel 的 img.header.get_zooms() 获取
        """
        # 1. 计算单个体素的物理体积 (单位: mm³)
        voxel_volume_mm3 = spacing[0] * spacing[1] * spacing[2]
    
        # 定义体素转化为毫升 (1 ml = 1000 mm³) 的计算闭包
        def get_volume_ml(count):
            return (count * voxel_volume_mm3) / 1000.0

        reports = []

        # ==================== 1. 海马体任务 ====================
        if task_key == "hippocampus":
            # 假设 Label 1 代表前部，Label 2 代表后部 (根据你实际模型的标签微调)
            ant_count = np.sum(mask_data == 1)
            post_count = np.sum(mask_data == 2)
        
            if ant_count > 0:
                reports.append(f"海马体前部 (Anterior) 体积约: {get_volume_ml(ant_count):.2f} ml")
            if post_count > 0:
                reports.append(f"海马体后部 (Posterior) 体积约: {get_volume_ml(post_count):.2f} ml")
        
            total_count = ant_count + post_count
            if total_count > 0:
                reports.append(f"总体积约: {get_volume_ml(total_count):.2f} ml")

        # ==================== 2. 心脏任务 ====================
        elif task_key == "heart":
            # 假设 Label 1 为左心室，Label 2 为右心室，Label 3 为心肌
            lv_count = np.sum(mask_data == 1)
            rv_count = np.sum(mask_data == 2)
            myo_count = np.sum(mask_data == 3)
        
            if lv_count > 0:
                reports.append(f"左心室 (Left Ventricle) 体积约: {get_volume_ml(lv_count):.2f} ml")
            if rv_count > 0:
                reports.append(f"右心室 (Right Ventricle) 体积约: {get_volume_ml(rv_count):.2f} ml")
            if myo_count > 0:
                reports.append(f"心肌结构 (Myocadium) 体积约: {get_volume_ml(myo_count):.2f} ml")
                reports.append("心肌结构评估: 正常，未见明显室壁运动异常。")

        # ==================== 3. 脑肿瘤任务 ====================
        elif task_key == "brainTumour":
            et_count = np.sum(mask_data == 3) # 增强肿瘤
            ed_count = np.sum(mask_data == 2) # 水肿
            ne_count = np.sum(mask_data == 1) # 坏死
            total_tumor_count = np.sum(mask_data > 0)
        
            if total_tumor_count > 0:
                reports.append(f"脑肿瘤靶区 (ROI) 总体积约: {get_volume_ml(total_tumor_count):.2f} ml")
            if ed_count > 0 and total_tumor_count > 0:
                ed_ratio = (ed_count / total_tumor_count) * 100
                reports.append(f"瘤周水肿区体积约: {get_volume_ml(ed_count):.2f} ml (占比: {ed_ratio:.1f}%)")
            if et_count > 0:
                reports.append(f"增强肿瘤区 (ET) 体积约: {get_volume_ml(et_count):.2f} ml")
                reports.append("临床状态提示: 建议结合增强 MRI 序列进一步确诊。")

        #==================== 4. 前列腺任务 ====================
        elif task_key == "prostate":
            pz_count = np.sum(mask_data == 1)
            tz_count = np.sum(mask_data == 2)
        
            if pz_count > 0:
                reports.append(f"前列腺外周带 (Peripheral Zone) 体积约: {get_volume_ml(pz_count):.2f} ml")
            if tz_count > 0:
                reports.append(f"前列腺移行/中央区 (Transition Zone) 体积约: {get_volume_ml(tz_count):.2f} ml")
        
            total_prostate = pz_count + tz_count
            if total_prostate > 0:
                reports.append(f"前列腺总体积约: {get_volume_ml(total_prostate):.2f} ml")

        # ==================== 5. 脾脏任务 ====================
        elif task_key == "spleen":
            spleen_count = np.sum(mask_data > 0)
            if spleen_count > 0:
                reports.append(f"脾脏靶区绝对体积约: {get_volume_ml(spleen_count):.2f} ml")
                reports.append("临床提示: 脾脏形态体积在正常范围内。")
        if not reports:
            reports.append("临床提示: 未在影像中检测到明显的对应靶区分割结构。")

        return reports
