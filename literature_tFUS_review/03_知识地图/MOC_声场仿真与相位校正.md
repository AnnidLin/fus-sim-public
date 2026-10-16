# MOC：声场仿真与相位校正

> [!important] 主题位置
> 本页整理声场求解、经颅聚焦和相位校正的方法证据，不维护某一次运行状态。虚拟平台的最新结果和下一步统一见 [[实验平台阶段看板]]。

## 核心问题

经颅聚焦超声仿真的关键在于：颅骨导致声束畸变、声压衰减和焦点偏移，因此需要 CT 建模、介质参数映射、换能器定位和相位校正。

上游影像输入见 [[MOC_影像预处理与颅骨建模]]：DICOM/NIfTI、分割、配准和 CT-HU 声学映射会决定声场仿真的介质模型质量。

## 本地论文

- [[01_seed_papers_summary#1 高鹏皓 2022经颅聚焦超声调控系统的参数仿真研究|高鹏皓 2022]]
- [[01_seed_papers_summary#3 孙天宇 2021经颅聚焦超声治疗脑血栓的数值仿真研究|孙天宇 2021]]

- [[05_论文与概念/notes/28_Han2015_transcranial_brain_tumor_HIFU_review|韩珍珍 2015 - 经颅脑肿瘤 HIFU 综述]]

## 外部论文

- [[05_论文与概念/notes/01_Treeby2010_kWave|Treeby & Cox 2010 - k-Wave toolbox]]
- [[05_论文与概念/notes/02_Treeby2012_nonlinear_heterogeneous|Treeby et al. 2012 - 非线性异质介质超声传播]]
- [[05_论文与概念/notes/03_Leung2019_rapid_beam_simulation|Leung et al. 2019 - 经颅 FUS 快速声束仿真]]
- [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction|Jin et al. 2020 - 开源经颅相位校正工具]]
- [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021 - CT 参数与颅骨异质性建模对仿真精度影响]]
- [[05_论文与概念/notes/25_Pasquinelli2020_transducer_modeling_for|Pasquinelli 2020 - 换能器建模与声场仿真校准]]
- [[05_论文与概念/notes/23_Drainville2023_a_simulation_study|Drainville 2023 - 射线追踪对颅骨属性的敏感性]]
- [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023 - micro-CT 相控阵经颅超声聚焦]]
- [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025 - 3D 真实松质颅骨相控阵仿真]]
- [[05_论文与概念/notes/13_Koh2021_acoustic_simulation_for|Koh 2021 - GAN 合成 CT 声学仿真]]
- [[05_论文与概念/notes/16_Chen2023_numerical_and_experimental|Chen 2023 - 人体颅骨低强度 tFUS 数值与实验验证]]
- [[05_论文与概念/notes/17_Jing2021_effect_of_skull|Jing 2021 - 颅骨松质骨结构对经颅超声的影响]]
- [[05_论文与概念/notes/24_Dagommer2024_robust_deep_learning|Dagommer 2024 - 深度学习估计皮质骨孔隙率]]

## 可复现实验链

1. 均匀水介质聚焦声场。
2. 二维简化颅骨层。
3. 影像预处理与 CT 颅骨参数映射。
   - [[05_论文与概念/concepts/DICOM|DICOM]] / [[05_论文与概念/concepts/NIfTI|NIfTI]]
   - [[05_论文与概念/concepts/影像分割|影像分割]] / [[05_论文与概念/concepts/配准|配准]]
   - [[05_论文与概念/concepts/CT-HU映射|CT-HU 映射]]
   - [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021]]：CT 参数选择直接影响精度
   - [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025]]：孔隙率指数替代 HU 映射
   - [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026]]：实验交叉验证设计
4. 目标点与候选换能器点阵。
5. [[05_论文与概念/concepts/时间反转|时间反转]]或 ray-based 相位校正。
   - [[05_论文与概念/notes/23_Drainville2023_a_simulation_study|Drainville 2023]]：射线追踪对颅骨属性敏感性
   - [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023]]：micro-CT 相控阵聚焦验证
6. 对目标与颅骨热点建立双点传递向量，联合优化阵元幅相和旁瓣。
7. 声压场通过后，再按治疗机制输出焦点偏移、声强、温升或热剂量。

## 关联 fus-sim 文件

- `<PRIVATE_WORKSPACE>\simulate_spherical_focus.py`
- `<PRIVATE_WORKSPACE>\outputs\spherical_focus\summary.txt`
- [[MOC_虚拟仿真平台证据与复现路线]]
