# Hosseinkhah et al. 2015 - 微泡、声发射与血管壁应力数值模型

## 基本信息

- 题名：Microbubbles and blood-brain barrier opening: a numerical study on acoustic emissions and wall stress predictions
- 期刊：IEEE Transactions on Biomedical Engineering, 2015
- DOI：10.1109/TBME.2014.2385651
- PMID：25546853
- PMCID：PMC4406873
- 来源：https://pubmed.ncbi.nlm.nih.gov/25546853/

## 研究目的

用数值模型研究 FUS + 微泡打开 BBB 时，微泡声发射和血管壁应力之间的关系。

## 实验/仿真对象

微泡与血管壁相互作用模型。

## 设备或软件

数值微泡动力学模型；具体实现细节需查阅全文。

## 数据来源与预处理

模型输入包括微泡尺寸、声压、频率、血管边界条件等。

## 参数设置

PubMed 记录确认其研究 acoustic emissions 和 wall stress predictions；具体半径、压力扫描区间以全文为准。

## 实验步骤

1. 建立单个或多个微泡在声场中的振动模型。
2. 设置血管壁边界和介质属性。
3. 扫描超声频率、声压和微泡尺寸。
4. 计算微泡半径响应。
5. 由微泡振动预测声发射谱。
6. 估计血管壁应力。
7. 分析声发射指标与潜在 BBB 开放/损伤机制之间的联系。

## 结果指标

- 微泡径向响应。
- 谐波/次谐波/宽带声发射。
- 血管壁应力。

## 安全性与局限

数值模型可解释机制，但需要动物或临床实验验证。模型参数对结论影响较大。

## 与 fus-sim 的衔接

适合补充潘婷论文中的 Keller-Miksis 模块，把 MI 指标进一步扩展为微泡振动和血管壁风险估计。

