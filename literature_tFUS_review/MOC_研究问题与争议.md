# MOC：研究问题与争议

## 核心问题

这张 MOC 用来收集 tFUS 领域里值得反复追问的问题：哪些已经比较清楚，哪些还依赖具体场景，哪些在文献中存在不同处理方式。

## 研究问题

### 经颅声场

- 颅骨造成的声压衰减和焦点偏移能否被稳定校正？
- CT 个体化建模相对简化颅骨模型带来多少收益？
- 相位校正应该优先使用时间反转、ray-based 方法，还是其他近似方法？

关联入口：

- [[MOC_声场仿真与相位校正]]
- [[notes/03_Leung2019_rapid_beam_simulation]]
- [[notes/04_Jin2020_open_source_phase_correction]]

### 神经调控

- 低强度 tFUS 的主要作用机制是机械效应、热效应，还是二者共同参与？
- 频率、脉冲模式和靶区差异怎样影响神经反应？
- 人体研究中的剂量报告是否足够可比较？

关联入口：

- [[notes/05_Legon2014_human_somatosensory]]
- [[notes/06_Stern2021_TLE_safety]]
- [[10_学习型论文阅读路线]]

### BBB 与微泡

- 有效开放 BBB 与避免损伤之间的安全窗口如何定义？
- MI、PCD 频谱和实际组织效应之间如何对应？
- 微泡半径、浓度和注射时序是否能形成统一参数框架？

关联入口：

- [[MOC_BBB微泡与空化监测]]
- [[notes/07_Chen2014_BBB_pressure]]
- [[notes/08_Hosseinkhah2015_microbubble_numerical]]
- [[notes/10_Kamimura2019_NHP_feedback]]

### 溶栓与 Histotripsy

- 溶栓场景中机械破坏、空化和药物/微泡协同如何区分？
- Histotripsy 的阈值和低强度 neuromodulation 的安全语言能否共用？
- 体外、动物和临床转化之间最大的参数断点是什么？

关联入口：

- [[MOC_超声溶栓与Histotripsy]]
- [[notes/11_Maxwell2009_histotripsy_thrombolysis]]
- [[notes/12_Maxwell2011_porcine_DVT]]

## 争议记录方式

新建争议笔记时，建议回答四件事：

- 问题是什么？
- 不同论文分别怎么处理？
- 分歧来自参数定义、模型假设、实验对象，还是测量方式？
- 目前最稳妥的表述是什么？
