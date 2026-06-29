import nibabel as nib
import numpy as np
from skimage import measure  # 处理 Marching Cubes
import trimesh               # 处理 3D 网格导出
import os

class Reconstructor:
    def __init__(self):
        """初始化 3D 重建引擎"""
        pass

    def nifti_to_glb(self, nifti_path, glb_output_path, reduction_ratio=0.1):
        """
        将 NIfTI 掩码转换为轻量化 GLB 文件
        nifti_path: AI 生成的 .nii.gz 路径
        glb_output_path: 目标 .glb 输出路径
        reduction_ratio: 减面比例（0.1 表示保留 10% 的面数）
        """
        try:
            # 1. 加载 NIfTI 掩码
            img = nib.load(nifti_path)
            data = img.get_fdata()
            affine = img.affine  # 关键：获取物理空间坐标变换矩阵

            # 2. 空数据检查
            if np.max(data) == 0:
                print(f"⚠️ 跳过：{nifti_path} 没有分割结果")
                return False

            # 3. Marching Cubes 提取表面网格
            # level=0.5 是二值化分割的标准阈值
            verts, faces, normals, values = measure.marching_cubes(data, level=0.5)

            # 4. 坐标变换
            verts_homogeneous = np.c_[verts, np.ones(len(verts))]
            verts_phys = (verts_homogeneous @ affine.T)[:, :3]

            # 5. 构建 trimesh 对象
            mesh = trimesh.Trimesh(vertices=verts_phys, faces=faces)
            
            # --- 6. 自动化轻量化方案 ---
            try:
                target_faces = int(len(faces) * reduction_ratio)
                if target_faces > 100:
                    # 尝试执行二次误差度量简化（Decimation）
                    # 提示：如果环境缺少 pyrender 或 openctm 可能触发报错
                    mesh = mesh.simplify_quadratic_decimation(target_faces)
            except Exception as e:
                # 容错处理：即使简化失败，也不影响模型生成
                print(f"💡 自动降级：跳过网格简化逻辑 (原因: {e})")
                pass

            # 7. 确保导出目录存在并写入文件
            os.makedirs(os.path.dirname(glb_output_path), exist_ok=True)
            mesh.export(glb_output_path)
            
            print(f"✅ 3D 模型转换完成: {glb_output_path}")
            return True

        except Exception as e:
            print(f"❌ 3D 重建失败: {e}")
            return False

# 保持与原有逻辑兼容，提供一个快捷调用接口
def nifti_to_glb(nifti_path, glb_output_path, reduction_ratio=0.1):
    return Reconstructor().nifti_to_glb(nifti_path, glb_output_path, reduction_ratio)

if __name__ == "__main__":
    # 测试用例
    # recon = Reconstructor()
    # recon.nifti_to_glb("test.nii.gz", "test.glb")
    pass