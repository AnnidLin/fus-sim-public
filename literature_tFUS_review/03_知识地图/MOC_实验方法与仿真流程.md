# MOC：实验方法与仿真流程

## 核心问题

tFUS 知识库里的“实验方法”重点不是记录某次实验做没做完，而是理解一类研究通常怎样提出问题、怎样建模、怎样测量、怎样判断结果是否可信。

## 仿真流程

- [[MOC_影像预处理与颅骨建模]]
- [[MOC_声场仿真与相位校正]]
- [[03_experimental_steps|实验步骤/SOP]]
- [[09_复现路线校准]]
- [[06_报告与数据/reports/历史路线/14_历史_本地论文实验步骤与输出复刻规划]]
- [[16_20250628_学术搜索补充批次]]

典型流程：

1. 明确研究对象：神经调控、BBB 开放、溶栓、Histotripsy 或热效应。
2. 准备影像和几何：[[05_论文与概念/concepts/DICOM|DICOM]]/[[05_论文与概念/concepts/NIfTI|NIfTI]]、[[05_论文与概念/concepts/影像分割|影像分割]]、[[05_论文与概念/concepts/配准|配准]]、[[05_论文与概念/concepts/CT-HU映射|CT-HU 映射]]。
3. 确定声学模型：均匀介质、简化颅骨层、CT 个体化颅骨、微泡/血管耦合。
4. 设定换能器与声束：频率、孔径、曲率半径、焦点、阵元数、相位延迟。
   - [[05_论文与概念/notes/25_Pasquinelli2020_transducer_modeling_for|Pasquinelli 2020]]：换能器建模对仿真精度的影响
5. 设定介质参数：声速、密度、衰减、非线性、热参数。
   - [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021]]：CT 参数和颅骨异质性建模
   - [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025]]：孔隙率指数声学建模
6. 输出可解释指标：声压、焦点偏移、声强、温升、[[05_论文与概念/concepts/MI|MI]]、[[05_论文与概念/concepts/PCD|PCD]] 频谱或空化风险。
   - [[05_论文与概念/notes/16_Chen2023_numerical_and_experimental|Chen 2023]]：人体颅骨声场数值与实验评估
   - [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026]]：实验交叉验证设计

## 主要方法类型

### 声场仿真

用于理解颅骨对聚焦、衰减和相位的影响。

- [[05_论文与概念/notes/01_Treeby2010_kWave|Treeby & Cox 2010 - k-Wave toolbox]]
- [[05_论文与概念/notes/02_Treeby2012_nonlinear_heterogeneous|Treeby et al. 2012 - 非线性异质介质超声传播]]
- [[05_论文与概念/notes/03_Leung2019_rapid_beam_simulation|Leung et al. 2019 - 经颅 FUS 快速声束仿真]]
- [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction|Jin et al. 2020 - 开源经颅相位校正工具]]
- [[05_论文与概念/notes/23_Drainville2023_a_simulation_study|Drainville 2023 - 射线追踪对颅骨属性的敏感性]]

### 影像预处理与颅骨建模

用于理解 CT/MRI 如何进入仿真。

- [[MOC_影像预处理与颅骨建模]]
- [[05_论文与概念/concepts/3D Slicer|3D Slicer]]
- [[05_论文与概念/concepts/FastSurfer|FastSurfer]]
- [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021 - CT 参数敏感性]]
- [[05_论文与概念/notes/13_Koh2021_acoustic_simulation_for|Koh 2021 - synthetic CT]]

### 安全性与临床规范

用于理解人体实验安全性、报告规范和临床转化路径。

- [[05_论文与概念/notes/19_Radjenovic2022_safety_of_clinical|Radjenovic 2022 - 临床超声神经调控安全性]]
- [[05_论文与概念/notes/18_Rezai2025_focused_ultrasound_neuromodulation|Rezai 2025 - FUS 神经调控治疗阿片使用障碍]]
- [[05_论文与概念/notes/15_Lee2024_a_review_of|K Lee 2024 - 人体低强度 tFUS 神经调控功能综述]]

### BBB 与空化监测

用于理解微泡、安全窗口、稳定空化与惯性空化。

- [[MOC_BBB微泡与空化监测]]
- [[05_论文与概念/notes/07_Chen2014_BBB_pressure|Chen & Konofagou 2014 - 声压决定 BBB 开放尺寸]]
- [[05_论文与概念/notes/09_Burgess2018_power_cavitation|Burgess et al. 2018 - 功率空化成像引导 BBB 开放]]
- [[02_大鼠BBB实验/02_实验文献/29_Rodriguez2023_rat_BBB_protocol|Rodríguez et al. 2023 - 大鼠短时 BBB 开放实验协议]]
- [[02_大鼠BBB实验/02_实验文献/30_Park2021_rat_BBB_validation|Park et al. 2021 - 人颅骨平台大鼠 BBB 破坏验证]]

### 溶栓与 Histotripsy

用于理解高强度机械效应、组织破坏阈值和血栓处理。

- [[MOC_超声溶栓与Histotripsy]]
- [[05_论文与概念/notes/11_Maxwell2009_histotripsy_thrombolysis]]
- [[05_论文与概念/notes/12_Maxwell2011_porcine_DVT]]

## 阅读时关注

- 研究是在做仿真、体外实验、动物实验还是人体研究？
  - [[05_论文与概念/notes/15_Lee2024_a_review_of|K Lee 2024]]：人体证据分层
- 结果是声学指标、热指标、生物效应，还是安全指标？
- 参数是 source、free-field、in situ，还是文中未说明？
- 方法能否迁移到另一类 tFUS 问题，还是只适用于原论文场景？
- 建模策略是否经过实验验证？
  - [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026]]：交叉验证方法论
  - [[05_论文与概念/notes/16_Chen2023_numerical_and_experimental|Chen 2023]]：数值+实验对比
