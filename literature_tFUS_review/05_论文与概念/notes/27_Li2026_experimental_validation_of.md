---
type: paper
status: unread
search_source: ct_acoustic_mapping
doi: 
pmid: 
pmcid: 
url: https://arxiv.org/abs/2606.09497
publication_info: H Li, AJ Horner, X Zhang, Z Huang - arXiv preprint arXiv:2606.09497, 2026 - arxiv.org
year: 2026
tags:
  - tFUS
  - ct_acoustic_mapping
---

# Experimental Validation of Skull Acoustic Modelling Strategies for Transcranial Focused Ultrasound Simulation: A Cross-Comparison Study

> [!warning] 核验状态
> [[01_虚拟仿真平台/02_论文原文/27_Li2026_skull_model_validation_preprint.pdf|本地 arXiv 预印本]]已取得；该版本尚非同行评审正式版，本笔记也尚未逐条按页码复核。

## 基本信息

- **作者**: H Li, AJ Horner, X Zhang, Z Huang
- **年份**: 2026
- **期刊/来源**: H Li, AJ Horner, X Zhang, Z Huang - arXiv preprint arXiv:2606.09497, 2026 - arxiv.org
- **引用数**: 0
- **链接**: https://arxiv.org/abs/2606.09497
- **搜索方向**: ct_acoustic_mapping

## 一句话总结

设计实验交叉验证框架，系统比较多种颅骨声学建模策略（包括基于局部孔隙率、颅骨密度比等）的精度，为 tFUS 仿真中的颅骨建模选择提供定量依据。

## 研究目的

建立一种可复现的交叉验证方法论，用于比较和评估不同颅骨声学建模策略在 tFUS 仿真中的预测精度。

## 实验/仿真对象

实验 + 仿真交叉验证：使用多个颅骨样本，分别用不同建模策略生成声学属性图，运行仿真，并与实验测量对比。

## 设备、软件或方程模型

- **实验设备**：水听器测量系统、tFUS 换能器
- **颅骨样本**：多个颅骨 CT 或物理标本（具体数量需阅读原文）
- **建模策略**：
  - 局部孔隙率（local porosity）方法
  - 颅骨密度比（Skull Density Ratio, SDR）方法
  - 其他常见策略（如 HU 直接映射）
- **声场求解器**：具体 solver 需阅读原文

## 数据来源与预处理

- 颅骨 CT 数据用于生成不同策略的声学属性映射
- 实验测量数据作为验证基准（ground truth）
- 生成每种策略的声场预测结果与实验对比

## 参数设置

- **建模策略**：至少 3 种（local porosity, SDR, HU-based）
- **频率**：tFUS 常用范围（具体值需阅读原文）
- **对比指标**：焦点位置、声压峰值、焦域大小、整体声场分布相关性
- **统计方法**：跨多个颅骨样本的系统性对比（具体统计方法需阅读原文）

## 实验步骤

1. 获取多个颅骨样本的 CT 数据和对应的实验声场测量数据。
2. 对每种颅骨声学建模策略（porosity-based, SDR-based, HU-based 等）：
   a. 从 CT 数据生成声学属性映射图。
   b. 运行 tFUS 声场仿真。
   c. 提取关键声场指标（焦点位置、峰值声压、焦域大小）。
3. 将每种策略的仿真结果与实验测量进行对比。
4. 计算每种策略的预测误差（位置误差、声压误差、分布相关性）。
5. 跨多个颅骨样本进行统计对比，评估哪种策略更稳健。

## 结果指标

- 焦点位置误差（每种策略 vs 实验）
- 峰值声压相对误差
- 焦域大小（-6 dB）差异
- 声场分布相关性（如 Pearson 相关系数、SSIM）
- 跨样本的误差统计（均值、标准差、置信区间）
- 策略排名或推荐

## 关键结论

- 提供了**交叉验证设计的统计方法**：如何用多个颅骨样本、多种建模策略、多种误差指标进行系统对比。
- **不同建模策略的精度可量化比较**：通过统一的实验基准和统计框架，可以客观判断哪种策略更优。
- **为 fus-sim 验证 roadmap 提供直接借鉴**：可以复用该框架来验证当前 `simple_hu300`、连续映射、孔隙率映射等策略的相对精度。

## 安全性与局限

- **安全性**：本文是方法学论文，不涉及生物安全性。
- **局限**：
  - **arXiv 预印本**：尚未经过正式同行评审，结论可能被后续修改。
  - **实验条件限制**：体外实验条件与体内真实场景存在差异。
  - **样本代表性**：颅骨样本可能无法覆盖所有人群（年龄、性别、颅骨厚度差异）。
  - **策略覆盖度**：仅比较了有限几种建模策略，未覆盖所有可能的映射方法。
- **与 fus-sim 的关联**：可直接借鉴其"多种策略 + 实验基准 + 统计对比"的验证框架，用于设计 fus-sim 的 mapping profile 验证 roadmap。
## 与 fus-sim 的衔接建议

直接指导：CT-HU 声学映射和颅骨建模

- 下一步可阅读：[[MOC_参数与指标]]

## 关联

- [[MOC_参数与指标]] | [[MOC_实验方法与仿真流程]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[13_Koh2021_acoustic_simulation_for]]
- [[14_Montanaro2021_the_impact_of]]
- [[17_Jing2021_effect_of_skull]]
- [[26_Kong2025_a_novel_method]]
- [[24_Dagommer2024_robust_deep_learning]]
