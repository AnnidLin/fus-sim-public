# MOC：声场仿真与相位校正

## 核心问题

经颅聚焦超声仿真的关键在于：颅骨导致声束畸变、声压衰减和焦点偏移，因此需要 CT 建模、介质参数映射、换能器定位和相位校正。

## 本地论文

- [[01_seed_papers_summary#1 高鹏皓 2022经颅聚焦超声调控系统的参数仿真研究|高鹏皓 2022]]
- [[01_seed_papers_summary#3 孙天宇 2021经颅聚焦超声治疗脑血栓的数值仿真研究|孙天宇 2021]]

## 外部论文

- [[notes/01_Treeby2010_kWave|Treeby & Cox 2010 - k-Wave toolbox]]
- [[notes/02_Treeby2012_nonlinear_heterogeneous|Treeby et al. 2012 - 非线性异质介质超声传播]]
- [[notes/03_Leung2019_rapid_beam_simulation|Leung et al. 2019 - 经颅 FUS 快速声束仿真]]
- [[notes/04_Jin2020_open_source_phase_correction|Jin et al. 2020 - 开源经颅相位校正工具]]

## 可复现实验链

1. 均匀水介质聚焦声场。
2. 二维简化颅骨层。
3. CT 颅骨参数映射。
4. 目标点与候选换能器点阵。
5. 时间反转或 ray-based 相位校正。
6. 声压场、焦点偏移、温升输出。

## 关联 fus-sim 文件

- `D:\AIprogram\fus-sim\simulate_spherical_focus.py`
- `D:\AIprogram\fus-sim\outputs\spherical_focus\summary.txt`
- [[MOC_fus-sim复现路线]]

