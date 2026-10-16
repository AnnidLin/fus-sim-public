---
type: paper
status: read
search_source: parameter_effect
doi: 10.1109/TMRB.2023.3289012
pmid: 37341029
url: https://ieeexplore.ieee.org/document/10160215
publication_info: M Javid, M R.A. et al. - IEEE Transactions on Medical Robotics and Bionics, 2023
year: 2023
tags:
  - tFUS
  - parameter_effect
  - review
  - hardware
---

# A review of ultrasound neuromodulation technologies

## 基本信息

- **作者**: M Javid, M R.A. et al.
- **年份**: 2023
- **期刊/来源**: IEEE Transactions on Medical Robotics and Bionics, 2023
- **引用数**: 34
- **链接**: https://ieeexplore.ieee.org/document/10160215
- **搜索方向**: parameter_effect

## 一句话总结

系统综述了超声脑调控的系统集成、换能器结构设计与传感器技术，比较了单阵元球面聚焦与多通道相控阵换能器在不同临床大脑靶点定位中的声学优势与局限。

## 研究目的

从工程学和医疗机器人角度，综述用于神经调控的经颅聚焦超声硬件设计、声束合成控制算法和传感器反馈技术的发展。

## 实验/仿真对象

主流超声神经调控设备平台，包括商用 MRgFUS（ExAblate）以及定制化实验室桌面系统。

## 设备、软件或方程模型

- **硬件结构**: 单阵元（Single-element）、环形阵列（Annular array）、二维相控阵（2D Phased array）。
- **定位辅助**: 磁共振成像引导（MRgFUS）、红外光学导航。

## 数据来源与预处理

工程与临床文献回顾，分析不同频率、激发功率和声场焦斑几何（长轴、短轴尺寸）的物理参数分配。

## 参数设置

- 常用频段：200 kHz - 1.0 MHz（对标 [[07_tFUS文献与公开代码参数对照|代码与参数对照表中的频频对标]]）。
- 阵元分布：从几十个到 1024 阵元相控系统。
- 焦点声能分布与旁瓣控制。

## 实验步骤

1. 收集和分类各种超声调控硬件的物理声学指标。
2. 比较不同物理设计（如平面振子加透镜 vs 球面压电陶瓷）的聚焦增益（focal gain）。
3. 整理适用于人体头部定位的相控阵相位延迟计算方法。
4. 汇编反馈机制（如[[05_论文与概念/concepts/PCD|被动空化探测器]] [[05_论文与概念/concepts/PCD|PCD]]，或磁共振温度成像 MRTI）的技术整合方案。

## 结果指标

- **聚焦性能**：单阵元系统空间定位灵活性差，焦斑呈长条橄榄状。
- **相位补偿复杂性**：多阵元相控阵能动态平移焦点，但需要实时颅骨个体化相位校正（对标 [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction|Jin 2020 开源相位校正工具]]）。
- **硬件集成度**：磁共振兼容（MR-compatible）的换能器材质研发是当前工程难点。

## 关键结论

- **单阵元与相控阵各具适应症**：在临床参数校准中，单阵元适合运动皮层等浅表靶区（符合 [[05_论文与概念/notes/05_Legon2014_human_somatosensory|Legon 2014 实验]]）；而伏隔核或海马等深部核团必须依靠多通道相控阵进行相位补偿聚焦（符合 [[05_论文与概念/notes/18_Rezai2025_focused_ultrasound_neuromodulation|Rezai 2025 双侧伏隔核调控]]）。
- **强烈建议在仿真设计中引入换能器的声电学阻抗与表面非均匀激发校准**（对标 [[05_论文与概念/notes/25_Pasquinelli2020_transducer_modeling_for|Pasquinelli 2020 的换能器仿真标定]]）。

## 安全性与局限

- **安全性**：热剂量指数和瞬时声强需进行软硬件双重限幅保护。
- **局限**：
  - 侧重于硬件系统架构，缺乏对神经元受体通道机械门控（mechanosensitive channels）具体生理机制的深入探讨。

## 与 fus-sim 的衔接建议

直接指导：参数设置和效应关系

- 下一步可阅读：[[MOC_AI与深度学习替代模型]] — 查阅使用 AI 进行快速声束聚焦合成的方案。

## 关联

- [[MOC_参数与指标]] | [[MOC_研究问题与争议]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[05_论文与概念/notes/25_Pasquinelli2020_transducer_modeling_for|Pasquinelli 2020 - 单阵元聚焦换能器的自由场标定与等效源数值建模]]
- [[05_论文与概念/notes/15_Lee2024_a_review_of|Lee 2024 - 关注人体临床应用与安全参数的荟萃综述]]
- [[05_论文与概念/notes/16_Chen2023_numerical_and_experimental|Chen 2023 - 低强度超声经人颅骨折射的数值与实验评测]]
- [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction|Jin 2020 - 开源相控阵相位校正算法及 ex vivo 颅骨水槽测定]]
- [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025 - 多通道相控阵聚焦在松质骨内部多孔界面的三维有限元仿真]]
