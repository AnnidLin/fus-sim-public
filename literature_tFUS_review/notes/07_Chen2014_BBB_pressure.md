# Chen & Konofagou 2014 - 声压决定 BBB 开放尺寸

## 基本信息

- 题名：The Size of Blood-Brain Barrier Opening Induced by Focused Ultrasound is Dictated by the Acoustic Pressure
- 期刊：Journal of Cerebral Blood Flow & Metabolism, 2014
- DOI：10.1038/jcbfm.2014.71
- PMID：24780905
- 来源：https://journals.sagepub.com/doi/10.1038/jcbfm.2014.71

## 研究目的

评估 FUS + 微泡诱导的 BBB 开放尺寸是否由声压决定，并分析稳定空化/惯性空化与不同分子量药物递送的关系。

## 实验/仿真对象

C57BL/6 成年雄性小鼠，左侧海马 sonication，右侧海马作为对照。

## 设备或软件

- 1.5 MHz 单阵元 FUS 换能器。
- Definity 微泡。
- 10 MHz 被动空化检测器。
- 荧光显微成像。
- H&E 组织学。

## 数据来源与预处理

使用 3、70、500、2000 kDa 荧光 dextran 作为不同尺寸递送标记物。小鼠灌流固定后切片成像。

## 参数设置

- 声压：0.31、0.51、0.84 MPa。
- 微泡剂量：Definity 0.05 uL/g。
- Sonication 时长：约 11 min。
- PCD 采样频率：50 MHz。

## 实验步骤

1. 麻醉并固定小鼠头部。
2. 将 FUS 换能器通过去气水和凝胶与头部耦合。
3. 注射 Definity 微泡和指定分子量 dextran。
4. 对左侧海马进行 FUS sonication，右侧海马作为未处理对照。
5. 在 sonication 期间同步采集 PCD 声发射。
6. 约 20 min 后灌流固定、取脑、切片。
7. 用荧光显微镜量化 dextran 渗出面积和强度。
8. 进行 H&E 组织学评估损伤。

## 结果指标

- 可通过 BBB 的最大 dextran 分子量。
- 稳定空化剂量和惯性空化剂量。
- 荧光面积/强度。
- 微出血或组织损伤。

## 安全性与局限

0.84 MPa 与惯性空化和较大分子递送相关，但也出现轻微显微损伤风险。小鼠结果不能直接外推到人体颅骨。

## 与 fus-sim 的衔接

为 BBB 模块提供压力-通透性-空化机制的实验标尺，可用于校准 MI 区间和 PCD 频谱指标。

