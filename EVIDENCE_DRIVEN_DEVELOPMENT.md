# 证据驱动开发层

## 目的

`fus-sim` 后续不再只按经验继续调参或堆脚本。每新增一个模块、默认参数、仿真 preset 或报告结论，都必须先把论文证据、公开工具参考和当前平台差距整理成 evidence brief，再决定实现方式和验收标准。

## 标准闭环

每个模块开发前必须先完成前三步；执行后再单独记录反馈：

1. **Evidence Scan**：从 `paper_parameter_matrix.*`、`tool_code_matrix.*`、`parameter_alignment_report.md`、`reproduction_route_calibration.md` 中筛选相关论文、参数和公开工具。
2. **Consensus / Divergence**：写清楚哪些参数可作为 baseline，哪些只是特定论文协议，哪些方向不能混入当前低强度神经调控 tFUS。
3. **Platform Decision**：把证据转成工程决策，包括参数命名、默认值、profile、输出指标和报告措辞。
4. **Gap Feedback**：执行后再记录实际结果、偏差、失败、风险变化、调整建议和下一步校准路线。

## Evidence Brief 与 Gap Feedback 分离

执行前证据输出固定为：

```text
outputs/evidence_briefs/<module>/evidence_brief.md
outputs/evidence_briefs/<module>/evidence_brief.json
```

`evidence_brief` 只能记录执行前证据、参数共识、参数分歧、当前平台已有能力、当前平台缺口、推荐工程决策、风险、检查点和验收标准。

执行后反馈输出固定为：

```text
outputs/evidence_briefs/<module>/gap_feedback.md
outputs/evidence_briefs/<module>/gap_feedback.json
```

`gap_feedback` 才记录执行后的结果、偏差、失败、超时、验证输出、调节策略和后续建议。不要把执行后结果写成执行前证据，也不要用执行后 quick 结果倒推成默认参数证据。

## Evidence Brief 必填内容

每个 brief 至少包含：

- 模块名称
- 模块目标
- 相关论文
- 相关公开工具
- 参数共识
- 参数分歧
- 当前平台已有内容
- 当前平台缺口
- 推荐实现决策
- 不应混用的参数或方向
- 验收标准
- 风险与检查点
- 下一步建议

机器可读 JSON 至少包含：

```json
{
  "brief_type": "evidence_brief_pre_execution",
  "module": "freefield_calibration",
  "goal": "",
  "related_papers": [],
  "related_tools": [],
  "consensus": [],
  "divergence": [],
  "platform_current_state": [],
  "platform_gaps": [],
  "recommended_decisions": [],
  "do_not_mix": [],
  "acceptance_criteria": [],
  "risks": [],
  "next_steps": [],
  "post_execution_feedback_outputs": [
    "outputs/evidence_briefs/<module>/gap_feedback.md",
    "outputs/evidence_briefs/<module>/gap_feedback.json"
  ]
}
```

## 禁止混用规则

- BBB、微泡、血栓、Histotripsy、热消融参数不得直接写入低强度神经调控 baseline。
- `1 MPa` 必须标为 source/excitation pressure，不能直接等同 free-field pressure 或 target in-situ pressure。
- `6% duty / 300 Hz / 67 ms / 2.5 s` 是 Gao protocol，不是通用 tFUS 协议。
- `ap30/r35` 是当前 079 tuned 参数，不是文献共识。
- quick / cropped-domain 结果只能用于 screening 和流程验证，不能写成 paper-grade reproduction。

## 负反馈调节要求

长任务必须遵守 `AGENTS.md` 的负反馈调节规则：

- 开始前写明目标、成功标准、预计耗时、检查点和主要风险。
- 执行中持续比较实际状态和预期状态。
- 出现超时、无输出、报错、测试失败、需求偏差、上下文不足、重复尝试无效、方案复杂度过高或修改范围失控时，必须先收集证据再调整策略。
- 调整策略可以是缩小范围、拆分任务、换命令、补充验证、复用现有模式、撤回自己造成的错误改动、重新估计时间或请求用户决策。
- 等待必须有目的、时间预算、检查点和退出条件。

## 推荐工作流

```powershell
D:\AIprogram\python-envs\kwave312\Scripts\python.exe generate_module_evidence_brief.py --module freefield_calibration --output-dir outputs\evidence_briefs\freefield_calibration
```

后续模块也应先生成 brief：

```powershell
D:\AIprogram\python-envs\kwave312\Scripts\python.exe generate_module_evidence_brief.py --module ct_hu_mapping --output-dir outputs\evidence_briefs\ct_hu_mapping
D:\AIprogram\python-envs\kwave312\Scripts\python.exe generate_module_evidence_brief.py --module thermal_safety --output-dir outputs\evidence_briefs\thermal_safety
D:\AIprogram\python-envs\kwave312\Scripts\python.exe generate_module_evidence_brief.py --module entry_planning --output-dir outputs\evidence_briefs\entry_planning
```

## 当前优先级

当前已完成参数证据层、自由场 quick 校准和 CT-HU mapping profile 化。下一阶段应先生成 `kwave_simulation_quality` evidence brief，再进入 `simulation_presets.json` 与 k-Wave summary 数值质量字段实现。
