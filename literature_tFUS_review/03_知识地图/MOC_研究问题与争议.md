# MOC：研究问题与争议

## 核心问题

这张 MOC 用来收集 tFUS 领域里值得反复追问的问题：哪些已经比较清楚，哪些还依赖具体场景，哪些在文献中存在不同处理方式。

## 研究问题

### 经颅声场

- 颅骨造成的声压衰减和焦点偏移能否被稳定校正？
- 单纯相位校正后仍存在远端颅骨热点时，目标/热点双点时间反转能否在保留 ROI 覆盖的同时稳定压低二次峰？
  - [[05_论文与概念/notes/28_Han2015_transcranial_brain_tumor_HIFU_review|韩珍珍 2015]] 回溯 Leduc 2012 的迭代热点消除路线；当前 fus-sim 已实现复数投影版本，但尚无热点校准压力证据。
- 如何从单体素焦点升级为解剖结构 ROI，并联合优化覆盖率、颅骨热点、非靶区暴露和剂量？

- CT 个体化建模相对简化颅骨模型带来多少收益？
  - [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021]]：异质颅骨模型显著优于均质模型，CT 参数选择（HU 阈值、层厚、重建核）直接影响精度。
- 相位校正应该优先使用[[05_论文与概念/concepts/时间反转|时间反转]]、ray-based 方法，还是其他近似方法？
  - [[05_论文与概念/notes/23_Drainville2023_a_simulation_study|Drainville 2023]]：射线追踪对颅骨属性（声速、密度）高度敏感，需评估近似方法适用范围。
- **CT 参数选择（HU 阈值、层厚、重建核）对仿真精度的影响范围？**
  - [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021]]：不同 CT 参数选择导致声学属性差异，需建立参数敏感性门控。
- **真实松质骨结构 vs 简化 CT 映射的声场差异？**
  - [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025]]：3D 真实松质骨模型的相控阵聚焦数值研究表明结构细节影响焦域分布。
- **micro-CT 分辨率下的颅骨声学模型 vs 临床 CT 分辨率？**
  - [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023]]：micro-CT 相控阵聚焦验证，但临床分辨率（1-3 mm）下细节丢失的影响尚未量化。
- **影像预处理误差会怎样传递到声场结果？**
  - [[MOC_影像预处理与颅骨建模]]：分割、配准、CT-HU 映射和 synthetic CT 都属于声场仿真前的误差来源。
- **FastSurfer / 3D Slicer 是否属于当前项目主线？**
  - 目前更稳妥的表述是：[[05_论文与概念/concepts/3D Slicer|3D Slicer]] 可能用于影像预处理；[[05_论文与概念/concepts/FastSurfer|FastSurfer]] 可能用于 MRI 脑结构分割；二者尚未进入当前 `fus-sim` 正式流程。

关联入口：

- [[MOC_影像预处理与颅骨建模]]
- [[MOC_声场仿真与相位校正]]
- [[05_论文与概念/notes/03_Leung2019_rapid_beam_simulation]]
- [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction]]
- [[05_论文与概念/notes/14_Montanaro2021_the_impact_of]]
- [[05_论文与概念/notes/23_Drainville2023_a_simulation_study]]
- [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing]]
- [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused]]
- [[05_论文与概念/notes/25_Pasquinelli2020_transducer_modeling_for]]
- [[05_论文与概念/notes/26_Kong2025_a_novel_method]]
- [[05_论文与概念/notes/27_Li2026_experimental_validation_of]]
- [[05_论文与概念/notes/24_Dagommer2024_robust_deep_learning]]

### 神经调控

- 低强度 tFUS 的主要作用机制是机械效应、热效应，还是二者共同参与？
- 频率、脉冲模式和靶区差异怎样影响神经反应？
- 人体研究中的剂量报告是否足够可比较？
  - [[05_论文与概念/notes/15_Lee2024_a_review_of|K Lee 2024]]：人体低强度 tFUS 参数差异大（频率 0.2-0.7 MHz，声压 0.1-1.0 MPa），protocol 不统一。
- **人体 vs 动物实验证据的可迁移性？**
  - [[05_论文与概念/notes/15_Lee2024_a_review_of|K Lee 2024]]：人体证据强度弱于动物，但低频（<500 kHz）穿透力在动物和人体间表现不同。
- **不同实验参数（频率、声压、PRF）的人体研究证据分层？**
  - [[05_论文与概念/notes/15_Lee2024_a_review_of|K Lee 2024]]：现有 RCT 和伪实验混合，需要系统化评估。
- **溶栓/BBB 的声压阈值（-6/-8 MPa）能否直接迁移为神经调控安全上限？**
  - [[05_论文与概念/notes/20_Javid2023_a_review_of|Javid 2023]]：超声神经调控技术综述，但参数范围过于宽泛，不能直接作为安全基准。

关联入口：

- [[05_论文与概念/notes/05_Legon2014_human_somatosensory]]
- [[05_论文与概念/notes/06_Stern2021_TLE_safety]]
- [[10_学习型论文阅读路线]]
- [[05_论文与概念/notes/15_Lee2024_a_review_of]]
- [[05_论文与概念/notes/16_Chen2023_numerical_and_experimental]]
- [[05_论文与概念/notes/20_Javid2023_a_review_of]]
- [[MOC_安全性与临床神经调控]]

### BBB 与微泡

- 有效开放 BBB 与避免损伤之间的安全窗口如何定义？
- [[05_论文与概念/concepts/MI|MI]]、[[05_论文与概念/concepts/PCD|PCD]] 频谱和实际组织效应之间如何对应？
- 微泡半径、浓度和注射时序是否能形成统一参数框架？

关联入口：

- [[MOC_BBB微泡与空化监测]]
- [[05_论文与概念/notes/07_Chen2014_BBB_pressure]]
- [[05_论文与概念/notes/08_Hosseinkhah2015_microbubble_numerical]]
- [[05_论文与概念/notes/10_Kamimura2019_NHP_feedback]]

### 溶栓与 Histotripsy

- 溶栓场景中机械破坏、空化和药物/微泡协同如何区分？
- Histotripsy 的阈值和低强度 neuromodulation 的安全语言能否共用？
- 体外、动物和临床转化之间最大的参数断点是什么？

关联入口：

- [[MOC_超声溶栓与Histotripsy]]
- [[05_论文与概念/notes/11_Maxwell2009_histotripsy_thrombolysis]]
- [[05_论文与概念/notes/12_Maxwell2011_porcine_DVT]]

## 争议记录方式

新建争议笔记时，建议回答四件事：

- 问题是什么？
- 不同论文分别怎么处理？
- 分歧来自参数定义、模型假设、实验对象，还是测量方式？
- 目前最稳妥的表述是什么？
