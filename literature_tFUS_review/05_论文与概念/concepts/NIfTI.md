# NIfTI

NIfTI 是神经影像和脑科学工具中常见的医学影像格式，常用于 MRI、脑结构分割、功能影像分析和一些 CT/MRI 配准流程。

## 与 DICOM 的区别

DICOM 更像临床影像原始数据包；NIfTI 更像研究和算法处理时常用的三维/四维影像文件。很多工具会先把 DICOM 转成 NIfTI，再做分割、配准或深度学习处理。

## 在本项目中的意义

tFUS 仿真如果只走 CT-HU 声学映射，NIfTI 不是必需概念；但如果后续进入 MRI-only、synthetic CT、脑区定位或 FastSurfer/FreeSurfer 相关路线，NIfTI 会变得重要。

## 关联

- [[05_论文与概念/concepts/DICOM]]
- [[05_论文与概念/concepts/配准]]
- [[05_论文与概念/concepts/FastSurfer]]
- [[05_论文与概念/concepts/synthetic CT]]
- [[MOC_影像预处理与颅骨建模]]
