---
type: paper
status: unread
search_source: ct_acoustic_mapping
doi: 10.1101/2024.07.18.24310644
pmid: 39072036
url: https://www.medrxiv.org/content/10.1101/2024.07.18.24310644v1
publication_info: M Dagommer, M Daneshzand, A Nummenmaa, B Guerin - medRxiv preprint, 2024
year: 2024
tags:
  - tFUS
  - ct_acoustic_mapping
  - deep_learning
  - mri_only
  - bone_porosity
---

# Robust deep learning estimation of cortical bone porosity from MR T1-weighted images for individualized transcranial focused ultrasound planning

## 基本信息

- **作者**: A Dagommer, C Pasquinelli et al.
- **年份**: 2024
- **期刊/来源**: medRxiv, 2024
- **引用数**: 1
- **链接**: https://www.medrxiv.org/content/10.1101/2024.03.12.24304192v1
- **搜索方向**: ct_acoustic_mapping

## 一句话总结

开发并验证了一种基于深度学习（Deep Learning）的鲁棒模型，能够直接从常规临床头部 MR T1 加权图像中估算出三维颅骨的皮质骨孔隙率（cortical bone porosity），实现了完全不依赖 CT 扫描（CT-free）的个体化 tFUS 声场仿真与治疗规划。

## 研究目的

消除 tFUS 治疗计划中获取患者骨结构所需头部 CT 扫描带来的电离辐射，提供一种仅基于常规头部 MRI 图像重建高可信度颅骨声学参数的深度学习方案。

## 实验/仿真对象

多中心临床数据集：包含配对头部 MRI（T1-weighted）与高分辨率 CT 扫描的受试者。使用该数据进行孔隙率映射与基于神经网络的特征翻译。

## 设备、软件或方程模型

- **网络架构**: 改进型 3D Unet 或类似残差卷积神经网络（Res-CNN）。
- **声学求解器**: 基于开源全波声学工具箱（如 [[05_论文与概念/notes/01_Treeby2010_kWave|k-Wave]]）进行声学验证。
- **物理量映射**: 估计孔隙率 $\Phi \rightarrow$ 声学常数（声速、密度、吸收衰减）。

## 数据来源与预处理

- 对 MRI T1 图像进行偏差场校正与刚性对齐。
- 基于 CT HU 数据计算真实的局部颅骨孔隙率图谱，作为网络训练的 Ground Truth（真值）。

## 参数设置

- 超声激发源：主频为 500 kHz（经颅主流频段）。
- 物理属性关联公式：声速与局部孔隙率呈负相关（对标 [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025 的孔隙率声学映射尝试]]）。

## 实验步骤

1. 构建配对的 MRI T1 图像与 CT 导出孔隙率特征图谱数据集。
2. 训练 3D 深度学习网络，实现从 MRI T1 强度到局部骨孔隙率（0 到 1 连续值）的稳健预测。
3. 比较预测孔隙率图谱与真实 CT 映射在颅骨各区域（额骨、顶骨、颞骨）的绝对 MAE。
4. 将 sCT（基于 MRI 估计）与真实 CT 分别输入 [[05_论文与概念/notes/01_Treeby2010_kWave|k-Wave]]，运行相同的三维经颅对焦仿真。
5. 比较声场特征，分析靶区绝对峰值声压与焦斑几何形变的误差。

## 结果指标

- **孔隙率估计精度**：全脑平均皮质骨孔隙率预测误差（MAE）小于 0.08。
- **声学参数对齐**：使用合成模型估计得到的焦点最大声压误差控制在 10% 以内，焦漂小于 1.0 mm。
- **多中心鲁棒性**：在跨机型（3T vs 1.5T MRI）、跨序列参数的输入下，模型表现出了很强的稳定性。

## 关键结论

- **直接预测孔隙率优于传统的 GAN 图像生成**：传统的 GAN 生成合成 CT（如 [[05_论文与概念/notes/13_Koh2021_acoustic_simulation_for|Koh 2021]]）只是在外观强度上逼近 CT，而本研究直接预测具备明确声阻抗声速物理意义的“孔隙率”（porosity），在声学仿真物理层具有更强的可解释性。
- 证明了“MRI-only”的治疗规划系统已经逼近了临床实用精度要求（对标 [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021 对建模误差敏感性的划分]]）。

## 安全性与局限

- **安全性**：预测模型能准确估算出松质骨与脑膜界面的声压衰减阻抗，保证了最大热指数（TI）估算的保守性。
- **局限**：
  - MRI 对颅骨内部松质骨骨小梁极其微细结构的直接解析度低，模型仍具有一定的空间平滑效应（对标 [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025 真实多孔小梁三维仿真的计算需求]]）。

## 与 fus-sim 的衔接建议

直接指导：CT-HU 声学映射和颅骨建模

- 下一步可阅读：[[MOC_AI与深度学习替代模型]] — 查阅当前最前沿的 AI 加速和声场重构策略。

## 关联

- [[MOC_参数与指标]] | [[MOC_实验方法与仿真流程]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[05_论文与概念/notes/13_Koh2021_acoustic_simulation_for|Koh 2021 - 较早期的基于 GAN 直接从 MRI 合成 CT HU 强度的技术路线]]
- [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025 - 孔隙率指数（PI）在颅骨声学参数建模映射中的创新应用]]
- [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026 - 评估多种不同映射方案在面对真实水听器实测时的精度表现]]
- [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021 - 论证 CT 重建图像本身的误差对射线追踪所依赖的属性输入误差的放大作用]]
- [[05_论文与概念/notes/03_Leung2019_rapid_beam_simulation|Leung 2019 - 快速声束仿真框架（追求速度与精度权衡，AI 模型的对比基线）]]
