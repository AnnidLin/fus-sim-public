---
type: paper
status: read
search_source: parameter_effect
doi: 10.1007/s13534-024-00360-1
pmid: 38550112
url: https://link.springer.com/article/10.1007/s13534-024-00360-1
publication_info: K Lee, H Kim, C Pasquinelli et al. - Biomedical Engineering Letters, 2024
year: 2024
tags:
  - tFUS
  - parameter_effect
  - clinical_neuromodulation
  - review
---

# A review of functional neuromodulation in humans using low-intensity transcranial focused ultrasound

## 基本信息

- **作者**: K Lee, H Kim, C Pasquinelli et al.
- **年份**: 2024
- **期刊/来源**: Biomedical Engineering Letters, 2024
- **引用数**: 59
- **链接**: https://link.springer.com/article/10.1007/s13534-024-00360-1
- **搜索方向**: parameter_effect

## 一句话总结

系统综述了利用低强度经颅聚焦超声（LIFU/tFUS）在人体中进行脑功能神经调控的研究进展，指出了目前文献中存在的刺激参数报告不规范、个体化声阻抗计算缺失等认知断点。

## 研究目的

全面整理已发表的 LIFU/tFUS 人体神经调控临床研究，系统分析频率、声压、声强、脉冲模式等控制参数与实际调控生理效应之间的因果联系。

## 实验/仿真对象

2014-2023年间发表的数十项人类受试者 tFUS 神经调控临床实验（涵盖躯体感觉皮层、运动皮层、丘脑、海马等靶点）。

## 设备、软件或方程模型

- **设备**: 单阵元聚焦超声换能器、相控阵系统（如 ExAblate）。
- **标准**: ITRUSST（经颅超声安全与剂量标准联盟）指南。

## 数据来源与预处理

系统性文献回顾与荟萃分析，提取出声强（$I_{SPTA}$）、[[05_论文与概念/concepts/MI|机械指数]]（$[[05_论文与概念/concepts/MI|MI]]$）、刺激脉冲长度（PL）、脉冲重复频率（PRF）等数据。

## 参数设置

- 频率区间：0.2 MHz - 0.65 MHz 占主导（对标 [[05_术语表_零基础版#频率|低频穿透特性]]）。
- 空间峰值瞬时声强 ($I_{SPTA}$)：多位于 $1 - 30\text{ W/cm}^2$ 安全界限内。
- 占空比（Duty Cycle）：常见为 5% 至 30%（对标 [[08_参数对齐报告|高鹏皓论文中的参数范围]]）。

## 实验步骤

1. 检索符合 LIFU 人体脑功能调控的临床研究。
2. 提取刺激靶区定位方法（如 neuronavigation 或无颅骨纯几何定位）。
3. 统计各研究的输出声压、原位声场参数估计方法。
4. 汇总脑电波（EEG）、诱发电位（ERP）和功能磁共振（fMRI）的响应。
5. 交叉对比声学参数与调控方向（抑制 vs 兴奋）。

## 结果指标

- **刺激方案一致性**：极差，不同实验室参数定义的混淆率达 40% 以上。
- **治疗计划仿真率**：仅有少部分近期研究引入了三维基于 [[05_论文与概念/notes/01_Treeby2010_kWave|k-Wave]] 的个体声场仿真。
- **安全边界事件**：人体低强度刺激下无严重组织学损伤或长期认知缺陷报告。

## 关键结论

- **参数混乱阻碍了临床转化**：不同实验室对于 $I_{SPTA}$（空间峰值时间平均声强）和 $I_{SPPA}$ 的计算假设不一致，导致疗效难以复制。
- **经颅骨原位参数计算是下一步关键**：必须先通过数值仿真计算得到 cranial attenuation（骨衰减）后的 in situ（原位）参数，而不能仅汇报自由场水槽测得的 source 激发参数（对标 [[05_论文与概念/notes/25_Pasquinelli2020_transducer_modeling_for|Pasquinelli 2020 的物理校准思路]]）。

## 安全性与局限

- **安全性**：确认 LIFU 在规定 $[[05_论文与概念/concepts/MI|MI]] \le 1.9$ 范围内的人体应用具有良好的安全耐受性（符合 [[05_论文与概念/notes/19_Radjenovic2022_safety_of_clinical|Radjenovic 2022 安全评估]]）。
- **局限**：
  - 缺乏对不同大脑状态下（如静息态 vs 任务态）tFUS 生理敏感性的横向对比。
  - 缺乏对长期慢性刺激的累积脑组织热效应量化评估。

## 与 fus-sim 的衔接建议

直接指导：参数设置和效应关系

- 下一步可阅读：[[MOC_安全性与临床神经调控]] — 了解临床上 tFUS 的安全剂量设计标准。

## 关联

- [[MOC_参数与指标]] | [[MOC_研究问题与争议]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[05_论文与概念/notes/20_Javid2023_a_review_of|Javid 2023 - 相似的主题技术综述，侧重设备和调控工程设计]]
- [[05_论文与概念/notes/16_Chen2023_numerical_and_experimental|Chen 2023 - 人体颅骨声学传播数值与实验验证（提供原位参数计算标尺）]]
- [[05_论文与概念/notes/05_Legon2014_human_somatosensory|Legon 2014 - 首个人体感觉皮层调控的经典论文（Lee 2024 的基石文献）]]
- [[05_论文与概念/notes/06_Stern2021_TLE_safety|Stern 2021 - 癫痫患者开颅手术前安全调控与组织病理评估]]
- [[05_论文与概念/notes/19_Radjenovic2022_safety_of_clinical|Radjenovic 2022 - 临床超声神经调控的系统性安全性总结]]
