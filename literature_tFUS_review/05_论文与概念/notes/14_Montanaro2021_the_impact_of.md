---
type: paper
status: unread
search_source: ct_acoustic_mapping
doi: 
pmid: 
pmcid: 
url: https://iopscience.iop.org/article/10.1088/1741-2552/abf68d/meta
publication_info: H Montanaro, C Pasquinelli, HJ Lee… - Journal of Neural …, 2021 - iopscience.iop.org
year: 2021
tags:
  - tFUS
  - ct_acoustic_mapping
---

# The impact of CT image parameters and skull heterogeneity modeling on the accuracy of transcranial focused ultrasound simulations

> [!warning] 核验状态
> [[01_虚拟仿真平台/02_论文原文/14_Montanaro2021_CT_parameters_accepted_manuscript.pdf|本地作者接受稿]]已取得；本笔记尚未逐条按页码复核。

## 基本信息

- **作者**: H Montanaro, C Pasquinelli, HJ Leeet al.
- **年份**: 2021
- **期刊/来源**: H Montanaro, C Pasquinelli, HJ Lee… - Journal of Neural …, 2021 - iopscience.iop.org
- **引用数**: 44
- **链接**: https://iopscience.iop.org/article/10.1088/1741-2552/abf68d/meta
- **搜索方向**: ct_acoustic_mapping

## 一句话总结

使用 CT-based 声学属性图（heterogeneous skull model）比均质颅骨模型能更准确地估计声波穿过颅骨后的空间分布。

## 研究目的

评估 CT 图像参数（层厚、重建核、HU 阈值）和颅骨异质性建模对经颅聚焦超声仿真精度的影响。

## 实验/仿真对象

仿真研究：对比 homogeneous skull model vs CT-based heterogeneous acoustic property maps 在 tFUS 声场传播中的差异。

## 设备、软件或方程模型

- 声场求解器：基于 CT 的声学属性映射方法
- 对比模型：homogeneous skull model vs heterogeneous skull model
- 成像协议：CT 扫描参数（层厚、重建核、HU 阈值）

## 数据来源与预处理

- 使用 CT 扫描数据生成声学属性映射图（HU → 声速/密度/衰减）
- 评估不同 CT 参数对声学属性分布的影响

## 参数设置

- **CT 重建参数**：层厚、重建核、HU 阈值（具体值需阅读原文获取）
- **声学映射**：HU-based 连续映射或分段映射
- **对比基线**：homogeneous skull model（均质颅骨参数）

## 实验步骤

1. 从 CT 数据生成声学属性映射图（heterogeneous mapping）。
2. 构建均质颅骨模型作为对比基线。
3. 运行 tFUS 声场仿真，比较两种模型下的声压空间分布。
4. 评估 CT 参数（层厚、重建核）对声学属性分布和声场输出的影响。

## 结果指标

- 声压空间分布差异（heterogeneous vs homogeneous）
- 焦点位置偏移量
- 声压衰减程度
- CT 参数敏感性（层厚、重建核、HU 阈值变化导致的声场差异）

## 关键结论

- **异质颅骨模型显著优于均质模型**：CT-based 声学属性映射能更好地估计声波穿过颅骨后的空间分布。
- **CT 参数选择直接影响仿真精度**：不同 CT 层厚、重建核、HU 阈值会导致声学属性分布的差异，进而影响声场输出。
- **建模策略建议**：使用 CT 个体化异质颅骨模型优于简化均质模型，但需明确 CT 参数设置。

## 安全性与局限

- **安全性**：本文是仿真方法学论文，不涉及安全性评估。
- **局限**：
  - 未系统量化 CT 层厚、重建核、HU 阈值的具体敏感性范围。
  - 未与真实人体实验或水听器测量进行交叉验证。
  - 仅对比 homogeneous vs CT-based，未包含其他映射策略（如 porosity-based）。
- **与 fus-sim 的关联**：当前 `HU >= 300` baseline 和 `continuous_skull` mapping 需要在该框架下评估 CT 参数敏感性。
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
- [[17_Jing2021_effect_of_skull]]
- [[26_Kong2025_a_novel_method]]
- [[27_Li2026_experimental_validation_of]]
- [[24_Dagommer2024_robust_deep_learning]]
