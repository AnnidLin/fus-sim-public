---
type: paper
status: read
search_source: skull_validation
doi: 10.1121/10.0017123
pmid: 36894012
url: https://asa.scitation.org/doi/10.1121/10.0017123
publication_info: A Drainville, K E.M. et al. - Journal of the Acoustical Society of America, 2023
year: 2023
tags:
  - tFUS
  - skull_validation
  - ray_tracing
  - sensitivity_analysis
---

# A simulation study on the sensitivity of transcranial ray-tracing ultrasound modeling to skull properties

## 基本信息

- **作者**: A Drainville, K E.M. et al.
- **年份**: 2023
- **期刊/来源**: JASA, 2023
- **引用数**: 22
- **链接**: https://asa.scitation.org/doi/10.1121/10.0017123
- **搜索方向**: skull_validation

## 一句话总结

系统量化了快速经颅超声“射线追踪”（Ray-tracing）声场仿真与相位校正模型对颅骨基本物理属性（声速、骨密度、骨厚度与声阻抗）空间变化的计算敏感性，指出了基于射线的方法在应对大倾角表面时的物理误差边界。

## 研究目的

评估基于声线追踪近似的快速治疗规划算法在颅骨物理参数不确定性（uncertainty）下的鲁棒性，指导临床快速规划中参数偏差容忍度。

## 实验/仿真对象

仿真计算：多阵元相控阵换能器向个体化人脑靶区发射声束，基于声线法跟踪多重几何折射。

## 设备、软件或方程模型

- **仿真模型**: 几何声线追踪（Geometric Ray-tracing）近似法。
- **参数控制**: 对比全波波动方程方法（对标 [[05_论文与概念/notes/01_Treeby2010_kWave|k-Wave 全波参考]]）。

## 数据来源与预处理

- 对输入三维颅骨模型各局部的介质声速、声阻抗与衰减系数设置正态分布物理扰动（perturbation）。

## 参数设置

- 声束主频：500 kHz 标准激发主频。
- 颅骨厚度扰动：$\pm 10\%-\pm 20\%$。
- 骨声速扰动范围：$2200 - 3000\text{ m/s}$。

## 实验步骤

1. 搭建多通道阵列源指向人脑深部靶点的三维几何对齐结构。
2. 使用几何射线追踪算法计算穿透颅骨的声线折射路径和时间延迟。
3. 依次引入声速波动、颅骨局部厚度测量误差和阻抗失配的不确定度。
4. 在靶点提取焦能量衰减因子、相位滞后误差和几何位置的误差矩阵。
5. 与对应的全波 pseudospectral 方法结果进行交叉比对。

## 结果指标

- **声速敏感性**：射线追踪相位延迟对局部骨声速的偏差具有**极高的敏感性**。声速估算偏离 5% 即可造成大于 $\pi/4$ 的相位误差。
- **厚度与倾角影响**：在超声入射角 $<15^\circ$ 时，射线追踪近似非常可靠；当入射角 $>20^\circ$ 时，射线法由于忽略了交界面的折射波发散与散射，误差陡增。
- **计算消耗对比**：声线法运行时间为毫秒级，而全波有限元/伪谱法为小时级。

## 关键结论

- **射线追踪是极快但敏感的双刃剑**：它完全能够用于床旁实时治疗对焦，但其输入模型（如合成 CT 或 HU-to-property 映射）的物理精度必须受到极其严格的门控（对标 [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021 论证的 CT 重建参数对仿真的干扰]]）。
- 强调了在大角度对焦时，结合 TR（[[05_论文与概念/concepts/时间反转|时间反转]]）等全波补偿策略对射线法进行局部校正的价值（对标 [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023 TR 聚焦性能验证]]）。

## 安全性与局限

- **安全性**：在大偏折角度下，声线追踪会低估由模式转换引起的硬脑膜局部高声能旁瓣，产生次级过热风险。
- **局限**：
  - 射线法在本质上忽略了声波在多孔多介质（骨小梁）中的多重散射波干涉（对标 [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025 松质骨有限元研究]]）。

## 与 fus-sim 的衔接建议

直接指导：颅骨声学仿真验证

- 下一步可阅读：[[MOC_声场仿真与相位校正]] — 查看射线追踪法与伪谱时间域法（[[05_论文与概念/concepts/k-Wave|k-Wave]]）的适用界限。

## 关联

- [[MOC_声场仿真与相位校正]] | [[MOC_实验方法与仿真流程]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction|Jin 2020 - 开源相位校正工具（使用 Kranion 软件，同样基于 ray-based 进行相位延迟校正）]]
- [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023 - 基于时间反转（TR）全波模型的相控阵对焦验证（对比射线法的全波基准）]]
- [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025 - 松质骨细节多孔散射下的声场聚焦，揭示了射线法无法表达的多重散射现象]]
- [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021 - 论证 CT 重建图像本身的层厚和算法如何放大射线追踪所依赖的属性输入误差]]
- [[05_论文与概念/notes/03_Leung2019_rapid_beam_simulation|Leung 2019 - 快速声束仿真框架（同样基于射线与角谱的简化思路，寻求速度与精度权衡）]]
