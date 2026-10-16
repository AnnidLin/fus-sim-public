# MOC：BBB 微泡与空化监测

## 核心问题

FUS 联合微泡开放 BBB 的关键不是单纯追求更高声压，而是在有效开放和组织损伤之间找到安全窗口。MI、稳定空化、惯性空化和 PCD 频谱是主要判断指标。

## 本地论文

- [[01_seed_papers_summary#2 潘婷 2021经颅聚焦超声联合微泡开放血脑屏障的数值仿真研究|潘婷 2021]]

## 外部论文

- [[notes/07_Chen2014_BBB_pressure|Chen & Konofagou 2014 - 声压决定 BBB 开放尺寸]]
- [[notes/08_Hosseinkhah2015_microbubble_numerical|Hosseinkhah et al. 2015 - 微泡、声发射与血管壁应力数值模型]]
- [[notes/09_Burgess2018_power_cavitation|Burgess et al. 2018 - 功率空化成像引导 BBB 开放]]
- [[notes/10_Kamimura2019_NHP_feedback|Kamimura et al. 2019 - 非人灵长类 BBB 开放反馈控制]]

## 关键参数

- 频率：常见 0.2-0.7 MHz，经颅低频有利于穿透颅骨。
- MI：常用安全有效区间可先按 `0.3 <= MI <= 0.7` 建模。
- 微泡半径：潘婷论文中约 6 um 时 MImax 较大。
- 微泡密度：潘婷论文中不大于 `1.56 x 10^10 / m^3` 是安全有效参考条件之一。
- PCD 指标：次谐波、超谐波、宽带噪声。

## 可复现实验链

1. 单微泡 Keller-Miksis 模型。
2. 频率、声压、半径、脉冲宽度参数扫描。
3. 简化血管中的 MI 分布。
4. PCD 频谱模拟或后处理。
5. BBB 开放风险分区图。

