# 参数对齐报告：从搜集表到平台校准

## 1. 使用原则

这份报告供 Codex 后续对话直接读取，用于判断参数是否能进入 `fus-sim` 的默认配置、复现实验或仅作为综述参考。

核心规则：

- `原文明确` 的参数可以进入候选配置，但仍要检查参数定义。
- `README/工具文档明确` 的字段适合对齐代码接口和文件组织。
- `由参数推算` 的字段必须在报告里标注推算过程。
- `二手信息` 和 `待全文复核` 不得作为最终证据。
- BBB、微泡、溶栓、Histotripsy、热消融参数不得直接混入低强度神经调控复现。

## 2. 参数定义统一

### 声压

必须区分：

- `source_pressure`：代码源面或换能器驱动声压。
- `free_field_pressure`：无颅骨水介质或自由场声压。
- `in_situ_pressure`：穿过颅骨后目标区域实际声压。
- `PNP`：peak negative pressure，峰值负压，常用于空化/溶栓/MI。

当前 `1 MPa` 应写为：

> 高鹏皓论文 source/excitation pressure；尚不能等同于目标区 in situ pressure。

### 声强和声功率

必须区分：

- `acoustic_power_W`：总声功率。
- `ISPTA`：spatial-peak temporal-average intensity。
- `ISPPA`：spatial-peak pulse-average intensity。
- `free_field_Isppa`：自由场脉冲平均声强。
- `in_situ_Isppa`：颅内目标区域估计声强。

当前平台如未显式计算 ISPTA/ISPPA，不应把 MPa 直接转写成声强。

### duty cycle

必须区分：

- `pulse_duty_cycle`：单个脉冲周期内开声比例。
- `train_duty_cycle`：一个 train 内脉冲开声比例。
- `protocol_average_duty_cycle`：包含 train 间隔后的整体平均占空比。

当前 `6%` 应保留为高鹏皓协议参数；Pennes 长程热模型应优先使用 `protocol_average_duty_cycle`。

### 频率

`500 kHz` 是合理 baseline，不是唯一共识。

建议平台频率字段支持：

- `frequency_hz`
- `frequency_source`：例如 `Gao2022_local`, `Legon2014`, `current_tuned`
- `frequency_role`：`baseline`, `sweep`, `review_only`

## 3. 当前参数状态

| 参数 | 当前状态 | 是否保留 | 下一步 |
|---|---|---:|---|
| 500 kHz | 文献常见范围内；Gao/Legon/TUSX 都支持 | 是 | 加入 270/300/650 kHz 扫描计划 |
| 1 MPa | Gao source pressure；定义需复核 | 暂保留 | 报告中改名为 `source_pressure_mpa` |
| 6% duty | Gao 协议特例 | 仅热协议保留 | 不作为默认 neuromodulation duty |
| PRF 300 Hz | Gao 协议特例 | 仅热协议保留 | 与 1 kHz/10 Hz 等文献值并列 |
| 67 ms train | Gao 协议特例 | 仅热协议保留 | 与 protocol-average duty 绑定 |
| 2.5 s interval | Gao 协议特例 | 仅热协议保留 | 明确是 train interval |
| aperture 25 / radius 30 mm | Gao transducer baseline | 是 | 自由场焦域校准 |
| aperture 30 / radius 35 mm | current tuned parameter | 暂保留 | 不写成文献共识；做水介质校准 |
| 42°C | 常用粗安全阈值 | 是 | 补 thermal dose/CEM43/skull max |
| HU >= 300 | 当前 baseline | 是 | 继续报告 250/300/400 HU 敏感性 |

## 4. 证据等级字段

后续所有新增参数行必须包含：

- `evidence_level`
- `source_locator`
- `definition_status`
- `review_status`

建议枚举值：

### evidence_level

- `原文明确`
- `README/工具文档明确`
- `由参数推算`
- `二手信息`
- `待全文复核`

### definition_status

- `source_pressure_not_in_situ`
- `free_field_pressure`
- `in_situ_pressure`
- `peak_negative_pressure`
- `ISPTA`
- `ISPPA`
- `pulse_duty`
- `protocol_average_duty`
- `transducer_geometry`
- `solver_setting`

### review_status

- `usable`
- `usable_with_caution`
- `usable_as_seed_only`
- `review_only`
- `do_not_mix_with_neuromod`
- `needs_fulltext_verification`

## 5. 给下一轮 Codex 的任务建议

下一轮不要继续扩写散文综述，优先做以下结构化工作：

1. 读取 `paper_parameter_matrix.csv/json` 和 `tool_code_matrix.csv/json`。
2. 为当前 `simulate_kwave_3d_focus.py` 的配置生成 `parameter_profile_current.json`。
3. 生成 `parameter_profile_gao2022_baseline.json`。
4. 生成 `parameter_profile_current_tuned_079.json`。
5. 实现自由场校准报告：水介质中检查 aperture/radius/focus/peak。
6. 把所有报告都输出 `source_pressure`、`free_field_peak`、`target_window_peak`，不要混写为一个 pressure。

