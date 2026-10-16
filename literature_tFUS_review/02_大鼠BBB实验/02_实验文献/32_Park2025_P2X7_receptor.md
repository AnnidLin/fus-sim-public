---
type: paper
status: verified-fulltext
theme: BBB_mechanism_P2X7
doi: 10.1038/s41598-024-83913-3
pmid: 39762398
pmcid: PMC11704064
year: 2025
tags:
  - BBB
  - low-intensity-FUS
  - P2X7
  - mechanism
  - rat
  - SD
fulltext: verified
---

# Park et al. 2025 - P2X7 受体在 FUS 诱导 BBB 调节中的作用

> [!note] 全文已核对
> 参数来自 PMC11704064 全文/摘要 XML（已核验）。

## 基本信息

- 题名：Role of P2X7 receptor during focused ultrasound induced blood brain barrier modulation
- 作者年份：Park J, Na YC, ..., Chang WS, 2025
- 期刊：Scientific Reports, 2025
- DOI：10.1038/s41598-024-83913-3
- PMID：39762398 / PMCID：PMC11704064
- 链接：https://pubmed.ncbi.nlm.nih.gov/39762398/

- 本机原文：[[02_大鼠BBB实验/03_原文PDF/32_Park2025_P2X7_receptor.pdf]]（开放获取，PMC11704064）
## 一句话总结

用低强度聚焦超声（LiFUS）+ 微泡开放大鼠 BBB，证明 **P2X7 嘌呤受体**及 NLRP3/IL-1β 通路参与其中，提示超声开放 BBB 不只是物理效应，还涉及受体介导的生物学过程。

## 研究目的

阐明 P2X7 受体是否及如何参与 LiFUS 诱导的 BBB 通透性改变及其下游炎症信号。

## 实验/仿真对象

- **动物**：Sprague-Dawley（SD）大鼠，经颅 LiFUS 开放 BBB（海马区）

## 设备、软件或方程模型

- **换能器**：**0.5 MHz** 换能器置于颅骨上
- **信号链**：波形发生器（33220A，Agilent）→ 功率放大器（240L，ENI Inc.）→ 耦合器（Pulsar C30-102）
- **麻醉**：腹腔注射 ketamine cocktail（75 mg/kg ketamine + 4 mg/kg xylazine + 0.75 mg/kg acepromazine + 0.9% 盐水）
- **检测**：western blot、RT-PCR、IHC、Evans blue 分光光度法、TUNEL、H&E

## 数据来源与预处理

LiFUS 超声后不同时间点（含 1 h 关键点）取材，量化 P2X7/NLRP3/IL-1β/ZO-1/occludin 表达与 EB 通透性。

## 参数设置（全文确认）

- **频率**：0.5 MHz
- **声压**：**0.3 MPa**
- **模式**：低强度聚焦超声 + 微泡（LiFUS + microbubbles）
- **观察时间点**：含超声后 **1 h**（P2X7↑、紧密连接蛋白↓）

## 实验步骤

1. SD 大鼠麻醉；
2. 0.5 MHz 换能器置于颅骨，LiFUS（0.3 MPa）+ 微泡辐照，开放 BBB（MRI T1 确认）；
3. 不同时间点取材；
4. western blot/RT-PCR 测 P2X7、NLRP3、IL-1β、ZO-1、occludin；
5. EB 分光光度法定量通透性；IHC 观察 P2X7/RECA-1；
6. TUNEL + H&E 评估细胞损伤与凋亡；
7. 施加 P2X7 拮抗剂验证其作用。

## 结果指标

- P2X7 及其下游信号（NLRP3、IL-1β）
- 紧密连接蛋白 ZO-1、occludin 表达
- EB 外渗量（通透性）
- 细胞凋亡/损伤（TUNEL、H&E）
- ATP 水平

## 关键结论（全文确认）

- LiFUS + 微泡开放 BBB **1 h 后** P2X7 及下游信号显著上调；紧密连接蛋白表达最低；
- P2X7 受体参与、可被拮抗剂调节；
- 无明确细胞死亡信号，LiFUS 在安全条件下可逆调节 BBB。

## 安全性与局限

- 关注超声后水肿/损伤监测；
- 能量传递受颅骨个体影响；样本与机制细节仍需更多验证。

## 对本大鼠实验的启发

提示 BBB 开放判读除 EB 外还可包含受体、炎症与紧密连接蛋白等生物学终点，为本地实验未来是否增加机制性检测提供参考。

## 关联

- [[MOC_BBB微泡与空化监测]] | [[MOC_研究问题与争议]]
- 术语：[[05_术语表_零基础版]]

## 同主题横向互链

- [[07_Chen2014_BBB_pressure]] — 声压决定 BBB 开放尺寸
- [[02_大鼠BBB实验/02_实验文献/29_Rodriguez2023_rat_BBB_protocol]] — 大鼠短时 BBB 协议
- [[02_大鼠BBB实验/02_实验文献/30_Park2021_rat_BBB_validation]] — 人颅骨大鼠 BBB 验证
