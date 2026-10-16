---
type: paper
status: verified-fulltext
theme: BBB_validation
doi: 10.3390/brainsci11111429
pmid: 34827428
pmcid: PMC8615862
year: 2021
tags:
  - BBB
  - rat
  - SD
  - human-skull
  - validation
  - focused-ultrasound
  - cavitation
fulltext: verified
---

# Park et al. 2021 - 基于人颅骨的临床验证平台大鼠 BBB 破坏验证

> [!note] 全文已核对
> 参数来自 PMC8615862 全文 XML（已核验）。

## 基本信息

- 题名：Verification of Blood-Brain Barrier Disruption Based on the Clinical Validation Platform Using a Rat Model with Human Skull
- 作者年份：Park CY, Seo H, ..., Park J, 2021
- 期刊：Brain Sciences, 2021
- DOI：10.3390/brainsci11111429
- PMID：34827428 / PMCID：PMC8615862
- 链接：https://pubmed.ncbi.nlm.nih.gov/34827428/

- 本机原文：[[02_大鼠BBB实验/03_原文PDF/30_Park2021_rat_BBB_validation.pdf]]（开放获取，PMC8615862）
## 一句话总结

用"**人颅骨片 + 大鼠**"建立临床前验证平台，通过 MRI 与空化剂量比较自由场与经人颅骨的 BBBD，用于推导临床 FUS 参数。

## 研究目的

搭建临床前验证平台，获取适合临床试验的 FUS 参数，并预测临床结果——解决小动物经颅结果难以外推到人体的难题。

## 实验/仿真对象

- **动物**：20 只雄性 Sprague-Dawley（SD）大鼠，8 周龄，300±30 g（Koatech，韩国）
- **人颅骨**：成人男性颅骨片 120.54 × 36.53 × 75.55 mm，平均厚 **5.45 mm**
- **仿真**：250 kHz 球面单阵元 FUS，SD 大鼠 micro-CT 提取颅骨 3D 图，颅骨内外声场仿真

## 设备、软件或方程模型

- **换能器**：球面弯曲孔径，中心频率 **250 kHz**；直径 80 mm；焦距 100 mm；**f-number 1.2**
- **FUS 系统**：NS-US200（NEUROSONA，韩国），含空化声发射采集
- **MRI**：3.0 T（Skyra，Siemens），T1 增强 + SWI（磁敏感加权成像）
- **麻醉**：Zoletil 25 mg/kg + Rumpun 4.6 mg/kg
- **统计分析**：SPSS 21.0

## 数据来源与预处理

通过水听器测量经人颅骨的衰减率，对输入参数进行衰减补偿；空化信号经 FFT 频谱化，计算稳定/惯性空化剂量。

## 参数设置（全文确认）

- **频率**：250 kHz（换能器中心频率）
- **靶点**：右侧尾壳核（right caudate putamen, CP）
- **辐照时长**：微泡存在下 sonication **90 s**
- **输入参数**：
  - 自由场（无人颅骨）：**300 mVpp**
  - 人颅骨：**700 mVpp**（补偿颅骨衰减）
- 对比基础：1 MHz FUS 先前研究测得的 0.7 MPa 安全 BBBD 压力点
- 微泡向目标区推注观察空化（谐波）约 120 s

## 实验步骤

1. SD 大鼠麻醉、MRI/固定；
2. 在靶点（右 CP）施加 FUS + 稀释微泡 90 s，分自由场与人颅骨两组；
3. 同步采集空化声发射（FFT→频谱→空化剂量）；
4. 3.0T MRI（T1 增强、SWI）评估 BBB 开放与出血；
5. BBBD 后 4 h 取材，H&E 组织学（5 μm 切片）；
6. micro-CT + 声学仿真验证经颅声场。

## 结果指标

- BBB 开放（MRI T1 增强、EB）
- 空化剂量：稳定空化 SCDh（谐波）/SCDu（超谐波）、惯性空化 ICD
- 组织学损伤（外渗红细胞）

## 关键结论

- 人颅骨使 SCDh、SCDu 相比自由场**下降 13.6、5.3 倍**；ICD 略升（1.05 倍）；
- 经颅需显著提高输入功率（300→700 mVpp）补偿衰减；
- 用 MRI/EB/组织学 + 空化剂量综合确认 BBBD。

## 安全性与局限

- 人颅骨衰减强、且引起显著加热与外渗风险；
- 样本量有限，需更多研究；
- 250 kHz 为低频，利于穿透但焦点精度受限。

## 对本大鼠实验的启发

为经颅衰减处理和 MRI/EB/空化验证终点提供方法参考。由于颅骨、换能器、动物与测量量均不一致，本研究不能直接验证 Case 079 或虚拟平台；未来只有在协议和可比较终点预先对齐后，才能作为独立实验比较来源。

## 关联

- [[MOC_实验方法与仿真流程]] | [[MOC_BBB微泡与空化监测]] | [[MOC_声场仿真与相位校正]]
- 术语：[[05_术语表_零基础版]]

## 同主题横向互链

- [[02_大鼠BBB实验/02_实验文献/29_Rodriguez2023_rat_BBB_protocol]] — 大鼠短时 BBB 开放协议
- [[07_Chen2014_BBB_pressure]] — 声压决定 BBB 开放尺寸
- [[09_Burgess2018_power_cavitation]] — 空化监测/引导
