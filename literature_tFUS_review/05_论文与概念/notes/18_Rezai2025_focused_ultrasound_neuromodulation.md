---
type: paper
status: read
search_source: safety_reporting
doi: 10.1016/j.biopsych.2024.08.012
pmid: 39182390
url: https://www.biologicalpsychiatryjournal.com/article/S0006-3223(24)01511-7/fulltext
publication_info: A Rezai, F Mahoney et al. - Biological Psychiatry, 2025
year: 2025
tags:
  - tFUS
  - safety_reporting
  - clinical_trial
  - opioid_use_disorder
---

# Focused ultrasound neuromodulation: exploring a novel treatment for severe opioid use disorder

## 基本信息

- **作者**: A Rezai, F Mahoney et al.
- **年份**: 2025
- **期刊/来源**: Biological Psychiatry, 2025
- **引用数**: 37
- **链接**: https://www.biologicalpsychiatryjournal.com/article/S0006-3223(24)01511-7/fulltext
- **搜索方向**: safety_reporting

## 一句话总结

报告了首次使用低强度聚焦超声（LIFU）靶向重度阿片类药物使用障碍（OUD）患者的双侧伏隔核（nucleus accumbens, NAc）进行无创物理调控的临床可行性与卓越的安全性，展示了深部核团神经调控的前景。

## 研究目的

评估低强度聚焦超声对难治性重度阿片类药物依赖患者进行伏隔核靶向无创神经调控的可行性、安全性和初步行为学疗效（如缓解急性戒断渴求）。

## 实验/仿真对象

符合重度难治性 OUD 标准的受试者，对双侧伏隔核进行低强度超声刺激。

## 设备、软件或方程模型

- **导航与定位**: 实时 MR 引导聚焦超声系统（MRgFUS）与 3D 光学追踪导航定位系统。
- **参数控制**: 低强度超声脉冲发生器。

## 数据来源与预处理

临床多维度评估，包含功能磁共振成像（fMRI）神经环路连接、戒断症状评定量表（COWS）以及治疗前后的认知和精神心理状态评测。

## 参数设置

- 超声主频：常见低频 220 kHz 或 250 kHz，以保障能量穿透头皮和颅骨直达深部伏隔核。
- 靶区估计原位声压：原位 $I_{SPTA}$ 控制在安全限值内，确保温升不足 0.1°C（对标 [[08_参数对齐报告|高鹏皓论文中的热效应计算]]）。
- 刺激时长：每侧靶点治疗持续数十分钟，通过脉冲控制（Duty Cycle ~ 5%-10%）。

## 实验步骤

1. 招募难治性 OUD 患者，采集术前结构 MRI 和头部 CT 进行仿真重建。
2. 将受试者固定于头架，通过 MR 引导将换能器焦点精准对准双侧伏隔核（NAc）。
3. 实施 LIFU 脉冲刺激，在此期间收集心理生理指标。
4. 刺激结束后通过高分辨率 MR 检查是否出现局部水肿或微出血。
5. 进行 90 天以上的随访，记录戒断心理渴求的改变和临床副作用。

## 结果指标

- **原位物理安全性**：全脑术后高分辨率 MR 未检测到任何微出血、局部组织水肿或异常热损伤。
- **生理反应**：急性戒断渴求（craving）在超声刺激后显著降低。
- **脑功能连接**：fMRI 证实伏隔核与前额叶皮层等成瘾环路之间的功能连接产生特异性重构。

## 关键结论

- **LIFU 脑深部靶向在人体中表现出极佳的安全性**：成功将声能聚焦到双侧伏隔核，而没有在传导通路（皮层和骨膜）引发明显的温升或空化副作用。
- **拓宽了 tFUS 的适应症范围**：将超声脑调控技术从皮层浅表（对标 [[05_论文与概念/notes/05_Legon2014_human_somatosensory|Legon 2014 的皮层运动区]]）推广至脑深部成瘾环路靶点。

## 安全性与局限

- **安全性**：无一例不良事件（SAE）发生，随访期间认知评估与术前无显著差异，符合 ITRUSST 的安全剂量边界（对标 [[05_论文与概念/notes/19_Radjenovic2022_safety_of_clinical|Radjenovic 2022 安全评估]]）。
- **局限**：
  - 样本量极小，为探索性首创临床试验，仍需多中心对照 RCT 验证。
  - 脑深部骨质环境复杂（颅底），大倾角声场路径的个体化参数校正难度高（对标 [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023 相控阵对焦分析]]）。

## 与 fus-sim 的衔接建议

间接指导：安全性与临床规范

- 下一步可阅读：[[MOC_安全性与临床神经调控]] — 查看深部刺激与皮层刺激的参数对比。

## 关联

- [[MOC_实验方法与仿真流程]] | [[MOC_研究问题与争议]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[05_论文与概念/notes/19_Radjenovic2022_safety_of_clinical|Radjenovic 2022 - 临床超声调控安全性评价与不良事件报告标准]]
- [[05_论文与概念/notes/06_Stern2021_TLE_safety|Stern 2021 - 临床癫痫患者治疗前的 LIFU 安全性及脑切片病理分析]]
- [[05_论文与概念/notes/05_Legon2014_human_somatosensory|Legon 2014 - 浅表皮层调控参数对照（用于对比深部与浅表声衰减）]]
- [[05_论文与概念/notes/15_Lee2024_a_review_of|Lee 2024 - 全球低强度人体神经调控临床进展与剂量参数横向对比]]
- [[05_论文与概念/notes/20_Javid2023_a_review_of|Javid 2023 - 神经调控技术与深部靶点换能器设计综述]]
