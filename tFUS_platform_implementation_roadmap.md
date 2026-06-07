# tFUS 仿真平台搭建路线图：从文献/公开代码参考到自有平台

> 目的：把“论文参数对照 + 公开代码参考 + 当前 fus-sim 工程基础”整合成一条可执行路线，后续主对话可以按本文继续搭建平台。

## 0. 总目标

最终目标不是简单复刻某一篇论文或某一个开源项目，而是搭建一个属于本项目自己的 tFUS 仿真平台：

- 能读取本地 CT/NIfTI/DICOM 和后续 pseudo-CT/MRI 派生数据。
- 能生成可解释的声学介质模型。
- 能规划 target、entry、source，并检查源面安全。
- 能运行 quick screening 和更高精度 paper-grade 两层声场仿真。
- 能输出焦域指标、热安全指标、病例报告和多病例汇总。
- 每个默认参数都能追溯到论文、公开工具或当前调参记录。

核心原则：

1. 论文给参数边界，公开代码给工程组织方式，我们自己的平台负责整合和验证。
2. 不把 BBB、微泡、血栓、Histotripsy、热消融参数直接混入低强度神经调控 tFUS。
3. quick 模型只用于筛选和流程验证；论文级结论必须经过自由场校准、网格报告和更高精度复核。
4. 每次新增模块都回答三个问题：参考了哪篇论文？借鉴了哪个工具？解决了当前平台哪个缺口？

## 1. 当前基础

当前 `fus-sim` 已经具备：

- CT/NIfTI/DICOM 到 3D 声学模型。
- 3D k-Wave quick pressure 仿真。
- target/entry 候选筛选。
- source safety 检查。
- Pennes 热模型、protocol-averaged duty、显式脉冲和 dose scan。
- 079 病例 tuned best。
- Visible Human 公开病例 quick pipeline。
- 多病例 manifest/QC/batch build/smoke/refinement 骨架。
- 文献与代码对照矩阵：
  - `paper_parameter_matrix.csv/json`
  - `tool_code_matrix.csv/json`
  - `parameter_alignment_report.md`
  - `reproduction_route_calibration.md`

当前主要缺口：

- 自由场/水槽校准。
- 换能器模型校准。
- CT-HU 到声学参数映射 profile 化。
- PPW/PML/CFL/网格收敛报告。
- 更真实的靶点选择。
- 多病例同流程复核。
- 相位校正或 phased-array 支持。

## 2. 参考体系如何使用

### 2.1 论文参考

论文不直接变成代码，而是进入参数证据层。

每条参数应记录：

- `paper_id`
- `application`
- `parameter_name`
- `value`
- `unit_or_definition`
- `evidence_level`
- `source_locator`
- `definition_status`
- `review_status`

优先使用方式：

- 高鹏皓论文：单阵元 CT/k-Wave/热效应 baseline。
- Legon/Lee/Mueller 等 neuromodulation 文献：人类 tFUS 参数范围参考。
- Leung/HAS/Jin/Kranion：快速声束、相位校正、水槽/水听器验证参考。
- Pan/Sun/BBB/Histotripsy：综述和未来模块参考，不作为当前神经调控默认参数。

### 2.2 公开代码参考

公开工具不直接照搬，而是拆成可借鉴模块：

| 工具 | 借鉴重点 | 在 fus-sim 中的落点 |
|---|---|---|
| TUSX | NIfTI 坐标、单阵元 k-Wave、水槽验证 | 自由场校准、单阵元 baseline |
| PRESTUS | preprocessing -> acoustic -> heating -> report pipeline | 项目目录结构、报告字段、参数 profile |
| BabelBrain | GUI 级输入输出、热协议、换能器 profile | 热安全报告、transducer profile |
| PlanTUS | target/entry 几何规划、avoidance | target/entry planner 升级 |
| Kranion | 相位校正、射线可视化、水听器验证 | 后续 phased-array/phase correction |
| HAS/RapidBeam | 快速预估和热数据校准 | k-Wave 前的快速筛选或对照 |
| TFUScapes | 数据集组织和批量仿真管理 | 多病例数据组织和输出格式 |

## 3. 平台模块化设计

建议把平台拆成以下模块，每个模块独立输入输出，避免脚本越写越乱。

### Module A：知识与参数证据层

目标：让平台默认参数有来源。

输入：

- `paper_parameter_matrix.csv/json`
- `tool_code_matrix.csv/json`
- 当前仿真 summary

输出：

- `parameter_profile_default.json`
- `parameter_source_report.md`
- `unsupported_or_uncertain_parameters.md`

成功标准：

- `500 kHz` 标记为 baseline frequency。
- `1 MPa` 标记为 source pressure，不误写成 in situ pressure。
- `6% duty / 300 Hz / 67 ms / 2.5 s` 标记为 Gao protocol，而不是通用 tFUS 协议。
- `ap30/r35` 标记为 current tuned parameter。

建议脚本：

- `generate_platform_parameter_profile.py`

### Module B：自由场/水槽校准层

目标：先验证换能器模型，不直接上颅骨。

参考：

- TUSX water tank validation。
- Jin/Kranion hydrophone scan 思路。

实现内容：

- 新增 `simulate_freefield_transducer.py`。
- 支持 `--aperture-mm`、`--radius-mm`、`--frequency-khz`、`--source-pressure-mpa`。
- 运行均匀水/软组织介质。
- 输出轴向曲线、横向曲线、焦点位置、FWHM、峰值声压。

输出：

- `outputs/freefield_calibration/ap25_r30_f500/`
- `outputs/freefield_calibration/ap30_r35_f500/`
- `freefield_summary.json`
- `axial_profile.csv/png`
- `lateral_profile.csv/png`

成功标准：

- 几何焦点接近曲率半径附近。
- `ap25/r30` 和 `ap30/r35` 的焦点、焦域宽度、峰值差异可解释。
- 后续经颅仿真使用的 transducer 参数先经过 free-field sanity check。

风险与检查点：

- 如果全局峰值贴源面，使用 target/focal-region 指标，不直接判失败。
- 如果焦点明显偏离几何焦区，先修 source mask 和相位/延迟定义。

### Module C：CT-HU 声学映射 profile 层

目标：把现在的硬编码阈值变成可复核材料配置。

参考：

- 高鹏皓、Pan/Sun 的 HU/孔隙率映射。
- PRESTUS continuous skull mapping。
- Leung/RapidBeam 对 HU attenuation 的强调。
- pseudo-CT 工具的密度/骨映射思想。

实现内容：

- 新增 `acoustic_mapping_profiles/`。
- 每个 profile 写成 JSON：
  - `bone_threshold_hu`
  - `air_threshold_hu`
  - `soft_tissue_speed`
  - `skull_speed_mapping`
  - `density_mapping`
  - `attenuation_mapping`
  - `evidence_source`

建议文件：

- `acoustic_mapping_profiles/gao_binary_hu300.json`
- `acoustic_mapping_profiles/simple_hu250.json`
- `acoustic_mapping_profiles/simple_hu300.json`
- `acoustic_mapping_profiles/continuous_skull_draft.json`

修改脚本：

- `build_ct_acoustic_model.py --mapping-profile acoustic_mapping_profiles/simple_hu300.json`

成功标准：

- 每个 CT 模型 summary 记录使用了哪个 mapping profile。
- 250/300/400 HU 分割差异可复现。
- 后续报告能说明材料参数不是凭空写死。

### Module D：target/entry planning 层

目标：从“能找到一个入口”升级为 PlanTUS-style 可解释规划。

参考：

- PlanTUS 的 entry/target 候选、avoidance regions、几何约束。
- 当前已有 `plan_ct_target_entry.py`、`scan_ct_entry_positions.py`、source safety。

实现内容：

- 支持多方向：`left_x/right_x/anterior/posterior/superior`。
- 增加几何指标：
  - source-to-target distance
  - skull path length
  - incidence angle
  - source safety counts
  - crop voxel count
  - air/sinus/eye/ear avoidance proxy
- 输出 ranked candidates，不默认跑 k-Wave。

建议脚本：

- 扩展 `scan_ct_entry_positions.py`
- 或新增 `plan_case_entry_candidates.py`

成功标准：

- 对每个病例能生成 top 5 source-safe entry candidates。
- 默认不启动 k-Wave。
- 推荐命令清晰可复制。

### Module E：声场仿真层

目标：建立 quick / standard / paper 三档仿真。

当前基础：

- `simulate_kwave_3d_focus.py`
- `analyze_kwave_3d_focus.py`

建议分层：

| 档位 | 用途 | 特征 |
|---|---|---|
| `smoke` | 流程是否能跑通 | 小 crop、短时长、低成本 |
| `quick` | 候选筛选 | 自动传播时间、焦域指标、source safety |
| `standard` | 论文前候选复核 | 更大 crop、更完整时间窗、完整报告 |
| `paper` | 论文级复现 | PPW/PML/CFL/网格收敛/GPU 或 HPC |

实现内容：

- 新增 `simulation_presets.json`。
- 每次仿真 summary 记录：
  - preset
  - dx
  - PPW
  - CFL
  - PML
  - grid size
  - runtime
  - source profile
  - mapping profile

成功标准：

- 报告中明确写出“这是 quick screening，不是论文级结论”。
- 论文级候选至少有一次 finer grid sanity check。

### Module F：热模型与剂量层

目标：保留当前热模块，同时让协议定义更清楚。

当前基础：

- `simulate_pennes_bioheat.py`
- `scan_pennes_sensitivity.py`
- `scan_pennes_protocol_dose.py`

下一步：

- 把 thermal material profile JSON 化。
- 增加 skull max、brain target、target-window、CEM43 或简化热剂量指标。
- 报告明确区分：
  - explicit pulse
  - protocol-averaged
  - constant averaged conservative upper bound

成功标准：

- 每个热结果都能说明使用的 pulse mode。
- 不把 constant averaged 误读成真实协议温升。

### Module G：多病例与报告层

目标：让平台能随着病例增加自动扩展。

当前基础：

- `inventory_ct_cases.py`
- `validate_ct_case.py`
- `batch_build_ct_models.py`
- `prepare_case_quick_pressure.py`
- `summarize_quick_pressure_runs.py`
- `prepare_case_refinement_plan.py`
- `generate_multicase_stage_report.py`

下一步：

- 对每个病例输出统一 case package：
  - `case_manifest.json`
  - `ct_qc.json`
  - `acoustic_model_summary.json`
  - `entry_plan.json`
  - `pressure_metrics.json`
  - `thermal_metrics.json`
  - `case_report.md`

成功标准：

- 新病例放入 `data/raw_ct/` 后，可以走 manifest -> QC -> model -> plan -> single smoke。
- 批量流程默认不跑 k-Wave，避免无意长时间计算。

### Module H：相位校正与高级求解层

目标：为后续 phased-array 或更接近论文级工具做准备。

参考：

- Kranion。
- HAS。
- Leung 2019/2021。
- BabelBrain/BabelViscoFDTD。

短期不直接实现完整 phased-array，但要预留接口：

- `phase_correction_profile.json`
- `transducer_array_profile.json`
- `element_positions`
- `element_phases`
- `element_amplitudes`

成功标准：

- 当前 single bowl 代码不阻碍未来 element-wise source。
- entry/target planner 能输出适合相位校正的路径信息。

## 4. 推荐执行顺序

### 第一阶段：把文献证据接入平台

预计 1-2 小时。

任务：

1. 新增 `generate_platform_parameter_profile.py`。
2. 读取 `paper_parameter_matrix.csv/json` 和 `tool_code_matrix.csv/json`。
3. 输出：
   - `outputs/parameter_profiles/platform_parameter_profile.json`
   - `outputs/parameter_profiles/platform_parameter_source_report.md`
4. 更新 README 和任务总结。

验收：

- 当前默认参数都有来源标签。
- 不确定参数被列入 `needs_calibration`。

### 第二阶段：自由场/水槽校准

预计 2-4 小时。

任务：

1. 新增 `simulate_freefield_transducer.py`。
2. 跑 `ap25/r30/f500`。
3. 跑 `ap30/r35/f500`。
4. 生成对比报告。

验收：

- 明确哪个换能器参数作为 Gao baseline。
- 明确哪个是 current tuned。
- 后续经颅仿真不再直接跳过自由场检查。

### 第三阶段：CT-HU 映射 profile 化

预计 2-3 小时。

任务：

1. 新增 `acoustic_mapping_profiles/`。
2. 改 `build_ct_acoustic_model.py` 支持 `--mapping-profile`。
3. 用 079 重建一次 profile-based 模型，不覆盖旧 best。
4. 生成 mapping 对比报告。

验收：

- 每个模型都知道自己的 HU/材料来源。
- 250/300 HU 对照可复现。

### 第四阶段：标准化 quick/standard/paper preset

预计 1-2 小时。

任务：

1. 新增 `simulation_presets.json`。
2. 让 `simulate_kwave_3d_focus.py` 支持 `--preset smoke|quick|standard|paper`。
3. summary 自动记录 PPW/PML/CFL/网格信息。

验收：

- 报告能自动说明当前仿真等级。
- quick 结果不会被误称为论文级复现。

### 第五阶段：病例级复现包

预计 2-4 小时。

任务：

1. 生成 `case_package` 目录结构。
2. 079 作为第一个完整 case package。
3. Visible Human female 作为公开病例流程包。

验收：

- 给导师/师姐看一个病例文件夹，就能理解输入、参数、结果、限制。

## 5. 近期不要做的事

暂时不要：

- 继续盲目扩大 Visible Human 左侧 target 扫描。
- 把 BBB/Histotripsy 的高压或 MI 参数用于神经调控 baseline。
- 直接声称当前 079 tuned result 是论文级复现。
- 自动批量跑多个 k-Wave 3D。
- 直接追求 phased-array，除非先完成 single bowl 的自由场和 CT-HU 校准。

## 6. 下一步建议给主对话的直接指令

可以直接复制下面这段作为下一步任务：

```text
PLEASE IMPLEMENT THIS PLAN:

# 下一步：把文献/公开代码参数矩阵接入 fus-sim 平台配置

目标：新增平台参数证据层，让当前默认参数都能追溯到论文或公开工具。

新增脚本 `generate_platform_parameter_profile.py`：
- 读取 `paper_parameter_matrix.csv/json`
- 读取 `tool_code_matrix.csv/json`
- 汇总当前平台关键参数：
  - frequency
  - source_pressure
  - aperture/radius
  - duty/PRF/train/inter-train
  - CT bone threshold
  - thermal threshold
  - simulation level
- 为每个参数输出：
  - value
  - unit
  - current_role: baseline / tuned / quick_approx / needs_calibration
  - evidence_level
  - source_locator
  - definition_status
  - review_status
  - next_action

输出到：
- `outputs/parameter_profiles/platform_parameter_profile.json`
- `outputs/parameter_profiles/platform_parameter_source_report.md`

要求：
- 中文报告。
- 不运行 k-Wave。
- 不修改已有声场/热结果。
- 明确写出：500 kHz 是 baseline；1 MPa 是 source pressure；ap30/r35 是 current tuned；6% duty/300 Hz/67 ms/2.5 s 是 Gao protocol，不是领域通用共识。
```

## 7. 最终判断

按照现在这条路线，搭建属于自己的 tFUS 仿真平台是可行的。

当前最重要的转变是：

- 以前是“能不能跑起来”。
- 现在要变成“每个参数、每个模块、每个输出是否有文献/代码/验证依据”。

这会让平台从工程 demo 逐步变成可解释、可复核、可扩展的研究工具。
