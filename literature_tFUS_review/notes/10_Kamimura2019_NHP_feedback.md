# Kamimura et al. 2019 - 非人灵长类 BBB 开放反馈控制

## 基本信息

- 题名：Feedback control of microbubble cavitation for ultrasound-mediated blood-brain barrier disruption in non-human primates under magnetic resonance guidance
- 期刊：Journal of Cerebral Blood Flow & Metabolism, 2019
- DOI：10.1177/0271678X17753514
- 来源：https://journals.sagepub.com/doi/10.1177/0271678X17753514

## 研究目的

在非人灵长类中建立 MR 引导 FUS + 微泡 BBB 开放系统，并用 PCD 相对谱进行反馈控制。

## 实验/仿真对象

非人灵长类动物，MR 引导下进行 BBB disruption。

## 设备或软件

- 7T MRI。
- MR-guided FUS 系统。
- Passive cavitation detection。
- T1 加权对比增强 MRI。

## 数据来源与预处理

MRI 用于靶向、术后确认 BBB 开放和出血/安全性评估。PCD 用于实时空化反馈。

## 参数设置

- 频率：500 kHz。
- 脉冲长度：10 ms。
- PRF：5 Hz。
- Sonication：2 min。
- 代表性安全压力范围：约 185 ± 22 kPa 至 266 ± 4 kPa。

## 实验步骤

1. 在 7T MRI 下定位靶区并设置 FUS 系统。
2. 注射微泡并进行 500 kHz FUS sonication。
3. 在 sonication 期间采集 PCD 信号。
4. 用相对谱反馈控制空化水平。
5. 进行 T1 加权对比增强 MRI，确认 BBB 开放。
6. 分析焦点处对比增强量和潜在出血风险。
7. 评估 PCD 对声耦合条件和跨实验会话一致性的监控能力。

## 结果指标

- BBB 开放增强区域。
- PCD 相对谱。
- 安全声压范围。
- 对比剂相对增强。
- 出血/组织风险。

## 安全性与局限

非人灵长类证据强于小动物，但样本和系统条件仍有限；参数不能直接迁移到所有患者。

## 与 fus-sim 的衔接

为闭环 BBB 安全控制提供高等级参考，可作为 `fus-sim` 未来输出“安全建议”时的外部标尺。

