# 下一阶段统一路线优先级

> 适用对象：Codex、Antigravity、Claude 或任何接手 `fus-sim` 的新对话。  
> 目的：防止多个方向同时发散，明确下一阶段的推进顺序和硬约束。

## 核心判断

根据当前 `fus-sim` 状态和相似平台经验，下一阶段不应继续散开多个新模块，而应按“先收束、再扩展”的顺序推进。

## 推荐顺序

### 1. 先收束当前 CT-HU continuous mapping 工作

当前工作区已有与 CT-HU 连续颅骨映射相关的未提交改动，例如：

- `build_ct_acoustic_model.py`
- `generate_module_evidence_brief.py`
- `acoustic_mapping_profiles/continuous_skull.json`
- `compare_continuous_vs_binary.py`

在这些改动完成验证、gap feedback、状态记录和 Git 提交前，不建议继续新开大模块。

验收标准：

- continuous mapping 的证据等级和适用边界写清楚。
- 二值模型与连续模型对比结果可复查。
- 不覆盖已有 079 best、Visible Human、Pennes 或原始 CT 数据。
- 未完成项明确写入 `gap_feedback` 或 handoff 文档。

### 2. 再做方案 A：PlanTUS-style 几何启发式筛选

目标：减少无意义 k-Wave 候选运行，让 target/entry/source 规划更像工程平台而不是盲扫。

建议实现：

- 在现有或新增 planning 流程中加入几何代理指标：
  - skull path length
  - incidence angle
  - source safety counts
  - source-to-target distance
  - quick voxel estimate
  - heuristic transmission proxy
- 默认只输出 ranking、CSV/JSON 和 recommended top candidates。
- 默认不批量跑 k-Wave。
- 只在用户明确授权后，对 top 1 或 top 2 做 dry-run-quality，再考虑实际仿真。

注意：

- `exp(-alpha_skull * d) * cos(theta)` 只能叫 heuristic proxy，不可写成精确透射率。
- 该方向借鉴 PlanTUS/TUSX/CoperniFUS 的规划思想，但仍需 k-Wave 或声场模型复核。

### 3. 之后做方案 B：Gao 2022 BHTE 分段热图复刻

目标：生成适合汇报和论文复刻的热安全图表。

建议实现：

- 优先复用或包装现有 `simulate_pennes_bioheat.py`。
- 不建议新写一个与现有热模型割裂的完整热求解器。
- 输出 5 s 升温 + 15 s 降温的标准科研图：
  - focal max temperature curve
  - skull max temperature curve
  - heating/cooling phase marker

注意：

- 这一步主要增强“论文复刻图表”和“热安全表达”，不是当前规划效率瓶颈。

### 4. MRI-CT 配准与真实靶点映射放中后期

目标：未来提高临床/解剖靶点真实性。

当前不建议直接从零实现互信息自动配准。更稳路线：

1. 先生成 `mri_ct_registration` evidence brief。
2. 优先支持外部配准矩阵导入。
3. 支持手动 landmark 或已知 affine。
4. 后续再考虑 SimpleITK/ANTs/FSL 等成熟工具。

原因：

- 当前缺少稳定的同病例 MRI + CT 数据。
- 手写互信息刚体配准风险较高。
- 靶点配准错误会污染后续所有声场结论。

## 硬约束

- 所有方案都必须 Evidence Brief 先行。
- 所有真实 k-Wave 运行前必须 `--dry-run-quality`。
- 所有执行后必须写 gap feedback 或 handoff 记录。
- 不覆盖 `data/raw_ct/` 和已验证输出。
- 不把 BBB、微泡、血栓、Histotripsy、热消融参数直接混入神经调控 baseline。
- quick/cropped-domain 结果不能写成 paper-grade reproduction 或医学安全结论。

## 给新 Agent 的一句话指令

```text
请先读取 AGENTS.md、ACTIVE_WORK.md、HANDOFF_LOG.md、EVIDENCE_DRIVEN_DEVELOPMENT.md 和 NEXT_ROUTE_PRIORITY.md。当前阶段必须先收束 CT-HU continuous mapping，再做 PlanTUS-style 几何启发式筛选；不要在未完成 gap feedback 和 dry-run 门控前启动新的 k-Wave 仿真。
```

