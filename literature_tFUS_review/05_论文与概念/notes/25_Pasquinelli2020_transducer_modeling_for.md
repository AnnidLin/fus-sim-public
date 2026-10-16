---
type: paper
status: unread
search_source: freefield_calibration
doi: 
pmid: 
pmcid: 
url: https://iopscience.iop.org/article/10.1088/1741-2552/ab98dc/meta
publication_info: C Pasquinelli, H Montanaro, HJ Lee… - Journal of neural …, 2020 - iopscience.iop.org
year: 2020
tags:
  - tFUS
  - freefield_calibration
---

# Transducer modeling for accurate acoustic simulations of transcranial focused ultrasound stimulation

> [!warning] 核验状态
> [[01_虚拟仿真平台/02_论文原文/25_Pasquinelli2020_transducer_modeling_accepted_manuscript.pdf|本地作者接受稿]]已取得；本笔记尚未逐条按页码复核。

## 基本信息

- **作者**: C Pasquinelli, H Montanaro, HJ Leeet al.
- **年份**: 2020
- **期刊/来源**: C Pasquinelli, H Montanaro, HJ Lee… - Journal of neural …, 2020 - iopscience.iop.org
- **引用数**: 41
- **链接**: https://iopscience.iop.org/article/10.1088/1741-2552/ab98dc/meta
- **搜索方向**: freefield_calibration

## 一句话总结

使用水听器声压测量验证单阵元聚焦换能器的模型精度，建立"换能器几何模型 → 自由场仿真 → 实验测量"的校准链，确保 tFUS 声场仿真的声学精度。

## 研究目的

开发并验证能够准确预测单阵元聚焦换能器声场输出的换能器模型，为后续经颅仿真提供可靠的源模型基础。

## 实验/仿真对象

体外实验 + 数值仿真：单阵元聚焦换能器在水介质中的声场传播。

## 设备、软件或方程模型

- **换能器**：单阵元聚焦换能器（single-element focused transducer）
- **测量设备**：水听器（hydrophone）声学压力测量系统
- **仿真工具**：声场仿真平台（具体 solver 需阅读原文）
- **对比模型**：几何活塞模型（piston source）vs 更精细的换能器模型

## 数据来源与预处理

- 水听器测量获取换能器声场的空间声压分布
- 换能器几何参数（孔径、曲率半径、频率）用于构建仿真模型

## 参数设置

- **换能器类型**：single-element focused
- **孔径/曲率半径**：具体值需阅读原文（但属于小型单阵元范围）
- **频率**：tFUS 常用范围（可能 500 kHz 或类似）
- **测量介质**：水（均匀介质，无颅骨）
- **测量网格**：hydrophone 扫描（可能为 2D 平面扫描，步长需阅读原文）

## 实验步骤

1. 测量单阵元聚焦换能器的几何参数（孔径、曲率半径、焦距）。
2. 在水槽中使用水听器扫描测量换能器的声场分布（峰值声压、焦距、焦域大小）。
3. 构建简单的几何活塞模型（piston source）作为仿真基线。
4. 构建更精细的换能器模型（可能包含更真实的振动面分布）。
5. 运行自由场仿真（水介质），对比仿真与实验测量的声场指标。
6. 评估不同换能器模型对仿真精度的影响。

## 结果指标

- 焦点位置（焦距）
- 峰值声压（仿真 vs 实验）
- 焦域大小（-6 dB 横向/轴向宽度）
- 声压分布曲线（横向/轴向剖面）
- 模型误差（几何活塞模型 vs 精细模型 vs 实验）

## 关键结论

- **换能器模型对仿真精度有决定性影响**：简单的几何活塞模型（piston source）可能无法准确预测真实换能器的声场输出。
- **水听器验证是必要的**：任何用于 tFUS 仿真的换能器模型，都应先用自由场/水槽实验验证。
- **模型改进方向**：更精细的换能器模型（如考虑振动面不均匀性、实际孔径函数）能提高仿真精度。

## 安全性与局限

- **安全性**：本文仅涉及自由场（水介质）声场验证，不涉及颅骨或生物组织，无生物安全性问题。
- **局限**：
  - **仅验证单阵元**：未覆盖多阵元、相控阵或环形阵列的换能器模型。
  - **自由场验证**：水槽中的自由场验证与经颅场景（有颅骨畸变）不同，自由场验证通过不代表经颅仿真正确。
  - **未涉及非线性**：高强度下的非线性效应可能改变换能器输出，但本文可能限于线性验证。
- **与 fus-sim 的关联**：当前 `aperture=25 mm, radius=30 mm` 和 `aperture=30 mm, radius=35 mm` 是几何参数近似，需要建立类似的自由场验证流程。
## 与 fus-sim 的衔接建议

直接指导：换能器建模和声场校准

- 下一步可阅读：[[MOC_声场仿真与相位校正]]

## 关联

- [[MOC_声场仿真与相位校正]] | [[MOC_参数与指标]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

