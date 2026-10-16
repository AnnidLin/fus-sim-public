# MOC：影像预处理与颅骨建模

> [!note] 主题位置
> 本页只整理影像进入声学模型的稳定知识。虚拟平台实时进度见 [[实验平台阶段看板]]；大鼠 BBB 实验不依赖本页定义自己的动物实验阶段。

## 核心问题

tFUS 仿真不是从声学方程直接开始的。真实经颅问题通常先要把 CT、MRI 或合成影像变成可计算的颅骨声学模型，再进入 [[05_论文与概念/concepts/k-Wave|k-Wave]]、射线追踪、有限元或其他声场求解器。

这张 MOC 用来回答：影像从哪里来、如何分割、怎样配准、怎样映射为声速/密度/衰减，以及 FastSurfer、3D Slicer 这类工具可能处在流程的哪一层。

## 基础概念

- [[05_论文与概念/concepts/DICOM|DICOM]]：医院 CT/MRI 原始影像常见格式。
- [[05_论文与概念/concepts/NIfTI|NIfTI]]：神经影像和许多脑科学工具常用格式。
- [[05_论文与概念/concepts/影像分割|影像分割]]：从影像中提取颅骨、脑组织、靶区或其他结构。
- [[05_论文与概念/concepts/配准|配准]]：把 CT、MRI、换能器坐标和仿真网格对齐。
- [[05_论文与概念/concepts/CT-HU映射|CT-HU 映射]]：把 CT HU 值映射为声学参数。
- [[05_论文与概念/concepts/synthetic CT|synthetic CT]]：从 MRI 等影像生成或估计 CT/骨参数的路线。

## 典型流程

1. 获取 CT、MRI、micro-CT 或公开颅骨数据。
2. 统一影像格式和空间坐标：DICOM/NIfTI、体素尺寸、方向矩阵。
3. 分割颅骨、软组织、靶区或感兴趣结构。
4. 必要时做 CT-MRI 配准或影像到换能器坐标的配准。
5. 将 CT HU、孔隙率或深度学习输出映射为声速、密度、衰减等声学属性。
6. 重采样到声场仿真网格，检查分辨率、PML、边界和物理范围。
7. 输出 acoustic model，再交给 [[MOC_声场仿真与相位校正]]。

## 相关论文

### CT 到声学模型

- [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021]]：CT 层厚、重建核、HU 阈值会影响声学属性和声场输出。
- [[05_论文与概念/notes/16_Chen2023_numerical_and_experimental|Chen 2023]]：人体颅骨 CT 建模与实验声场对比。
- [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026]]：不同颅骨声学建模策略的实验交叉验证。

### 高分辨率骨结构

- [[05_论文与概念/notes/17_Jing2021_effect_of_skull|Jing 2021]]：micro-CT 松质骨结构对经颅传播的影响。
- [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023]]：micro-CT 支持下的相控阵聚焦验证。
- [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025]]：真实 3D 松质骨结构下的相控阵仿真。

### MRI-only / CT-free 路线

- [[05_论文与概念/notes/13_Koh2021_acoustic_simulation_for|Koh 2021]]：MRI 生成 synthetic CT 后做声学仿真。
- [[05_论文与概念/notes/24_Dagommer2024_robust_deep_learning|Dagommer 2024]]：从 MR T1 估计皮质骨孔隙率。
- [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025]]：基于 CT HU 区间和孔隙率指数做声学建模。

## 工具位置

- [[05_论文与概念/concepts/3D Slicer|3D Slicer]]：更接近影像查看、分割、配准和格式转换工具。
- [[05_论文与概念/concepts/FastSurfer|FastSurfer]]：更接近脑 MRI 结构分割工具，是否适合本项目取决于是否进入 MRI/脑结构建模路线。

当前项目主体仍是 CT/颅骨声学建模和声场仿真；FastSurfer 与 3D Slicer 暂时应标为“待了解工具”，不要写成已经用于项目流程。

## 关联入口

- [[MOC_声场仿真与相位校正]]
- [[MOC_参数与指标]]
- [[MOC_AI与深度学习替代模型]]
- [[MOC_研究问题与争议]]
- [[03_experimental_steps]]
- [[06_报告与数据/reports/历史路线/14_历史_本地论文实验步骤与输出复刻规划]]
