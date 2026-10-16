---
type: paper
status: read
search_source: ct_acoustic_mapping
doi: 10.1109/TBME.2021.3106248
pmid: 34424177
url: https://ieeexplore.ieee.org/abstract/document/9513594/
publication_info: H Koh, TY Park, YA Chung, JH Leeet al. - IEEE Journal of Biomedical and Health Informatics, 2021
year: 2021
tags:
  - tFUS
  - ct_acoustic_mapping
  - gan_synthetic_ct
  - ct_free
---

# Acoustic simulation for transcranial focused ultrasound using GAN-based synthetic CT

## 基本信息

- **作者**: H Koh, TY Park, YA Chung, JH Lee et al.
- **年份**: 2021
- **期刊/来源**: IEEE Transactions on Biomedical Engineering, 2021
- **引用数**: 51
- **链接**: https://ieeexplore.ieee.org/abstract/document/9513594/
- **搜索方向**: ct_acoustic_mapping

## 一句话总结

证明了使用 3D-GAN 从 MRI 图像生成的“合成 CT”（synthetic CT）来进行经颅聚焦超声声场仿真，能达到与真实 CT 极为接近的焦点声压和空间分布，为临床 tFUS 治疗计划的“CT-free”化提供了可行性方案。

## 研究目的

评估基于生成对抗网络（GAN）生成的合成 CT 在 tFUS 声学仿真中的可行性与精度，旨在减少患者接受电离辐射（CT 扫描）的必要性。

## 实验/仿真对象

10 名受试者的真实头部 MRI 和 CT 配对图像，生成合成 CT。仿真靶点包括丘脑（thalamus）和运动皮层（motor cortex）。

## 设备、软件或方程模型

- **生成模型**: 3D CycleGAN 或 pix2pix GAN 变体。
- **声学求解器**: 基于 [[05_论文与概念/notes/01_Treeby2010_kWave|k-Wave]] 的经颅声场传播仿真。
- **属性映射**: HU 线性映射（声速、密度、衰减）。

## 数据来源与预处理

- MRI T1/T2 图像与 CT 配对，通过刚性配准（registration）对齐。
- GAN 接受 MRI 作为输入，输出生成伪 CT，并在骨骼区域计算 MAE。

## 参数设置

- 超声频率：250 kHz 与 500 kHz（对标 [[07_tFUS文献与公开代码参数对照|tFUS 常见临床频段]]）。
- 映射公式：标准分段 HU 映射。
- 网格分辨率：$\lambda/6$ 或更高，保证 [[05_论文与概念/concepts/k-Wave|k-Wave]] 收敛。

## 实验步骤

1. 使用临床配对 MRI 和 CT 数据训练 3D-GAN 模型。
2. 输入测试集 MRI，生成 synthetic CT (sCT)。
3. 在真实 CT (rCT) 和 sCT 下运行相同的 [[05_论文与概念/notes/01_Treeby2010_kWave|k-Wave]] 三维经颅超声声场仿真。
4. 提取几何焦点的声压峰值、焦点偏移量和声场空间相似度（SSIM）。
5. 比较 250 kHz 和 500 kHz 下的绝对误差。

## 结果指标

- **骨骼 HU 绝对误差**：sCT vs rCT 的骨骼区域 MAE。
- **焦点声压峰值误差**：在 500 kHz 下，声压误差小于 8.5%。
- **焦点位置偏移**：真实焦点与合成焦点的几何漂移在 1.5 mm 以内（小于半波长）。

## 关键结论

- **GAN 生成的骨骼细节具备高声学可信度**：Synthetic CT 完全可以替代真实 CT 进行 tFUS 的三维声场规划。
- sCT 在 250 kHz 下的表现优于 500 kHz，表明声速/衰减映射在高频下对几何细微偏差更敏感（对标 [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021 的 CT 敏感性结论]]）。

## 安全性与局限

- **安全性**：sCT 预测的声场能有效识别脑实质内的次级声压峰值（旁瓣），避免局部过热风险。
- **局限**：
  - 未考虑松质骨的多孔弹性横波（对标 [[05_论文与概念/notes/17_Jing2021_effect_of_skull|Jing 2021]]）。
  - GAN 对非典型颅骨病变（如颅骨增厚、骨质疏松）的泛化精度有待提高。

## 与 fus-sim 的衔接建议

直接指导：CT-HU 声学映射和颅骨建模

- 下一步可阅读：[[MOC_AI与深度学习替代模型]] — 了解其他 AI 替代模型和合成模型的发展。

## 关联

- [[MOC_参数与指标]] | [[MOC_实验方法与仿真流程]]
- 本地论文: [[01_seed_papers_summary]]
- 搜索批次: [[19_增强搜集补充清单]]

---

## 同主题横向互链

本笔记与以下同主题笔记可交叉阅读：

- [[05_论文与概念/notes/24_Dagommer2024_robust_deep_learning|Dagommer 2024 - 升级版：直接从 MRI 估计皮质骨孔隙率]]
- [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021 - 评估 CT 重建参数本身对声场精度的敏感性]]
- [[05_论文与概念/notes/17_Jing2021_effect_of_skull|Jing 2021 - 评估松质骨对折射/反射的影响]]
- [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025 - 相比 HU 映射，采用孔隙率指数映射的效果]]
- [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026 - 各种声学建模映射策略的交叉实验验证]]
