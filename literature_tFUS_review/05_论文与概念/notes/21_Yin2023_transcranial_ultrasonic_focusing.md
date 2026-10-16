---
type: paper
status: read
search_source: ct_acoustic_mapping
doi: 10.3390/s23052612
pmid: 36904816
url: https://www.mdpi.com/1424-8220/23/5/2612
publication_info: F Yin, Y Wang et al. - Sensors, 2023
year: 2023
tags:
  - tFUS
  - ct_acoustic_mapping
  - phased_array
  - time_reversal
  - micro_ct
---

# Transcranial ultrasonic focusing by a phased array based on micro-CT images

> [!warning] 核验状态
> [[01_虚拟仿真平台/02_论文原文/21_Yin2023_microCT_phased_array_original.pdf|本地开放获取正式版]]已取得；本笔记尚未逐条按页码复核。

## 基本信息

- **作者**: F Yin, Y Wang et al.
- **年份**: 2023
- **期刊/来源**: Sensors, 2023
- **引用数**: 5
- **链接**: https://www.mdpi.com/1424-8220/23/5/2612
- **搜索方向**: ct_acoustic_mapping

## 一句话总结

基于高分辨率 micro-CT 扫描图像建立了离体人类颅骨三维高保真有限元模型，运用[[05_论文与概念/concepts/时间反转|时间反转]]（[[05_论文与概念/concepts/时间反转|Time Reversal]]）算法对多通道相控阵超声换能器进行相位校正，验证了该模型能够显著克服颅骨引起的焦斑畸变与衰减。

## 研究目的

评估基于高精度 micro-CT 图像的物理几何映射对于相控阵聚焦超声相位校正精度的收益，量化复杂骨小梁几何下的声波能量折射和时间延迟。

## 实验/仿真对象

离体人类颞骨标本，通过高精度 micro-CT 扫描重建几何。相控阵超声换能器系统。

## 设备、软件或方程模型

- **三维有限元方程**: 三维流体-固体耦合波动方程或流体近似伪谱法。
- **校正算法**: [[05_论文与概念/concepts/时间反转|时间反转]]（[[05_论文与概念/concepts/时间反转|Time Reversal]], TR）算法（对标 [[03_experimental_steps#A 经颅聚焦超声声场仿真与相位校正|SOP 相位校正步骤]]）。
- **成像**: micro-CT 高分辨率成像。

## 数据来源与预处理

- 对离体颞骨进行 100 微米以下级别的高清 micro-CT 扫描。
- 分割得到皮质骨、松质骨和周边软组织的三维坐标网格。

## 参数设置

- 超声主频：常见的经颅频段，如 500 kHz 或 1.0 MHz。
- 相控阵阵元：由数十个独立压电陶瓷块组成的非球形贴合阵列（对标 [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction|Jin 2020 临床换能器阵元配置]]）。
- 骨声速：HU 连续经验公式计算。

## 实验步骤

1. 导入 micro-CT 提取出的颞骨三维实体几何。
2. 在脑实质靶点放置虚拟“声学点源”，反向向外发射声波，穿透颞骨传播至换能器阵元表面。
3. 提取各个相控阵阵元接收到的声波相位，并对其计算复共轭（即[[05_论文与概念/concepts/时间反转|时间反转]]TR相位延迟）。
4. 在正向激励仿真中，将计算好的相位延迟加载至各个阵元，再次激发，使超声声束经颅骨在靶点实现重聚焦。
5. 比较未校正与[[05_论文与概念/concepts/时间反转|时间反转]]校正后的焦斑（焦域尺寸、声压强度、旁瓣比）。

## 结果指标

- **焦斑重建质量**：未校正前，焦点漂移达 3 mm 以上，声压峰值严重衰减，旁瓣能量扩散。
- **TR 重聚焦性能**：校正后焦斑几何形状恢复为对称椭球体，焦点位置重合度大于 90%。
- **反射与透射占比**：量化了 micro-CT 级复杂边缘的局部声压散射损耗。

## 关键结论

- **[[05_论文与概念/concepts/时间反转|时间反转]]法在高分辨率图像支持下可实现完美对焦**：micro-CT 提供的结构细节极大地消除了声速估算带来的多重折射误差。
- 证明了相控阵多通道独立调节对克服复杂颞鳞区（temporal bone）骨厚度剧烈变化的必要性（对标 [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025 真实松质骨相控对焦]]）。

## 安全性与局限

- **安全性**：TR 校正显著调低了非靶区（尤其是颅骨内侧表层）的声能聚集，有助于降低副瓣对脑膜的热副反应。
- **局限**：
  - micro-CT 无法在活体人类受试者（in vivo）中常规实施（辐射剂量太大），如何用临床低清 CT 或 MRI 合成类似的高保真几何是应用瓶颈（对标 [[05_论文与概念/notes/13_Koh2021_acoustic_simulation_for|Koh 2021 GAN 合成 CT 进展]]）。

## 与 fus-sim 的衔接建议

直接指导：CT-HU 声学映射和颅骨建模

- 下一步可阅读：[[MOC_声场仿真与相位校正]] — 查阅其他相位校正算法（如 ray-tracing）。

## 关联

- [[MOC_参数与指标]] | [[MOC_实验方法与仿真流程]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[05_论文与概念/notes/22_Rossano2025_probing_phased-array_focused|Rossano 2025 - 同样使用 3D松质骨几何的多通道相控阵聚焦仿真评估]]
- [[05_论文与概念/notes/23_Drainville2023_a_simulation_study|Drainville 2023 - 射线追踪（ray-tracing）与时间反转法在大斜度入射下的误差灵敏度对比]]
- [[05_论文与概念/notes/04_Jin2020_open_source_phase_correction|Jin 2020 - 开源经颅相位校正工具（同样针对相控阵的 ex vivo 标定与对比）]]
- [[05_论文与概念/notes/17_Jing2021_effect_of_skull|Jing 2021 - 评估大入射角下横波转换对聚焦校正的物理限制]]
- [[05_论文与概念/notes/13_Koh2021_acoustic_simulation_for|Koh 2021 - 合成高精度 CT（sCT）用于相位延迟计算的可行性探索]]
