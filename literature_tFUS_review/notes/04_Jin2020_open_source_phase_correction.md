# Jin et al. 2020 - 开源经颅相位校正工具

## 基本信息

- 题名：An open-source phase correction toolkit for transcranial focused ultrasound
- 期刊：BMC Biomedical Engineering, 2020
- DOI：10.1186/s42490-020-00043-3
- 来源：https://bmcbiomedeng.biomedcentral.com/articles/10.1186/s42490-020-00043-3

## 研究目的

开发并验证一个 ray-based 开源相位校正工具 Kranion，用于补偿颅骨导致的经颅 FUS 相位畸变和焦点偏移。

## 实验/仿真对象

离体人颅骨和临床 MRgFUS 系统。

## 设备或软件

- Kranion 软件。
- ExAblate 650 kHz FUS transducer。
- 1024 阵元临床脑部换能器。
- AIMS III 水槽和 hydrophone 扫描系统。

## 数据来源与预处理

离体颅骨 CT 扫描，并对颅骨进行脱气处理。工具根据 CT/几何信息计算相位校正。

## 参数设置

- 650 kHz 临床 FUS 系统。
- 水槽中去气水，残余氧含量低于 1.1 ppm。
- Hydrophone 2D 扫描覆盖约 10 mm x 10 mm，步长 0.25 mm。

## 实验步骤

1. 准备离体人颅骨并完成 CT 扫描。
2. 将临床 FUS 换能器安装到水槽测试平台。
3. 进行自由场 sonication，记录无颅骨焦点。
4. 加入颅骨后分别测试无校正、ExAblate 校正和 Kranion 校正。
5. 用 hydrophone 扫描焦平面和轴向平面。
6. 比较焦点偏移、峰值负压和计算时间。

## 结果指标

- 焦点偏移。
- 峰值负压提升。
- 每次 sonication 的相位计算时间。

## 安全性与局限

该研究是离体颅骨和水槽验证，不直接证明人体治疗安全，但对治疗计划中的相位补偿有很高复现价值。

## 与 fus-sim 的衔接

可作为 `fus-sim` 后续相位校正模块的模板：先实现简化 ray-based 延迟，再与时间反转或 k-Wave 结果比较。

