# 当前实验基线：Case 079

> [!warning] 历史状态
> 本页记录 2026-07-10 前后的早期工程基线，不再代表平台最新进度。当前执行目标和最新 250 kHz TR 结果见 [[实验平台阶段看板]]；本页数值仅按原有证据边界保留。

## 实验对象

- 数据：Case 079 NIfTI CT。
- 靶点：`target_020 = [93, 121, 63]`。
- 当前工程 profile：`simple_hu300`。
- 主要网格：dx 0.75 mm；PML 12；CFL 0.2。
- 换能器：孔径 30 mm、曲率半径 35 mm、频率 500 kHz。

背景入口：[[MOC_影像预处理与颅骨建模]]、[[05_论文与概念/concepts/NIfTI|NIfTI]]、[[05_论文与概念/concepts/CT-HU映射|CT-HU 映射]]。

## 两类结果必须分开

### corrected 边缘掠过基线

- dx0.75 target-window peak：2.449 MPa。
- global peak：5.179 MPa。
- target/global：40.3%。
- 热学基线最大升温约 1.476°C，skull CEM43 约 0.0059 min，局部工程门控为 `overall_safe=true`。

波束轴避开了 300 HU 骨阈值，因此它更接近 **自由场等效聚焦增益**，不能解释为真实厚颅骨穿透后的残余压力。

### `(+5,0)` 厚颅骨外部有效性测试

- source mask：1319/1319 体素均在背景，source-safe 门控通过。
- target pressure：0.5337 MPa。
- target-window peak：0.5957 MPa。
- global skull peak：9.6982 MPa。
- target/global：0.0550。
- 全局峰值距 entry 3.09 mm，距 target 56.39 mm。
- target waveform PNP：0.5142 MPa；target-site MI proxy：0.727。

运行本身成功，但**聚焦目标失败**。它证明平台能执行真实穿颅候选，也证明当前几何会把能量集中在入颅附近，而不是靶区。

## 当前阻塞

下一个候选必须同时处理：

- source mask 不进入组织；
- 入颅附近全局峰值下降；
- effective peak 更接近 target；
- target-window 递送不因加窗或幅度抑制而完全丢失。

相关入口：[[MOC_声场仿真与相位校正]]、[[MOC_参数与指标]]、[[MOC_研究问题与争议]]。

## 结论边界

当前可以说：

- Case 079 的 CT-to-pressure-to-Pennes 工程链可重复运行。
- 数值边界和时间步敏感性已有工程级证据。
- 边缘掠过路径能得到较高靶区压力。
- 真实厚颅骨路径暴露严重入颅热点和靶区递送不足。

当前不能说：

- 已获得可靠的真正经颅聚焦基线。
- 当前结果达到论文级数值收敛。
- 当前 MI、温升或 CEM43 能支持临床安全结论。
- `simple_hu300` 或其他映射 profile 已经被验证为默认方案。

## 关联项目证据

- `outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/`
- `outputs/corrected_pennes_thermal_dx0p5/`
- `outputs/freefield_current_tuned_calibration/`
- `outputs/thick_skull_candidate_runs/079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_pressure_20260710/`
- `outputs/thick_skull_external_validity_079/`
- `outputs/evidence_briefs/focus_optimization/`
