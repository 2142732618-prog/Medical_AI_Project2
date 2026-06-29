import pydicom
import numpy as np
import logging
import streamlit as st

class DicomReader:

    @staticmethod
    def load_dicom_series(uploaded_files):
        """
        加载并解析 DICOM 序列。
        """
        if not uploaded_files:
            return None, None, {"Error": "未上传文件"}

        try:
            # 1. 从上传对象中读取 Dataset
            datasets = []
            for file in uploaded_files:
                try:
                    ds = pydicom.dcmread(file)
                    if hasattr(ds, 'pixel_array'):
                        datasets.append(ds)
                except Exception as e:
                    continue

            if not datasets:
                return None, None, {"Error": "无可读 DICOM 图像"}

            # 2. 物理坐标 Z 轴排序 (保证 3D 空间连续性)
            # 逻辑参考自 DicomParser._sort_dicom_slices
            try:
                if all(hasattr(ds, 'ImagePositionPatient') for ds in datasets):
                    datasets.sort(key=lambda x: float(x.ImagePositionPatient[2]))
                else:
                    datasets.sort(key=lambda x: int(getattr(x, 'InstanceNumber', 0)))
            except Exception:
                datasets.sort(key=lambda x: 0)

            # 3. 提取像素数据并应用 Rescale Slope/Intercept (校准为 HU 值)
            # 逻辑参考自 DicomParser._extract_pixel_data
            pixel_arrays = []
            for ds in datasets:
                pixel_array = ds.pixel_array.astype(np.float32)
                slope = float(getattr(ds, 'RescaleSlope', 1.0))
                intercept = float(getattr(ds, 'RescaleIntercept', 0.0))
                pixel_array = pixel_array * slope + intercept
                pixel_arrays.append(pixel_array)

            volume = np.stack(pixel_arrays, axis=0)

            # 4. 提取元数据与窗值预设
            # 逻辑参考自 DicomParser.get_window_center_width
            first_ds = datasets[0]
            center = getattr(first_ds, 'WindowCenter', 40.0)
            width = getattr(first_ds, 'WindowWidth', 400.0)

            # 处理多重预设（取第一个值）
            if isinstance(center, pydicom.multival.MultiValue): center = center[0]
            if isinstance(width, pydicom.multival.MultiValue): width = width[0]

            meta = {
                "患者姓名": str(getattr(first_ds, "PatientName", "Anonymous")),
                "检查模态": str(getattr(first_ds, "Modality", "CT")),
                "默认窗位": float(center),
                "默认窗宽": float(width),
                "切片层数": len(datasets),
                "数值范围": f"{int(np.min(volume))} ~ {int(np.max(volume))} HU"
            }

            # 物理间距
            spacing = (float(getattr(first_ds, 'SliceThickness', 1.0)),
                       float(first_ds.PixelSpacing[0]),
                       float(first_ds.PixelSpacing[1]))

            return volume, spacing, meta

        except Exception as e:
            return None, None, {"Error": f"解析失败: {str(e)}"}

    @staticmethod
    def load_single_dicom(file_obj):
        """加载单张 DICOM 文件（包含强制读取逻辑）"""
        try:
            # 添加 force=True 以处理缺少文件头的文件
            ds = pydicom.dcmread(file_obj, force=True)

            # 兼容性检查：有些非标文件可能缺少像素数据属性
            if not hasattr(ds, 'pixel_array'):
                # 尝试再次同步传输语法
                ds.file_meta = pydicom.dataset.FileMetaDataset()
                ds.is_implicit_VR = True
                ds.is_little_endian = True

            pixel_array = ds.pixel_array.astype(float)

            # 执行 HU 值校准
            rescale_intercept = getattr(ds, 'RescaleIntercept', 0)
            rescale_slope = getattr(ds, 'RescaleSlope', 1)
            hu_array = pixel_array * rescale_slope + rescale_intercept

            meta = {
                "FileName": getattr(file_obj, 'name', 'Unknown'),
                "PatientName": str(getattr(ds, 'PatientName', 'N/A')),
                "InstanceNumber": int(getattr(ds, 'InstanceNumber', 0))
            }
            return hu_array, None, meta
        except Exception as e:
            st.error(f"单张强制加载仍然失败: {e}")
            return None, None, None