# Treeby & Cox 2010 - [[05_论文与概念/concepts/k-Wave|k-Wave]] toolbox

## 基本信息

- 题名：[[05_论文与概念/concepts/k-Wave|k-Wave]]: MATLAB toolbox for the simulation and reconstruction of photoacoustic wave fields
- 期刊：Journal of Biomedical Optics, 2010
- DOI：10.1117/1.3360308
- PMID：20459236
- 来源：https://doi.org/10.1117/1.3360308
- 本地原文：[[01_虚拟仿真平台/02_论文原文/01_Treeby2010_kWave_original.pdf|打开 PDF]]
- 核验状态：PDF 已取得；本笔记尚未逐条按页码复核。

## 研究目的

提出并说明 [[05_论文与概念/concepts/k-Wave|k-Wave]] MATLAB 工具箱，用于一维、二维和三维声波传播仿真，以及[[05_论文与概念/concepts/时间反转|时间反转]]重建。

## 实验/仿真对象

均匀和非均匀介质中的声波场，重点是光声成像场景，但核心求解器也被大量用于医学超声、HIFU 和 tFUS。

## 设备或软件

- MATLAB [[05_论文与概念/concepts/k-Wave|k-Wave]]。
- k-space pseudospectral time-domain 求解器。
- PML 吸收边界。

## 数据来源与预处理

工具论文本身不依赖特定 CT 数据。使用者需要提供网格、介质声速、密度、吸收和声源/探测器分布。

## 参数设置

主要由用户定义：

- 网格维度与步长。
- 介质声速、密度、吸收。
- 声源时序和空间分布。
- 传感器位置。

## 实验步骤

1. 定义计算网格。
2. 指定介质参数。
3. 设置声源和传感器。
4. 运行时间域传播仿真。
5. 保存传感器数据或全场声压。
6. 如需要，使用[[05_论文与概念/concepts/时间反转|时间反转]]进行图像或声源重建。

## 结果指标

- 时间域压力信号。
- 空间声压场。
- [[05_论文与概念/concepts/时间反转|时间反转]]重建结果。

## 安全性与局限

该文是数值工具论文，不直接给出人体安全阈值。用于 tFUS 时需要额外加入颅骨参数、热模型和安全评估。

## 与 fus-sim 的衔接

`fus-sim` 当前路线可把该文作为 [[05_论文与概念/concepts/k-Wave|k-Wave]] 工作流的基础引用：先建立均匀介质声场，再逐步加入颅骨、吸收、热效应和相位校正。

## 关联

- [[MOC_声场仿真与相位校正]] | [[MOC_实验方法与仿真流程]]
- 本地论文: [[01_seed_papers_summary]]
- 术语: [[05_术语表_零基础版]]

## 同主题横向互链

- [[02_Treeby2012_nonlinear_heterogeneous]] — 同一作者，非线性扩展
- [[03_Leung2019_rapid_beam_simulation]] — 基于 [[05_论文与概念/concepts/k-Wave|k-Wave]] 的快速仿真
- [[04_Jin2020_open_source_phase_correction]] — [[05_论文与概念/concepts/k-Wave|k-Wave]] 相位校正应用
- [[05_论文与概念/notes/25_Pasquinelli2020_transducer_modeling_for]] — [[05_论文与概念/concepts/k-Wave|k-Wave]] 换能器建模
