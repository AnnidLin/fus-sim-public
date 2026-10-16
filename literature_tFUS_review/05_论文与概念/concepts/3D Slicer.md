# 3D Slicer

3D Slicer 是医学影像查看、处理、分割和配准平台。它常用于打开 DICOM/NIfTI、查看三维结构、做手动或半自动分割、导出 mask 或模型。

## 在本项目中的位置

当前 `fus-sim` 项目里，3D Slicer 只在公开 CT 数据来源筛选中边缘出现过，还没有进入正式影像处理或仿真流程。

如果后续要处理真实 CT/MRI，3D Slicer 可能用于：

- 查看 [[05_论文与概念/concepts/DICOM|DICOM]] 或 [[05_论文与概念/concepts/NIfTI|NIfTI]]
- 检查 CT 方向、层厚和体素尺寸
- 做颅骨或靶区 [[05_论文与概念/concepts/影像分割|分割]]
- 做初步 [[05_论文与概念/concepts/配准|配准]]
- 导出 mask、surface model 或重采样影像

## 注意

3D Slicer 是影像预处理工具，不是声场求解器。它能帮助生成或检查仿真输入，但不能替代 [[05_论文与概念/concepts/k-Wave|k-Wave]]、有限元或其他声学传播模型。

## 关联

- [[05_论文与概念/concepts/DICOM]]
- [[05_论文与概念/concepts/NIfTI]]
- [[05_论文与概念/concepts/影像分割]]
- [[05_论文与概念/concepts/配准]]
- [[MOC_影像预处理与颅骨建模]]
