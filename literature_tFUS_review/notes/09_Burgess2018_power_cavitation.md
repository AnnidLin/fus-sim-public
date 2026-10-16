# Burgess et al. 2018 - 功率空化成像引导 BBB 开放

## 基本信息

- 题名：Power cavitation-guided blood-brain barrier opening with focused ultrasound and microbubbles
- 期刊：Physics in Medicine & Biology, 2018
- DOI：10.1088/1361-6560/aab05c
- PMID：29457587
- PMCID：PMC5881390
- 来源：https://pubmed.ncbi.nlm.nih.gov/29457587/

## 研究目的

提出 power cavitation imaging，用于高分辨率监测 FUS + 微泡诱导的空化活动，并与 BBB 开放区域对应。

## 实验/仿真对象

FUS + 微泡 BBB 开放动物实验模型。

## 设备或软件

- FUS 发射。
- 被动接收阵列。
- Delay-and-sum beamforming。
- Power cavitation image 计算。

## 数据来源与预处理

采集 FUS 脉冲期间的被动空化信号，并同步 FUS 发射与接收时间。

## 参数设置

PubMed 摘要确认该研究使用短脉冲 FUS，以限制声发射持续时间并提高轴向分辨率。

## 实验步骤

1. 准备 FUS + 微泡 BBB 开放实验模型。
2. 同步 FUS transmit 与 passive receive acquisition。
3. 使用短脉冲 FUS 激发微泡空化。
4. 对被动接收信号使用绝对时间延迟的 delay-and-sum beamforming。
5. 生成高帧率 cavitation image。
6. 计算随时间平均的 power cavitation image。
7. 将空化图像与 BBB 开放区域比较。

## 结果指标

- 空化图像空间分辨率。
- Power cavitation intensity。
- BBB 开放区域。

## 安全性与局限

该方法强调监控和引导，但具体安全阈值仍需结合 MRI、组织学或其他终点判断。

## 与 fus-sim 的衔接

为未来 PCD/空化定位提供可实现算法思路：先从频谱指标开始，再做被动阵列定位。

