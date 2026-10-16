# Maxwell et al. 2011 - 猪 DVT 模型 histotripsy 溶栓

## 基本信息

- 题名：Noninvasive treatment of deep venous thrombosis using pulsed ultrasound cavitation therapy (histotripsy) in a porcine model
- 期刊：Journal of Vascular and Interventional Radiology, 2011
- DOI：10.1016/j.jvir.2010.10.007
- PMID：21194969
- PMCID：PMC3053086
- 来源：https://pubmed.ncbi.nlm.nih.gov/21194969/

## 研究目的

评估 histotripsy 作为非侵入、图像引导的体内血栓溶解方法在猪深静脉血栓模型中的可行性。

## 实验/仿真对象

30-40 kg 幼猪股静脉急性血栓模型。

## 设备或软件

- Histotripsy FUS 系统。
- 实时超声成像引导。
- 血流/再通评估工具。

## 数据来源与预处理

ScienceDirect 摘要确认急性血栓通过球囊阻塞和凝血酶注入在股静脉形成。

## 参数设置

具体脉冲序列和换能器参数需查阅全文；核心方法是短高强度聚焦脉冲诱导空化机械破碎。

## 实验步骤

1. 麻醉幼猪并暴露/定位股静脉区域。
2. 通过两个导管球囊阻塞目标静脉段。
3. 注入凝血酶形成急性血栓。
4. 使用实时超声成像定位血栓。
5. 对血栓区域进行 histotripsy sonication。
6. 评估血管再通、血流恢复和残余血栓。
7. 检查血管壁损伤、出血和远端碎片风险。

## 结果指标

- 血管再通。
- 血流恢复。
- 血栓破碎程度。
- 血管壁损伤。
- 体内安全性。

## 安全性与局限

研究对象是深静脉血栓，不是脑血栓；经颅脑血栓应用还需考虑颅骨、脑血管尺度、栓子碎片和神经安全性。

## 与 fus-sim 的衔接

为从仿真声压阈值走向动物实验验证提供路线。`fus-sim` 后续若做脑血栓，应先加入血管/血栓几何，再讨论再通指标。

