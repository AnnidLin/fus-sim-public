# MOC：实验方法与仿真流程

## 核心问题

tFUS 知识库里的“实验方法”重点不是记录某次实验做没做完，而是理解一类研究通常怎样提出问题、怎样建模、怎样测量、怎样判断结果是否可信。

## 仿真流程

- [[MOC_声场仿真与相位校正]]
- [[03_experimental_steps|实验步骤/SOP]]
- [[09_复现路线校准]]
- [[14_本地论文实验步骤与输出复刻规划]]

典型流程：

1. 明确研究对象：神经调控、BBB 开放、溶栓、Histotripsy 或热效应。
2. 确定声学模型：均匀介质、简化颅骨层、CT 个体化颅骨、微泡/血管耦合。
3. 设定换能器与声束：频率、孔径、曲率半径、焦点、阵元数、相位延迟。
4. 设定介质参数：声速、密度、衰减、非线性、热参数。
5. 输出可解释指标：声压、焦点偏移、声强、温升、MI、PCD 频谱或空化风险。

## 主要方法类型

### 声场仿真

用于理解颅骨对聚焦、衰减和相位的影响。

- [[notes/01_Treeby2010_kWave|Treeby & Cox 2010 - k-Wave toolbox]]
- [[notes/02_Treeby2012_nonlinear_heterogeneous|Treeby et al. 2012 - 非线性异质介质超声传播]]
- [[notes/03_Leung2019_rapid_beam_simulation|Leung et al. 2019 - 经颅 FUS 快速声束仿真]]
- [[notes/04_Jin2020_open_source_phase_correction|Jin et al. 2020 - 开源经颅相位校正工具]]

### BBB 与空化监测

用于理解微泡、安全窗口、稳定空化与惯性空化。

- [[MOC_BBB微泡与空化监测]]
- [[notes/07_Chen2014_BBB_pressure|Chen & Konofagou 2014 - 声压决定 BBB 开放尺寸]]
- [[notes/09_Burgess2018_power_cavitation|Burgess et al. 2018 - 功率空化成像引导 BBB 开放]]

### 溶栓与 Histotripsy

用于理解高强度机械效应、组织破坏阈值和血栓处理。

- [[MOC_超声溶栓与Histotripsy]]
- [[notes/11_Maxwell2009_histotripsy_thrombolysis]]
- [[notes/12_Maxwell2011_porcine_DVT]]

## 阅读时关注

- 研究是在做仿真、体外实验、动物实验还是人体研究？
- 结果是声学指标、热指标、生物效应，还是安全指标？
- 参数是 source、free-field、in situ，还是文中未说明？
- 方法能否迁移到另一类 tFUS 问题，还是只适用于原论文场景？
