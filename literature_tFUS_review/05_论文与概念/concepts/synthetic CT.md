# synthetic CT

synthetic CT 通常指从 MRI 或其他非 CT 影像中生成类似 CT 的图像，或直接估计与 CT/骨结构相关的声学参数。它的目的通常是减少对真实 CT 扫描的依赖。

## 在 tFUS 中的意义

经颅声场仿真需要颅骨信息。真实 CT 能提供 HU 和骨结构，但有辐射和数据可得性问题。synthetic CT 或 MRI-only 路线试图从 MRI 中恢复足够可靠的骨参数，再用于治疗规划或声场预测。

## 两类路线

- MRI -> synthetic CT -> HU/声学映射 -> 声场仿真。
- MRI -> 孔隙率/骨参数 -> 声学属性 -> 声场仿真。

## 局限

- 合成影像外观接近 CT，不等于声学参数一定准确。
- 低分辨率 MRI 对颅骨微结构的表达有限。
- 需要与真实 CT 或实验声场测量对照验证。

## 相关笔记

- [[05_论文与概念/notes/13_Koh2021_acoustic_simulation_for|Koh 2021]]
- [[05_论文与概念/notes/24_Dagommer2024_robust_deep_learning|Dagommer 2024]]
- [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021]]
- [[MOC_AI与深度学习替代模型]]
- [[MOC_影像预处理与颅骨建模]]
