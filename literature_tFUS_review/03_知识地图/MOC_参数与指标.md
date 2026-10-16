# MOC：参数与指标

> [!note] 使用原则
> 本页统一参数和指标语义，不保存当前实验数值。虚拟平台结果见 [[实验平台阶段看板]]；大鼠实验参数见 [[02_大鼠BBB实验/01_本地实验/01_本地BBB实验参数对照与参考]]，两者不可直接换算。

## 核心问题

tFUS 文献中的参数很容易看似相同、实际含义不同。这个入口用来区分“输入参数”“介质参数”“声学输出指标”“安全指标”和“生物效应指标”。

## 参数资料入口

- [[07_tFUS文献与公开代码参数对照]]
- [[08_参数对齐报告]]
- [[12_实验指导型文献清单]]
- [[05_术语表_零基础版]]
- [[16_20250628_学术搜索补充批次]]

## 输入参数

- 频率：影响颅骨穿透、焦点大小和吸收。
- 声压/驱动强度：必须区分 source pressure、free-field pressure、in situ pressure 和 PNP。
- 脉冲参数：pulse duration、PRF、duty cycle、train duration、inter-train interval。
- 换能器几何：孔径、曲率半径、焦距、阵元数、阵列布局。

## 介质参数

- 声速：决定相位延迟和焦点偏移。
- 密度：影响声阻抗和传播。
- 衰减：决定能量损失和热沉积。
- 非线性参数：影响高强度声场中的波形畸变。
- 热参数：热导率、比热、灌注、热剂量模型。

## 影像到参数

- [[05_论文与概念/concepts/DICOM|DICOM]]：原始 CT/MRI 影像和扫描参数来源。
- [[05_论文与概念/concepts/NIfTI|NIfTI]]：MRI/神经影像处理常用格式。
- [[05_论文与概念/concepts/影像分割|影像分割]]：决定哪些体素属于颅骨、软组织或靶区。
- [[05_论文与概念/concepts/配准|配准]]：决定影像、换能器、靶点和仿真网格是否对齐。
- [[05_论文与概念/concepts/CT-HU映射|CT-HU 映射]]：把 CT 数值转换为声速、密度和衰减。
- [[05_论文与概念/concepts/synthetic CT|synthetic CT]]：MRI-only 或 CT-free 路线中的替代输入。

## 输出指标

- 声压峰值：常用于判断聚焦质量，但不能单独代表安全性。
- 焦点偏移：反映颅骨畸变和相位校正效果。
- 声强：常见 ISPTA、ISPPA，定义必须明确。
- 温升：需要区分短时局部温升、颅骨温升和热剂量。
- [[05_论文与概念/concepts/MI|MI]]：常用于微泡和空化风险判断。
- [[05_论文与概念/concepts/PCD|PCD]] 频谱：用于识别稳定空化、惯性空化和宽带噪声。

## CT 声学映射参考

- [[MOC_影像预处理与颅骨建模]]
- [[05_论文与概念/notes/14_Montanaro2021_the_impact_of|Montanaro 2021]]：CT 参数和颅骨异质性建模对仿真精度影响
- [[05_论文与概念/notes/17_Jing2021_effect_of_skull|Jing 2021]]：多孔松质结构对超声传播的影响
- [[05_论文与概念/notes/26_Kong2025_a_novel_method|Kong 2025]]：基于孔隙率指数的颅骨声学建模
- [[05_论文与概念/notes/27_Li2026_experimental_validation_of|Li 2026]]：颅骨声学建模实验交叉验证
- [[05_论文与概念/notes/24_Dagommer2024_robust_deep_learning|Dagommer 2024]]：MR 估计皮质骨孔隙率

## 换能器与自由场校准

- [[05_论文与概念/notes/25_Pasquinelli2020_transducer_modeling_for|Pasquinelli 2020]]：换能器建模与声场仿真校准

## 参数效应与人体证据

- [[05_论文与概念/notes/15_Lee2024_a_review_of|K Lee 2024]]：人体低强度 tFUS 神经调控功能综述
- [[05_论文与概念/notes/16_Chen2023_numerical_and_experimental|Chen 2023]]：人体颅骨声场数值与实验评估
- [[05_论文与概念/notes/20_Javid2023_a_review_of|Javid 2023]]：超声神经调控技术综述

## HIFU 热消融专属参数

- [[05_论文与概念/notes/28_Han2015_transcranial_brain_tumor_HIFU_review|韩珍珍 2015]]：半球相控阵、目标/热点双点时间反转、Pennes 温度场和 MRI 温控的历史路线综述。
- HIFU 的设备声功率、持续时间、焦点温度、CEM43 和消融体积必须成套报告。
- 文献中的 650-800 W 是特定历史设备功率，不能换算为当前模型的 1 MPa 源归一化，也不能作为患者剂量建议。
- 热消融、神经调控、BBB 和溶栓必须使用不同的剂量目标与安全门。

## 关联主题

- [[MOC_声场仿真与相位校正]]
- [[MOC_影像预处理与颅骨建模]]
- [[MOC_BBB微泡与空化监测]]
- [[MOC_超声溶栓与Histotripsy]]

## 易混点

- `1 MPa` 如果没有上下文，不能判断是 source、free-field、in situ 还是 PNP。
- duty cycle 可能指脉冲内占空比，也可能指整个刺激协议的平均占空比。
- BBB、神经调控、溶栓和 Histotripsy 使用的安全阈值不是同一套。
- CT-HU 到声学参数的映射不是唯一标准，不同论文和工具可能采用不同经验式。
