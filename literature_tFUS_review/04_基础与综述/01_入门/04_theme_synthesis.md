# 主题综合：从文献到 fus-sim 复现路线

## 1. 四篇论文的共同问题

四篇中文论文看似应用不同，但核心技术链相同：

1. 颅骨会改变超声传播路径，导致声压衰减、焦点偏移和旁瓣。
2. CT/MRI 个体化建模是经颅 FUS 治疗计划的前置步骤。
3. 相位校正和幅值补偿是相控阵经颅聚焦的关键。
4. 声压场只是第一层结果，必须进一步转化为温升、[[05_论文与概念/concepts/MI|MI]]、空化或溶栓阈值。
5. 安全性判断依赖多指标：温度、[[05_论文与概念/concepts/MI|MI]]、空化谱、组织学或 MRI/影像结果。

## 2. 声场仿真文献给出的路线

[[05_论文与概念/notes/01_Treeby2010_kWave|Treeby]] 与 Cox 的 [[05_论文与概念/notes/01_Treeby2010_kWave|k-Wave]] 系列论文提供了工具和数值方法基础。[[05_论文与概念/notes/03_Leung2019_rapid_beam_simulation|Leung 2019]] 和 [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction|Jin 2020]] 更接近经颅治疗计划场景，说明快速仿真和相位校正可以作为临床参数筛选工具。

对 `fus-sim` 的启发：

- 当前轻量球面聚焦模型适合作为几何验证层。
- 下一层应是二维颅骨层模型，验证衰减和焦点偏移。
- 再下一层才是 CT 颅骨模型和三维相控阵。
- 每一步都应输出可比较指标：峰值声压、焦点位置、焦域尺寸、温升。

## 3. BBB + 微泡文献给出的路线

[[05_论文与概念/notes/07_Chen2014_BBB_pressure|Chen 2014]] 从动物实验角度证明 BBB 开放尺寸与声压/空化机制相关；[[05_论文与概念/notes/08_Hosseinkhah2015_microbubble_numerical|Hosseinkhah 2015]] 从数值模型解释声发射和血管壁应力；[[05_论文与概念/notes/09_Burgess2018_power_cavitation|Burgess 2018]] 与 [[05_论文与概念/notes/10_Kamimura2019_NHP_feedback|Kamimura 2019]] 强调空化监测和反馈控制。

对 `fus-sim` 的启发：

- 只做声压场不足以评价 BBB 开放，需要至少计算 [[05_术语表_零基础版#MI|MI]]。
- 如果后续做微泡模块，应从单微泡 [[05_术语表_零基础版#Keller-Miksis|Keller-Miksis]] 模型开始，不急于做完整血管网络。
- [[05_论文与概念/concepts/PCD|PCD]] 指标可以先做频谱分析原型：基频、次谐波、超谐波、宽带噪声。
- 安全区间应明确标注，避免把高 [[05_论文与概念/concepts/MI|MI]] 区域误解为单纯“效果更强”。

## 4. 溶栓文献给出的路线

[[05_论文与概念/notes/11_Maxwell2009_histotripsy_thrombolysis|Maxwell 2009]] 和 [[05_论文与概念/notes/12_Maxwell2011_porcine_DVT|2011]] 是孙天宇论文中溶栓声压阈值的重要外部依据。它们说明 histotripsy 的核心不是热消融，而是短高强度脉冲诱导空化云造成机械碎裂。

对 `fus-sim` 的启发：

- 溶栓仿真不能只看温升，首要目标是峰值负压是否达到空化/碎裂阈值。
- -6 MPa 和 -8 MPa 可作为初始仿真目标，但不应直接等同于临床安全阈值。
- 后续若要贴近脑血栓，需要加入血管和血栓几何，否则只能评价焦域是否具备潜在溶栓能力。

## 5. 脑肿瘤 HIFU 综述给出的路线

[[05_论文与概念/notes/28_Han2015_transcranial_brain_tumor_HIFU_review|韩珍珍 2015]] 将 CT 个体建模、相控阵、时间反转、幅值补偿、热点消除、Pennes 温度场和 MRI 温控串成完整治疗规划流程。其最直接的项目价值是为当前双点热点约束 TR 提供历史方法依据。

这篇文章是 2015 年叙述性综述，参数和临床状态必须与原始论文及近年证据交叉验证。统一路线见 [[17_四篇本地论文对虚拟平台的证据分工]]。

## 6. 推荐的复现优先级

1. 二维颅骨层声场：最快验证颅骨衰减和焦点偏移。
2. 二维热效应：复现高鹏皓论文的安全性分析。
3. 三维均匀介质小模型：验证 [[05_论文与概念/concepts/k-Wave|k-wave]]-python 的三维工作流。
4. 简化相控阵相位延迟：连接孙天宇/潘婷论文中的 82 阵元思路。
5. [[05_论文与概念/concepts/MI|MI]] 计算和 BBB 参数表：先不模拟复杂微泡群，只建立风险指标。
6. 公开 CT 数据集接入：最后处理真实颅骨个体差异。

## 关联

### 声场仿真文献
- [[05_论文与概念/notes/01_Treeby2010_kWave]] | [[05_论文与概念/notes/02_Treeby2012_nonlinear_heterogeneous]] — [[05_论文与概念/concepts/k-Wave|k-Wave]] 系列
- [[05_论文与概念/notes/03_Leung2019_rapid_beam_simulation]] — 快速仿真
- [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction]] — 相位校正
- [[MOC_声场仿真与相位校正]]

### BBB + 微泡文献
- [[05_论文与概念/notes/07_Chen2014_BBB_pressure]] — 声压与 BBB 开放
- [[05_论文与概念/notes/08_Hosseinkhah2015_microbubble_numerical]] — 微泡数值模型
- [[05_论文与概念/notes/09_Burgess2018_power_cavitation]] — 空化监测
- [[05_论文与概念/notes/10_Kamimura2019_NHP_feedback]] — NHP 反馈控制
- [[MOC_BBB微泡与空化监测]]

### 溶栓文献
- [[05_论文与概念/notes/11_Maxwell2009_histotripsy_thrombolysis]] | [[05_论文与概念/notes/12_Maxwell2011_porcine_DVT]] — Histotripsy 系列
- [[MOC_超声溶栓与Histotripsy]]

### 复现路线
- [[MOC_虚拟仿真平台证据与复现路线]] — 复现路线图
- [[03_experimental_steps]] — 实验步骤 SOP
- [[01_seed_papers_summary]] — 种子论文总结
