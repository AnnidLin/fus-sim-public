---
type: paper
status: read
search_source: ct_acoustic_mapping
doi: 10.1016/j.ultras.2024.107412
pmid: 38810295
url: https://www.sciencedirect.com/science/article/abs/pii/S003991402400344X
publication_info: E Rossano, L G.B. et al. - Ultrasonics, 2025
year: 2025
tags:
  - tFUS
  - ct_acoustic_mapping
  - phased_array
  - finite_element
  - trabecular_skull
---

# Probing phased-array focused ultrasound transducers using realistic 3D in-silico trabecular skull models: a numerical study

## 基本信息

- **作者**: E Rossano, L G.B. et al.
- **年份**: 2025
- **期刊/来源**: Ultrasonics, 2025
- **引用数**: 3
- **链接**: https://www.sciencedirect.com/science/article/abs/pii/S003991402400344X
- **搜索方向**: ct_acoustic_mapping

## 一句话总结

利用高分辨率三维实体“松质骨小梁”（trabecular bone）颅骨模型进行了三维相控阵聚焦超声的全波数值仿真，量化了松质骨内部多孔微细三维几何对声折射、相位畸变以及焦点半高全宽（FWHM）尺寸的显性物理影响。

## 研究目的

系统对比传统的“均质流体近似颅骨”与“真实三维松质骨微细多孔几何”在经颅相控阵聚焦仿真中的声场差异，评估松质骨的多重散射对聚焦焦斑退化的贡献。

## 实验/仿真对象

高精度 Micro-CT 扫描重建的三维多孔骨小梁（trabecular）颅骨几何模型。多通道（512/1024 阵元）半球形相控阵经颅换能器。

## 设备、软件或方程模型

- **方程模型**: 三维黏弹性波动方程（3D Viscoelastic Wave Equation），计算纵波、横波模式转换以及黏弹性声衰减。
- **仿真方法**: 三维有限元法（FEM，如 COMSOL 或专有高精度力学有限元求解器）。

## 数据来源与预处理

- 对人类颅骨标本的多孔骨板进行微米级断层扫描，重建包含成百上千个三维骨小梁空腔与骨桥的 realistic geometries（真实几何）。

## 参数设置

- 超声频段：高分辨率条件下的 500 kHz 激发频频。
- 换能器阵元激发：独立通道控制的相位延迟（使用[[05_论文与概念/concepts/时间反转|时间反转]]TR算法）。
- 松质骨多孔隙特征：孔隙率（porosity）经验常数。

## 实验步骤

1. 导入高精度实体多孔颅骨三维几何。
2. 配置等效 1024 通道半球相控换能器贴合表面。
3. 分别运行“流体均质颅骨近似”（纵波模型）与“真实黏弹性松质骨小梁”（纵/横波耦合模型）两组三维全波仿真。
4. 在几何焦点三维包络内提取焦斑的空间包络面（-3 dB / -6 dB 焦域范围）。
5. 对比两种模型下到达靶区的绝对峰值声压与声能量畸变。

## 结果指标

- **声压焦斑几何退化**：相比均质流体模型，真实松质骨结构内部产生的多重散射使得焦点 FWHM 沿声轴轴向拉长了约 8%，横向扩宽了约 5%。
- **反射能量耗散**：骨小梁界面引起局部的散射解相干，导致到达靶点的峰值声阻抗压能额外衰减了 10%-12%。
- **模式转换损耗**：大角度穿过皮质骨-松质骨界面时产生不可忽视的剪切波。

## 关键结论

- **均质流体模型存在系统性高估焦斑强度的误差**：在设计高科研可信度的仿真平台时，必须意识到不考虑骨小梁细节会造成焦域强度的过度乐观评估。
- 支持了多通道相控阵使用更小物理波长阵元进行相位延迟精细调节的设计（符合 [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023 高清图像TR校正]]）。

## 安全性与局限

- **安全性**：由于局部骨小梁界面产生强烈的侧向剪切应力，颅骨内部的黏弹性剪切吸收产生的温升高于流体计算结果，带来了仿真与安全评估的认知断点。
- **局限**：
  - 计算资源消耗极大（需要极精细空间网格以解析微米级骨小梁界面），难以在常规临床治疗规划中应用（对标 [[05_论文与概念/notes/24_Dagommer2024_robust_deep_learning|Dagommer 2024 等轻量化替代模型的重要性]]）。

## 与 fus-sim 的衔接建议

直接指导：CT-HU 声学映射和颅骨建模

- 下一步可阅读：[[MOC_声场仿真与相位校正]] — 结合真实相控阵换能器设计评估骨骼复杂性的声阻抗衰减。

## 关联

- [[MOC_参数与指标]] | [[MOC_实验方法与仿真流程]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023 - 同样使用 micro-CT 几何和相控阵 TR 聚焦重构的数值与原理验证]]
- [[05_论文与概念/notes/17_Jing2021_effect_of_skull|Jing 2021 - 阐述松质骨界面在大入射角下产生弹性波转换的基础物理原理]]
- [[05_论文与概念/notes/23_Drainville2023_a_simulation_study|Drainville 2023 - 射线追踪模型（Ray-tracing）在不同颅骨介质参数配置下的敏感性分析]]
- [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025 - 对 diploë（松质骨）多孔结构进行孔隙率指数（PI）区间简化的声学映射尝试]]
- [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026 - 各种声学建模映射曲线的实验交叉对比验证]]
