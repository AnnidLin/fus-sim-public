# Legon et al. 2014 - 人体感觉皮层 tFUS 调控

## 基本信息

- 题名：Transcranial focused ultrasound modulates the activity of primary somatosensory cortex in humans
- 期刊：Nature Neuroscience, 2014
- DOI：10.1038/nn.3620
- 来源：https://www.nature.com/articles/nn.3620

## 研究目的

验证低强度经颅聚焦超声是否能调制人类初级躯体感觉皮层活动。

## 实验/仿真对象

健康人受试者，靶点为 primary somatosensory cortex。

## 设备或软件

- 低强度 tFUS 装置。
- EEG/诱发电位记录。
- 行为感觉辨别任务。

## 数据来源与预处理

人体实验数据，包括 EEG 和行为任务表现。具体声束建模和靶向参数需以全文及补充材料为准。

## 参数设置

该文公开页面核验 DOI 和研究主题；具体 tFUS 脉冲、频率、强度等细节应查阅全文/补充材料。

## 实验步骤

1. 定位初级躯体感觉皮层靶区。
2. 在任务期间给予低强度 tFUS。
3. 记录感觉诱发电位和脑电变化。
4. 同步采集行为辨别任务表现。
5. 比较 sonication 与对照条件下的神经和行为指标。

## 结果指标

- Somatosensory evoked potentials。
- 行为辨别能力。
- 靶区调制效应。

## 安全性与局限

该文证明人体 tFUS 调制可行，但不是经颅颅骨声场仿真论文；用于 `fus-sim` 时主要作为应用和安全背景。

## 与 fus-sim 的衔接

为高鹏皓论文的 tFUS 神经调控应用提供国际研究背景；仿真平台应最终能输出与低强度神经调控相关的剂量指标。

