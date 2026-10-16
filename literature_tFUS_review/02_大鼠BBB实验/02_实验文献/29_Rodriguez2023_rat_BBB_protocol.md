---
type: paper
status: verified-fulltext
theme: BBB_opening_protocol
doi: 10.3390/pharmaceutics15122733
pmid: 38140074
pmcid: PMC10748005
year: 2023
tags:
  - BBB
  - rat
  - Wistar
  - craniotomy
  - focused-ultrasound
  - protocol
  - Evans-blue
fulltext: verified
---

# Rodríguez et al. 2023 - 短时聚焦超声诱导大鼠 BBB 临时开放协议

> [!note] 全文已核对
> 本笔记参数来自 PMC10748005 全文 XML（已核验），非元数据推断。

## 基本信息

- 题名：Protocol to Induce the Temporary Opening of the Blood-Brain Barrier with Short-Time Focused Ultrasound in Rats
- 作者年份：Rodríguez JA, Gutiérrez MI, ..., Leija L, 2023
- 期刊：Pharmaceutics, 2023
- DOI：10.3390/pharmaceutics15122733
- PMID：38140074 / PMCID：PMC10748005
- 链接：https://pubmed.ncbi.nlm.nih.gov/38140074/
- 本机原文：[[02_大鼠BBB实验/03_原文PDF/29_Rodriguez2023_rat_BBB_protocol.pdf]]（开放获取，PMC10748005）

## 一句话总结

给出**雄性 Wistar 大鼠、2 MHz 聚焦超声 + 颅骨切开**开放 BBB（靶向黑质）的可逆实验协议，并用 FEM 数值仿真确定参数。与本地 0.8 MHz BBB 实验最相关的方法学参考。

## 研究目的

建立一套临时、可逆、微创的 FUS 开放 BBB 协议；先用数值仿真确定参数，再用活体动物验证。

## 实验/仿真对象

- **动物**：雄性 Wistar 大鼠，经**颅骨切开术（craniotomy）**辐照黑质（substantia nigra）
- **仿真**：2D 轴对称 FEM 模型，研究颅骨/脑膜/脑组织的声场与温升

## 设备、软件或方程模型

- **换能器**：单凹面 2 MHz，焦距 20 mm、直径 20 mm（Onda 公司）
- **信号源**：波形发生器（Rohde & Schwarz 6200-601841）
- **换能器表征**：宽带水听器 HNP-1000（Onda）+ 3D 自动定位系统，脱气水校准
- **颅骨切开**：Dremel 395 钻 + 1 mm 钻头
- **动物固定**：立体定位仪（Stoelting 51600）
- **仿真**：Helmholtz 方程（频域/线性）、Pennes 生物传热方程；三角形网格 9 单元/波长

## 数据来源与预处理

数值仿真 + 活体实验。颅骨切开半径在 0.5–5 mm 范围系统变化，比较温升与开野外形。

## 参数设置（全文确认）

- **频率**：标称 2 MHz，实测工作频率 **1.965 MHz**
- **功率**：电功率 **5 W**；换能器表面声压 **200 kPa**
- **脉冲**：正弦，**10 Hz tone burst**；占空比 **DC=20%**
  - 50 s 通（DC 20%），30 s 关（rest），重复
- **总辐照时长**：颅骨切开后约 **2.5 min**
- **颅骨切开**：方形边长对应侧，**5 mm 半径（10 mm 边长）温升最佳**
- **EB 染色**：**1 mL Evans blue（MW 960.8 g/mol）**，尾背静脉注射
- 动物规范：NOM-062-ZOO-1999；伦理 CICUAL（protocol 162-15）

## 实验步骤

1. 麻醉并固定于立体定位仪；
2. Dremel 制作方形颅骨切开（避开头骨强吸收温升）；
3. 尾背静脉注射 1 mL EB；
4. FUS 2 MHz、5 W、DC20% 脉冲照射靶点（黑质）约 2.5 min；
5. 观察 EB 外渗；FUS 后不同时间点（立即、6 h）注射 EB 检验可逆性；
6. 24 h 后深麻醉（戊巴比妥 0.7 mL/220 g）取脑、切片；
7. 数值仿真同步验证声场与温升。

## 结果指标

- BBB 开放区域（EB 蓝染）
- 颅骨/骨产生温升
- BBB 开放持续与恢复时间

## 关键结论

- 产生**临时、局部、可逆**的 BBB 开放：FUS 约 2.5 min，**约 6 h 后 BBB 恢复**；
- 最佳颅骨切开 5 mm 半径；
- 数值仿真用于确定实验参数，减小骨吸收温升。

## 安全性与局限

- 采用颅骨切开避开头骨强吸收温升损伤；
- 骨吸收是主要热风险；
- **2 MHz 与本地 0.8 MHz 设置不同，参数不可直接照抄**，需换算频率/声压。

## 对本大鼠实验的启发

EB 法和短时 BBB 开放协议可作为本地大鼠实验的显色终点与时间安排参考。该研究的颅窗、频率和设备条件与本地实验不同，参数不能直接照搬。

## 关联

- [[MOC_实验方法与仿真流程]] | [[MOC_BBB微泡与空化监测]]
- 术语：[[05_术语表_零基础版]]
- 本地 BBB 预实验见 `<LOCAL_REFERENCE_DATA>\实验\`（0.8 MHz、无颅窗，参数需对照）

## 同主题横向互链

- [[02_大鼠BBB实验/02_实验文献/30_Park2021_rat_BBB_validation]] — 人颅骨平台大鼠 BBB 验证
- [[09_Burgess2018_power_cavitation]] — 空化引导 BBB 开放
- [[07_Chen2014_BBB_pressure]] — 声压决定 BBB 开放尺寸
