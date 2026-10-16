---
type: paper
status: read
search_source: ct_acoustic_mapping
doi: 10.1016/j.ultrasmedbio.2021.05.021
pmid: 34229910
url: https://www.sciencedirect.com/science/article/abs/pii/S030156292100253X
publication_info: Y Jing, J Cheng et al. - Ultrasound in Medicine & Biology, 2021
year: 2021
tags:
  - tFUS
  - ct_acoustic_mapping
  - elastic_wave
  - mode_conversion
---

# Effect of skull porous trabecular structure on transcranial ultrasound imaging in the presence of elastic wave mode conversion at varying incidence angle

## 基本信息

- **作者**: Y Jing, J Cheng et al.
- **年份**: 2021
- **期刊/来源**: Ultrasound in Medicine & Biology, 2021
- **引用数**: 22
- **链接**: https://www.sciencedirect.com/science/article/abs/pii/S030156292100253X
- **搜索方向**: ct_acoustic_mapping

## 一句话总结

揭示了颅骨中部多孔松质骨结构（trabecular bone）在超声大角度入射时引发的弹性波“纵波-横波模式转换”（mode conversion），指出了仅依赖流体动力学简化模型会导致声衰减和折射角估算出现显性物理误差。

## 研究目的

系统评估颅骨皮质骨（inner/outer table）与多孔松质骨（diploë）界面处的弹性波转换机制，量化入射角度对声速传播和声能量畸变的影响。

## 实验/仿真对象

包含微细松质骨小梁结构的离体人类颅骨标本切片，高分辨率 micro-CT 几何重建。

## 设备、软件或方程模型

- **声学方程**: 弹性波动方程（Elastic Wave Equation），包含拉梅常数 $\lambda$ 和 $\mu$ 以捕捉剪切波（shear wave / 横波）。
- **求解器**: 有限差分时域法（FDTD）或有限元物理求解器。

## 数据来源与预处理

- 利用 micro-CT 获取微米级颅骨多孔结构几何。
- 计算弹性阻抗失配及不同偏折界面处的非平面波透射系数。

## 参数设置

- 超声激发源：主频范围覆盖 500 kHz 至 1.0 MHz。
- 临界入射角：剪切波一阶临界角（约 $20^\circ-30^\circ$）和二阶临界角（约 $45^\circ-55^\circ$）。
- 骨骼密度和弹性常数：从 HU 属性通过多相经验映射导出。

## 实验步骤

1. 构建包含三层结构（皮质骨-松质骨-皮质骨）的高分辨率二维/三维物理实体模型。
2. 改变激发声束与颅骨外表面的倾斜入射角（$0^\circ$ 至 $60^\circ$）。
3. 比较在流体模型（仅纵波，即 $c_s = 0$）与弹性模型（纵波 + 横波）下的声波传播路径。
4. 测量通过颅骨后的焦域偏移量、声阻抗反射能量分配和高频声波在多孔多重散射下的能量损耗。

## 结果指标

- **透射声强损失**：在入射角 $>20^\circ$ 时，流体模型对声能损失的预测误差上升至 15% 以上。
- **折射偏移**：横波模式转换导致声折射方向偏离 Snell 定律预测的流体折射线。
- **多孔松质骨小梁散射**：导致高频（>1 MHz）声波产生局部的宽带相位解相干。

## 关键结论

- **横波转换是高角度入射时不可忽略的物理事实**：声波大角度（超过临界角）射入颅骨时，大部分能量转换为骨内横波，若仿真中忽略这一机制将导致焦斑中心声压显著估算偏高。
- 松质骨多孔结构对声波在交界面的剪切运动有很强的物理锚定效应。

## 安全性与局限

- **安全性**：高角度偏折下的横波转换会导致颅骨表层（骨膜、硬脑膜）吸收大量剪切能而温升增加，带来了仿真中被忽视的局部热安全隐患（对标 [[13_ITRUSST_BabelBrain文献与物理对齐总结|ITRUSST 局部骨吸收限值]]）。
- **局限**：
  - micro-CT 高精度骨骼建模仅局限于小尺度切片，无法在全脑临床大网格仿真中实时求解（计算资源受限，对标 [[15_全球相似平台与AI替代模型综述|AI替代模型的研制动力]]）。

## 与 fus-sim 的衔接建议

直接指导：CT-HU 声学映射和颅骨建模

- 下一步可阅读：[[MOC_声场仿真与相位校正]] — 了解包含剪切波与复杂颅骨结构时的声学建模挑战。

## 关联

- [[MOC_参数与指标]] | [[MOC_实验方法与仿真流程]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025 - 针对三维真实松质骨结构相控阵仿处的有限元分析（直接基于 Jing 2021 理论）]]
- [[05_论文与概念/notes/23_Drainville2023_a_simulation_study|Drainville 2023 - 射线追踪模型（Ray-tracing）对颅骨弹性常数的物理敏感性分析]]
- [[05_论文与概念/notes/21_Yin2023_transcranial_ultrasonic_focusing|Yin 2023 - 真实相控阵换能器基于 micro-CT 几何的聚焦性能验证]]
- [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025 - 对 diploë（松质骨）采用多区间划分以改善映射精度的策略]]
- [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026 - 对流体波求解器（k-Wave）在大角度时误差特征的实验评测]]
