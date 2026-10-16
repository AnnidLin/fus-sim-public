---
type: paper
status: verified-fulltext
theme: BBB_microbubble_dose
doi: 10.7150/thno.15411
pmid: 28042323
pmcid: PMC5196892
year: 2017
tags:
  - BBB
  - rat
  - SD
  - microbubble
  - Evans-blue
  - gas-volume
  - dose-response
fulltext: verified
---

# (Theranostics 2017) - 微泡气体体积：FUS 开放 BBB 的统一剂量参数

> [!note] 全文已核对
> 参数来自 PMC5196892 全文 XML（已核验）。

## 基本信息

- 题名：Microbubble gas volume: A unifying dose parameter in blood-brain barrier opening by focused ultrasound
- 作者年份：Song KH, Fan AC, ..., 2017
- 期刊：Theranostics, 2017
- DOI：10.7150/thno.15411
- PMID：28042323 / PMCID：PMC5196892
- 链接：https://pubmed.ncbi.nlm.nih.gov/28042323/

- 本机原文：[[02_大鼠BBB实验/03_原文PDF/36_Song2017_microbubble_gas_volume.pdf]]（开放获取，PMC5196892）
## 一句话总结

证明**微泡气体体积剂量**（=平均微泡体积 × 微泡数）能统一预测 FUS 开放 BBB 的程度——EB 外渗随气体体积剂量**线性增加**，且 2µm/6µm 两种微泡尺寸数据落在同一条线上。**是 EB 定量 + 微泡剂量方法学的核心参考。**

## 研究目的

独立考察微泡**尺寸（2 vs 6 µm）**与**浓度**对 FUS-BBB 开放的影响，验证"气体体积剂量"能否统一两种尺寸的结果。

## 实验/仿真对象

- **动物**：33 只成年雄性 **Sprague-Dawley（SD）大鼠**，300–400 g，13–15 周龄
- **靶区**：纹状体（striatum，先右后左，各超声 5 min）

## 设备、软件或方程模型

- **换能器**：Therapy Imaging Probe System（**TIPS**，Philips）
- **微泡**：尺寸分离的**阳离子 MB**（Advanced Microbubble Laboratories），直径 **2µm 与 6µm**，壳组分 70 mol%
- **微泡表征**：显微镜 + Coulter 计数
- **EB 定量**：Odyssey 扫描仪 + **ImageJ**（NIH）叠加 5 片 400 µm 脑片量化荧光
- **病毒递送**：dsAAV1-CMV-eGFP（50 µL，3.38×10¹² vg）

## 数据来源与预处理

单次静脉注射 MB/EB 混合液后，先右纹状体超声 5 min，再左纹状体 5 min；取 5 片 400 µm 脑切片，Odyssey + ImageJ 量化 EB 荧光。

## 参数设置（全文确认）

- **微泡剂量**：气体体积剂量范围 **1–40 µL/kg**；基准 20 µL 的 6µm（**2×10⁸ MB/kg**）
- **微泡尺寸**：2 µm vs 6 µm（阳离子脂质壳 70 mol%）
- **频率**：FUS（具体 MHz 以正文为准，TIPS 系统常用 ~2 MHz 或更低）
- **超声时长**：每侧纹状体 5 min
- **EB**：2 wt% Evans blue，尾静脉注射

## 实验步骤

1. 尾静脉注射 MB（2×10⁸ MB/kg）+ EB 混合液；
2. 右纹状体 FUS 超声 5 min，再左纹状体 5 min；
3. 深麻醉、肝素化生理盐水经心灌注；
4. 取 5 片 400 µm 脑片覆盖纹状体；
5. Odyssey 扫描 + ImageJ 叠加量化 EB 荧光；
6. 比较不同微泡尺寸/气体体积剂量下的 EB 外渗。

## 结果指标

- EB 外渗量（荧光）—— BBB 开放程度
- EB 剂量-反应线性
- 气体体积剂量统一性（两尺寸是否落同线）
- eGFP 病毒递送效率

## 关键结论（全文确认）

- EB 外渗与气体体积剂量**线性相关**，2µm/6µm 数据落到同一条线；
- **气体体积剂量比"浓度"更能统一预测 BBB 开放**；
- 尺寸影响循环半衰期与开放空间分布，但气体体积剂量是统一参数。

## 安全性与局限

- 需在有效开放与损伤间平衡；微泡表面也可能引发免疫反应；
- 与 TIPS 系统/特定微泡关联，参数外推需谨慎。

## 对本大鼠实验的启发

为本地 BBB 实验提供 **EB 定量判读标准（荧光量化）** + **微泡剂量选择的统一参数（按气体体积而非只按浓度）**，是对照你 EB 显色与微泡用量的直接方法学依据。

## 关联

- [[MOC_BBB微泡与空化监测]] | [[MOC_实验方法与仿真流程]]
- 术语：[[05_术语表_零基础版]]

## 同主题横向互链

- [[02_大鼠BBB实验/02_实验文献/30_Park2021_rat_BBB_validation]] — 空化剂量与 BBB
- [[02_大鼠BBB实验/02_实验文献/32_Park2025_P2X7_receptor]] — EB 分光光度定量
- [[02_大鼠BBB实验/02_实验文献/29_Rodriguez2023_rat_BBB_protocol]] — 大鼠 BBB 协议
