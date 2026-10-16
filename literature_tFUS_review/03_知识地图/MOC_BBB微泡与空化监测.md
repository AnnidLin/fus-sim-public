# MOC：BBB 微泡与空化监测

> [!important] 共享主题，不是同一项目线
> 本页汇总 BBB、微泡与空化监测的通用知识，同时服务于 [[18_虚拟平台_BBB个体化规划应用设想|虚拟平台应用设想]] 和 [[02_大鼠BBB实验/00_大鼠BBB实验入口|大鼠 BBB 湿实验]]。两条线路只共享文献概念，不直接共享剂量、进度或验证结论。

## 核心问题

FUS 联合微泡开放 BBB 的关键不是单纯追求更高声压，而是在有效开放和组织损伤之间找到安全窗口。[[05_论文与概念/concepts/MI|MI]]、稳定空化、惯性空化和 [[05_论文与概念/concepts/PCD|PCD]] 频谱是主要判断指标。

## 本地论文

- [[01_seed_papers_summary#2 潘婷 2021经颅聚焦超声联合微泡开放血脑屏障的数值仿真研究|潘婷 2021]]

## 外部论文

- [[05_论文与概念/notes/07_Chen2014_BBB_pressure|Chen & Konofagou 2014 - 声压决定 BBB 开放尺寸]]
- [[05_论文与概念/notes/08_Hosseinkhah2015_microbubble_numerical|Hosseinkhah et al. 2015 - 微泡、声发射与血管壁应力数值模型]]
- [[05_论文与概念/notes/09_Burgess2018_power_cavitation|Burgess et al. 2018 - 功率空化成像引导 BBB 开放]]
- [[05_论文与概念/notes/10_Kamimura2019_NHP_feedback|Kamimura et al. 2019 - 非人灵长类 BBB 开放反馈控制]]
- [[02_大鼠BBB实验/02_实验文献/29_Rodriguez2023_rat_BBB_protocol|Rodríguez et al. 2023 - 大鼠短时 BBB 开放协议]]（方法学首选）
- [[02_大鼠BBB实验/02_实验文献/30_Park2021_rat_BBB_validation|Park et al. 2021 - 人颅骨平台大鼠 BBB 破坏验证]]
- [[02_大鼠BBB实验/02_实验文献/32_Park2025_P2X7_receptor|Park et al. 2025 - P2X7 受体与 FUS BBB 调节]]
- [[02_大鼠BBB实验/02_实验文献/36_Song2017_microbubble_gas_volume|Song et al. 2017 - 微泡气体体积统一剂量参数（EB 定量）]]
- [[02_大鼠BBB实验/02_实验文献/37_Yang2012_BTB_pulsedFUS|Yang et al. 2012 - 1 MHz 脉冲 FUS 增强胶质瘤 BTB 渗透]]

## 关键参数

- 频率：常见 0.2-0.7 MHz，经颅低频有利于穿透颅骨。
- [[05_论文与概念/concepts/MI|MI]]：潘婷论文的 `0.3 <= MI <= 0.7` 只能作为本地模型种子范围，不是跨微泡、设备、物种或患者通用的安全窗口。
- 微泡半径：潘婷论文中约 6 um 时 MImax 较大。
- 微泡密度：潘婷论文中不大于 `1.56 x 10^10 / m^3` 是安全有效参考条件之一。
- [[05_论文与概念/concepts/PCD|PCD]] 指标：次谐波、超谐波、宽带噪声。

## 可复现实验链

1. 单微泡 Keller-Miksis 模型。
2. 频率、声压、半径、脉冲宽度参数扫描。
3. 简化血管中的 [[05_论文与概念/concepts/MI|MI]] 分布。
4. [[05_论文与概念/concepts/PCD|PCD]] 频谱模拟或后处理。
5. 患者 CT/MRI 上的声学代价路径排名和 ROI 覆盖。
6. PCD/AE 闭环调节与宽带风险停止规则。
7. MRI 对比增强开放体积与损伤指标验证。

## 患者级闭环证据

- 972 次患者 sonication 的声发射剂量与 BBB 开放关联：<https://pubmed.ncbi.nlm.nih.gov/41395575/>。
- 9 名胶质母细胞瘤患者、38 次治疗的次谐波反馈控制：<https://pubmed.ncbi.nlm.nih.gov/38897294/>。
- 10 名胶质瘤患者的设备、耦合和治疗过程声学 QA：<https://pubmed.ncbi.nlm.nih.gov/38531173/>。

## 关联 MOC

- [[MOC_参数与指标]] — 声压阈值、[[05_论文与概念/concepts/MI|MI]] 定义
- [[MOC_研究问题与争议]] — BBB 安全窗口争议
- [[MOC_安全性与临床神经调控]] — [[05_论文与概念/concepts/MI|MI]] 安全阈值
- [[MOC_实验方法与仿真流程]] — BBB 开放实验方法
