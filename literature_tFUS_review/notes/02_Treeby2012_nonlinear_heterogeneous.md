# Treeby et al. 2012 - 非线性异质介质超声传播

## 基本信息

- 题名：Modeling nonlinear ultrasound propagation in heterogeneous media with power law absorption using a k-space pseudospectral method
- 期刊：Journal of the Acoustical Society of America, 2012
- DOI：10.1121/1.4712021
- PMID：22712907
- 来源：https://pubmed.ncbi.nlm.nih.gov/22712907/

## 研究目的

建立适用于组织真实非均匀介质的非线性超声传播模型，处理幂律吸收、介质异质性和非线性声学效应。

## 实验/仿真对象

组织真实介质中的超声传播，包括临床超声探头波束仿真等数值实验。

## 设备或软件

- k-space pseudospectral 方法。
- Fourier collocation 计算空间梯度。
- k-space 校正的时间推进。

## 数据来源与预处理

该文强调数值模型本身；实际应用时需要将组织结构映射为声速、密度、吸收、非线性系数等参数。

## 参数设置

- 非线性声学方程组。
- 幂律吸收模型。
- 异质介质参数分布。
- 临床探头或自定义声源。

## 实验步骤

1. 从流体力学方程推导包含非线性、吸收和异质介质项的一阶耦合声学方程。
2. 用 k-space pseudospectral 方法离散空间梯度。
3. 用数值实验验证精度和稳定性。
4. 在三维临床超声探头场景中展示模型实用性。

## 结果指标

- 声压场。
- 数值误差。
- 计算效率。
- 对复杂探头波束的模拟能力。

## 安全性与局限

本文提供传播模型，不直接处理热损伤、空化或组织安全阈值。

## 与 fus-sim 的衔接

当 `fus-sim` 从线性近似走向更真实的经颅声场时，该文可作为加入非线性、幂律吸收和异质介质的理论依据。

