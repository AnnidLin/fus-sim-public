# MOC：超声溶栓与 Histotripsy

## 核心问题

超声溶栓路线关注短高强度脉冲诱导的机械空化和组织碎裂效应，重点指标是峰值负压、空化云、焦域范围、温升和血管安全性。

## 本地论文

- [[01_seed_papers_summary#3 孙天宇 2021经颅聚焦超声治疗脑血栓的数值仿真研究|孙天宇 2021]]

## 外部论文

- [[notes/11_Maxwell2009_histotripsy_thrombolysis|Maxwell et al. 2009 - 体外 histotripsy 溶栓]]
- [[notes/12_Maxwell2011_porcine_DVT|Maxwell et al. 2011 - 猪 DVT 模型 histotripsy 溶栓]]

## 关键参数

- 溶栓效果初始阈值：约 -6 MPa。
- 显著溶栓初始阈值：约 -8 MPa。
- 孙天宇论文建议重点频段：0.7-0.9 MHz。
- 经颅达到同样负压所需功率约高于开颅条件。

## 可复现实验链

1. 均匀脑组织模型声压阈值扫描。
2. 经颅/开颅模型对比。
3. 频率和输入声功率扫描。
4. 占空比和辐照时间温升评估。
5. 后续加入血管和血栓几何。

