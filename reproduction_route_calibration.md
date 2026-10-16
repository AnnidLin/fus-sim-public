# 复现路线校准：工程跑通到论文级复现

## 0. 当前阶段判断

`fus-sim` 已经完成“工程跑通”：

- CT/NIfTI/DICOM 到 3D 声学模型。
- quick 3D k-Wave 声压仿真。
- target/entry 候选筛选。
- source safety 检查。
- Pennes 热模型。
- 079 病例 tuned best。
- Visible Human 公开 CT quick pipeline。

但尚未达到“论文级复现”：

- 缺自由场/水槽校准。
- 缺换能器 profile 级校准。
- 缺 CT-HU 映射 profile。
- 缺 PPW/PML/CFL/网格收敛报告。
- 缺相位校正。
- 缺多病例统计。

## 1. 推荐阶段路线

### Stage 1：结构化参数层

目标：让平台参数可追溯、可比较。

新增或维护：

- `paper_parameter_matrix.csv`
- `paper_parameter_matrix.json`
- `tool_code_matrix.csv`
- `tool_code_matrix.json`
- `parameter_alignment_report.md`

验收：

- 每个默认参数都能追踪到 evidence_level 和 source_locator。
- 每个声压字段都说明 source/free-field/in-situ/PNP。

### Stage 2：自由场/水槽校准

目标：先验证换能器几何和声源模型，不直接上颅骨。

推荐配置：

- Gao baseline：500 kHz，aperture 25 mm，radius 30 mm。
- Current tuned：500 kHz，aperture 30 mm，radius 35 mm。

输出：

- free-field pressure map。
- axial/lateral profile。
- focus coordinate。
- FWHM / focal region estimate。
- peak pressure relative to source pressure。

对齐参考：

- TUSX water tank validation。
- Jin/Kranion hydrophone scan workflow。

### Stage 3：CT-HU 映射校准

目标：从“能生成骨模型”升级到“材料映射可解释”。

需要 profile 化：

- skull threshold：250/300/400 HU。
- density mapping。
- sound speed mapping。
- attenuation mapping。
- cortical/trabecular distinction if available。

输出：

- `acoustic_mapping_profile.json`
- threshold sensitivity report。
- path bone intersection report。

### Stage 4：网格与数值设置报告

目标：使 quick 结果和论文级结果分层。

报告字段：

- dx/dy/dz。
- points per wavelength, PPW。
- PML thickness。
- CFL。
- simulation time。
- CPU/GPU backend。
- memory estimate。
- runtime。

验收：

- quick run 只能叫 `screening`。
- 论文级候选必须有至少一次 finer-grid 或 convergence sanity check。

### Stage 5：经颅 baseline 复现

目标：优先对齐高鹏皓论文的单阵元 CT/k-Wave/热效应路线。

输入：

- Gao baseline parameter profile。
- 一个本地 CT 或 Visible Human case。
- 安全 source placement。

输出：

- pressure field。
- target-window peak。
- effective peak-to-target distance。
- skull max pressure/temperature。
- Pennes protocol-average thermal report。

注意：

- 不能要求 Visible Human 直接复现高鹏皓靶点，因为解剖目标、CT、坐标都不同。
- 应复现“流程和指标”，不是复现其数值。

### Stage 6：entry/target planning 升级

目标：把当前 entry scan 变成 PlanTUS-style 可解释规划。

加入指标：

- skin-to-target distance。
- target accessibility。
- required transducer tilt。
- skin/skull normal angle mismatch。
- air/sinus/ear/eye avoidance。
- beam-target overlap proxy。

输出：

- ranked entry CSV。
- candidate geometry report。
- exportable transform/profile。

### Stage 7：相位校正

目标：当 single bowl 路线稳定后，再进入相控阵/phase correction。

参考：

- Kranion：ray-based phase correction。
- HAS：rapid phase correction。
- Sun/Pan local theses：time reversal / cross-correlation phased-array excitation。

不要提前做：

- 在自由场和材料映射没校准前，不建议直接实现复杂 phased array。

## 2. 下一步最小可执行任务

推荐下一轮 Codex 执行：

1. 生成 `parameter_profile_gao2022_baseline.json`。
2. 生成 `parameter_profile_current_tuned_079.json`。
3. 增加自由场校准脚本或复用现有 3D quick 脚本水介质模式。
4. 输出 `outputs/free_field_calibration_gao2022/`。
5. 输出 `outputs/free_field_calibration_current_tuned/`。
6. 写 `free_field_calibration_report.md`。

## 3. 暂停事项

以下方向先暂停，不作为下一步主线：

- 继续盲调 Visible Human 左侧 target/entry。
- 把 BBB 微泡 MI 参数混进神经调控默认配置。
- 把溶栓 -6/-8 MPa 阈值作为 low-intensity target。
- 直接上 AI surrogate 替代物理仿真。
- 未做自由场校准就讨论临床安全结论。

## 4. 给其他对话的读取顺序

后续 Codex 对话应按这个顺序读取：

1. `ACTIVE_WORK.md`
2. `literature_code_review_collection_result.md`
3. `parameter_alignment_report.md`
4. `reproduction_route_calibration.md`
5. `paper_parameter_matrix.csv`
6. `tool_code_matrix.csv`

