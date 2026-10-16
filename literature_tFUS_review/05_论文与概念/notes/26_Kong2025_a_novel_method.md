---
type: paper
status: unread
search_source: ct_acoustic_mapping
doi: 
pmid: 
pmcid: 
url: https://www.nature.com/articles/s41598-025-33411-x
publication_info: D Kong, T Zhang, G Hou, G Liu, X Qi, H Xing - Scientific Reports, 2025 - nature.com
year: 2025
tags:
  - tFUS
  - ct_acoustic_mapping
---

# A novel method for acoustic modeling of cranial bone based on the porosity index

> [!warning] 核验状态
> [[01_虚拟仿真平台/02_论文原文/26_Kong2025_porosity_index_original.pdf|本地开放获取正式版]]已取得；本笔记尚未逐条按页码复核。

## 基本信息

- **作者**: D Kong, T Zhang, G Hou, G Liu, X Qi, H Xing
- **年份**: 2025
- **期刊/来源**: D Kong, T Zhang, G Hou, G Liu, X Qi, H Xing - Scientific Reports, 2025 - nature.com
- **引用数**: 0
- **链接**: https://www.nature.com/articles/s41598-025-33411-x
- **搜索方向**: ct_acoustic_mapping

## 一句话总结

提出基于颅骨孔隙率指数（Porosity Index, PI）的声学建模新方法，将 7 个 CT Hounsfield Unit 区间映射为声学属性，作为传统 HU 直接映射的替代方案。

## 研究目的

开发一种不直接依赖 HU 值而是基于颅骨孔隙率指数的声学建模方法，以改进经颅聚焦超声仿真中的颅骨声学属性分配精度。

## 实验/仿真对象

仿真研究：使用 CT 数据计算颅骨孔隙率指数，并基于 PI 生成声学属性映射图用于 tFUS 声场仿真。

## 设备、软件或方程模型

- **成像**：CT 扫描（用于获取 HU 和计算 PI）
- **映射方法**：7 个 CT HU 区间 → PI → 声学属性（声速、密度、衰减）
- **对比基线**：传统 HU 直接映射方法
- **声场求解器**：具体 solver 需阅读原文（可能为 [[05_论文与概念/concepts/k-Wave|k-Wave]] 或 FDTD）

## 数据来源与预处理

- CT 扫描数据用于提取 HU 值和计算孔隙率指数
- 将颅骨区域按 HU 分段为 7 个区间，每个区间对应不同的 PI 值
- 基于 PI 映射生成声学属性图

## 参数设置

- **CT 分段**：7 个 HU 区间（具体 HU 范围需阅读原文）
- **映射链**：HU → PI（孔隙率指数）→ 声学属性（声速、密度、衰减）
- **对比基线**：传统 HU 直接映射（如线性或分段线性 HU→声学属性）

## 实验步骤

1. 从 CT 数据提取颅骨区域的 HU 值分布。
2. 将 HU 分布分段为 7 个区间，计算每个区间的孔隙率指数（PI）。
3. 基于 PI 映射生成声学属性图（声速、密度、衰减系数）。
4. 同时基于传统 HU 直接映射生成对比用的声学属性图。
5. 运行 tFUS 声场仿真，对比 PI-based mapping vs HU-based mapping 的声场输出差异。
6. 评估 PI 方法在焦点位置、声压峰值、衰减量等方面的表现。

## 结果指标

- 焦点位置（PI-based vs HU-based）
- 峰值声压（两种映射方法的差异）
- 声压衰减（透过颅骨后的声压损失对比）
- 焦点大小（-6 dB 区域对比）
- 映射方法间的系统性差异

## 关键结论

- **PI 方法是 HU 直接映射的可行替代**：基于孔隙率指数的映射能产生与 HU 直接映射不同的声学属性分布，可能更符合颅骨真实声学特性。
- **7 区间 HU 分段**：将 HU 分为 7 个区间并分别映射，比单一连续映射更能捕捉颅骨结构异质性。
- **需要对比验证**：PI 方法是否优于 HU 直接映射，需要与实验测量或交叉验证框架对比确认。

## 安全性与局限

- **安全性**：本文是仿真方法学论文，不涉及生物安全性评估。
- **局限**：
  - **新论文（0 引用）**：尚未经过广泛同行评审和复现验证，结论的稳健性待确认。
  - **未与实验交叉验证**：仅展示了仿真层面的对比，未用水听器或体内实验验证 PI 方法的物理正确性。
  - **HU 区间划分的通用性**：7 个 HU 区间的划分方式可能依赖于特定 CT 协议，通用性需验证。
  - **PI 计算依赖 CT 分辨率**：临床 CT 分辨率（1-3 mm）可能不足以精确计算局部孔隙率。
- **与 fus-sim 的关联**：可作为 `acoustic_mapping_profiles/` 中一个候选 profile（`kong2025_porosity_index_draft.json`），但只能做 model-build-only validation，不进入 pressure simulation，直到经过交叉验证。
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
- [[27_Li2026_experimental_validation_of]]
- [[24_Dagommer2024_robust_deep_learning]]
