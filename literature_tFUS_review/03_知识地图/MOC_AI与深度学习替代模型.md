# MOC：AI 与深度学习替代模型

## 核心问题

全波仿真计算量大（3D [[05_论文与概念/concepts/k-Wave|k-Wave]] 一次运行可能需要数十分钟到数小时），限制了临床实时应用和大规模参数扫描。AI/深度学习替代模型（surrogate model）和 GAN 合成 CT 等方法试图在保持精度的同时大幅缩短计算时间。

如果问题是 MRI 如何进入声学模型，先看 [[05_论文与概念/concepts/synthetic CT|synthetic CT]] 和 [[MOC_影像预处理与颅骨建模]]。

## 外部论文

### 颅骨声学建模替代

- [[05_论文与概念/notes/24_Dagommer2024_robust_deep_learning|Dagommer 2024 - 深度学习从 MR T1 估计皮质骨孔隙率（CT-free 路线）]]
- [[05_论文与概念/notes/13_Koh2021_acoustic_simulation_for|Koh 2021 - GAN 合成 CT 用于声学仿真]]

### 映射策略创新

- [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025 - 孔隙率指数替代 HU 直接映射]]
- [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026 - 多策略颅骨声学建模实验交叉验证]]

### 快速仿真

- [[05_论文与概念/notes/03_Leung2019_rapid_beam_simulation|Leung 2019 - 经颅 FUS 快速声束仿真（速度 vs 精度权衡）]]

## 平台与工具

| 工具/模型 | 类型 | 论文来源 |
|---|---|---|
| TFUScapes / DeepTFUS | 端到端 AI 声场预测 | — |
| tFUSFormer | Transformer 声场预测 | — |
| [[05_论文与概念/concepts/synthetic CT|GAN synthetic CT]] | MRI→CT 合成 | Koh 2021 |
| DL porosity | MR T1→孔隙率→声学参数 | Dagommer 2024 |

## 与全波仿真的互补关系

1. AI 模型**不能替代**全波仿真用于安全验证 and 机理研究。
2. AI 模型可用于**参数预筛选**和**实时治疗规划**。
3. 训练数据来源仍是 [[05_论文与概念/concepts/k-Wave|k-Wave]] 等全波求解器。
4. 精度-速度权衡需要对每个应用场景独立验证。

## 关联 MOC

- [[MOC_声场仿真与相位校正]] — AI 替代的基准对象
- [[MOC_影像预处理与颅骨建模]] — MRI/CT 进入模型的上游流程
- [[MOC_参数与指标]] — 参数预测精度评估
- [[MOC_虚拟仿真平台证据与复现路线]] — 长远路线中的 AI 替代方向

## 相关索引

- [[15_全球相似平台与AI替代模型综述]] — 全球平台与 AI 模型综合评估
- [[16_20250628_学术搜索补充批次]] — 搜索批次中的 AI 相关论文
