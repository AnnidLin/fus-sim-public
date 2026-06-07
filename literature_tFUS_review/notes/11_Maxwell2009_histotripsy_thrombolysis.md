# Maxwell et al. 2009 - 体外 histotripsy 溶栓

## 基本信息

- 题名：Noninvasive thrombolysis using pulsed ultrasound cavitation therapy - histotripsy
- 期刊：Ultrasound in Medicine & Biology, 2009
- DOI：10.1016/j.ultrasmedbio.2009.07.001
- PMID：19854563
- PMCID：PMC2796469
- 来源：https://pubmed.ncbi.nlm.nih.gov/19854563/

## 研究目的

评估短脉冲空化治疗 histotripsy 是否可非侵入性破碎血栓。

## 实验/仿真对象

体外血凝块/血栓模型。

## 设备或软件

- Pulsed focused ultrasound / histotripsy 系统。
- 实时超声成像或声学监测。

## 数据来源与预处理

构建体外血栓或血凝块样本，并在声束焦点处接受短高强度脉冲。

## 参数设置

PubMed 和二级记录确认该研究使用 pulsed ultrasound cavitation therapy；孙天宇论文引用其 -6 MPa 和 -8 MPa 相关溶栓阈值作为仿真目标。

## 实验步骤

1. 制备体外血栓/血凝块样本。
2. 将样本置于声学耦合介质中并定位到 FUS 焦点。
3. 设置短高强度脉冲序列诱导空化云。
4. 逐步调节声压/脉冲参数，观察空化和血栓破碎。
5. 用图像、质量变化或通道形成评估溶栓效果。
6. 记录是否存在非靶区损伤或碎片风险。

## 结果指标

- 血栓质量损失或通道形成。
- 空化云形成。
- 峰值负压阈值。
- 处理时间。

## 安全性与局限

体外模型不能完整反映血流、血管壁和体内碎片风险，需要动物实验验证。

## 与 fus-sim 的衔接

为孙天宇论文中的声压阈值提供实验依据；`fus-sim` 溶栓模块应先输出峰值负压是否达到 -6/-8 MPa 区间。

