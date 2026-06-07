# fus-sim Agent 执行规则

本文件是项目级执行纪律。任何新对话、接力代理或自动化脚本在修改本仓库前，都应先读取本文件。

## 负反馈调节

复杂任务默认采用负反馈调节，而不是机械按计划推进。

每个任务开始前必须写明：

- 目标
- 成功标准
- 预计耗时
- 检查点
- 主要风险
- 停止条件

执行中持续比较实际状态与目标/预期状态。偏差包括但不限于：

- 超时
- 无输出
- 报错
- 测试失败
- 结果偏离预期
- 需求理解偏差
- 上下文不足
- 重复尝试无效
- 方案复杂度过高
- 体验或性能变差
- 修改范围失控

发现偏差时，先基于日志、summary、输出文件、测试结果、页面表现或代码证据获取事实，再调整策略。可选调整包括缩小范围、拆分任务、换命令、补充验证、复用现有模式、撤回自己造成的错误改动、重新估计时间，或在需要用户决策/授权时询问用户。

等待必须有目的、时间预算、检查点和退出条件。多次无法收敛时，停止重复尝试，并说明当前偏差、已尝试的调节、剩余不确定性和建议下一步。

## Evidence Brief 先行

任何新模块实现前，必须先生成 evidence brief。默认输出位置为：

```text
outputs/evidence_briefs/<module>/evidence_brief.md
outputs/evidence_briefs/<module>/evidence_brief.json
```

没有 evidence brief，不允许直接实现新模块、引入新默认参数或启动长耗时仿真。

`evidence_brief` 只能记录执行前证据、参数共识、参数分歧、当前平台差距、推荐工程决策、风险和验收标准。执行后的结果、偏差、失败和调整建议必须写入：

```text
outputs/evidence_briefs/<module>/gap_feedback.md
outputs/evidence_briefs/<module>/gap_feedback.json
```

不要把执行后结果伪装成执行前证据。

## 默认参数必须可追溯

任何默认参数都必须能追溯到以下至少一个来源：

- `paper_parameter_matrix.csv`
- `tool_code_matrix.csv`
- `parameter_alignment_report.md`
- `reproduction_route_calibration.md`
- 当前平台已有 summary/report

关键边界：

- `500 kHz` 可作为 Gao baseline，但不是领域唯一共识。
- `1 MPa` 必须标记为 source/excitation pressure，不能写成 free-field pressure 或 target in-situ pressure。
- `ap25/r30` 是 Gao baseline transducer。
- `ap30/r35` 是 current 079 tuned parameter，不是论文共识。
- `6% duty / 300 Hz / 67 ms / 2.5 s` 是 Gao protocol，不是通用 tFUS 协议。
- quick/cropped-domain 结果只能用于 screening 和流程验证，不能写成 paper-grade reproduction。

## 仿真分层

后续 k-Wave 仿真必须显式标记 preset 层级：

- `smoke`：只验证脚本、I/O、source/sensor/medium 能跑通。
- `quick`：用于候选筛选和趋势比较，不用于论文级结论。
- `standard`：记录 PPW、PML、CFL、grid size、runtime、backend、memory estimate，并至少做基础数值质量复核。
- `paper-grade`：需要网格收敛、边界/PML 复核、运行环境记录、参数来源审计，以及与论文或公开工具的可解释对照。

任何 summary 都应尽量记录 preset、dx、PPW、PML、CFL、grid size、runtime、backend 和 memory estimate。

## 长任务和 k-Wave 规则

禁止盲跑 k-Wave。运行 k-Wave 前必须确认：

- 已有对应模块 evidence brief。
- 本轮任务明确需要仿真。
- 已估计运行时间和输出检查点。
- 已定义停止条件。
- 输出目录不会覆盖已验证结果。

长耗时 k-Wave 优先通过 `run_kwave_command.py` 运行。该 runner 默认只生成计划，只有显式 `--execute` 才允许真实执行；运行前必须先通过 `--dry-run-quality`。除非用户明确要求调试启动机制，不要再用 `Start-Process` 或 PowerShell Job 作为默认入口。

长任务默认每 2 分钟检查一次输出目录、日志或进程状态。若超过预设硬停止时间仍无 `summary.json`、核心输出或明确进展，必须停止等待并重新评估，而不是继续空等。

## 禁止混用方向

BBB、微泡、血栓、Histotripsy、热消融等高强度或不同应用方向的参数，不得直接混入当前低强度神经调控 baseline。若未来要支持这些方向，必须单独建立 evidence brief、参数 profile 和风险说明。

## Evidence Governance Entry Point

Future Codex, Antigravity, or Claude agents must treat the governance layer as durable project memory.

- Read `EVIDENCE_GOVERNANCE.md` before changing project direction.
- Read `outputs/evidence_registry/evidence_registry.json` before choosing the next task.
- Current maturity is `M2_standard_engineering_baseline_hardening`, not paper-grade.
- The current allowed claim is a runner-gated `simple_hu300` standard engineering pressure output for 079 `candidate_006`, dx0.75, PML12.
- Blocked claims remain: validated pressure baseline, paper-grade reproduction, medical/safety conclusion, source-backed alpha pressure eligibility, and default profile promotion.
- Next preferred task is a read-only CFL/environment gate, then refresh the evidence registry.
- Do not run additional pressure unless a gate and the user explicitly authorize exactly one run.
