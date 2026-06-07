# Leung et al. 2019 - 经颅 FUS 快速声束仿真

## 基本信息

- 题名：A rapid beam simulation framework for transcranial focused ultrasound
- 期刊：Scientific Reports, 2019
- DOI：10.1038/s41598-019-43775-6
- 来源：https://www.nature.com/articles/s41598-019-43775-6

## 研究目的

提出快速经颅聚焦超声声束仿真框架，用于治疗计划、焦点预测和温升相关评估。

## 实验/仿真对象

经颅 FUS 治疗计划场景，使用医学影像中的颅骨信息来估计声束传播。

## 设备或软件

- 快速 beam simulation framework。
- 医学影像输入，包含 CT/MRI 相关信息。
- 与 MR thermometry 等治疗监测结果对照。

## 数据来源与预处理

使用患者影像建立头颅/颅骨模型。需要将影像体素转换为声学属性，并对换能器和靶点坐标配准。

## 参数设置

公开页面确认该文围绕 transcranial focused ultrasound、CT/MRI、MR thermometry 和治疗计划展开；更细参数应以全文为准。

## 实验步骤

1. 获取患者头部影像并配准换能器坐标。
2. 从影像中提取颅骨相关声学传播信息。
3. 使用快速声束模型预测焦点和能量分布。
4. 与实际治疗或 MR thermometry 结果比较。
5. 评估该框架在临床治疗计划中的速度和可靠性。

## 结果指标

- 焦点位置。
- 声束形态。
- 与 MR 热测量/治疗结果的一致性。
- 计算速度。

## 安全性与局限

快速模型适合筛选和计划，但高精度安全评估仍需更完整的声热模型或实验验证。

## 与 fus-sim 的衔接

适合作为 `fus-sim` 的中期目标：在完整 k-Wave 三维仿真之前，建立更快的声束预估层，用于参数筛选。

