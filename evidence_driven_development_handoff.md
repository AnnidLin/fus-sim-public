# 证据驱动开发层交接说明

> 用途：供新的 Codex 对话直接读取，继续把 `fus-sim` 从“能跑的 quick 仿真平台”升级为“有论文和公开代码依据、能持续校准的 tFUS 仿真平台”。

## 0. 背景

当前 `fus-sim` 已经完成了工程层面的主要闭环：

- CT/NIfTI/DICOM 到 3D 声学模型。
- 3D k-Wave quick 声场仿真。
- target/entry 候选筛选。
- source safety 检查。
- Pennes 热模型、protocol-averaged duty、显式脉冲、多 train dose scan。
- 079 病例 tuned best。
- Visible Human 公开病例 quick pipeline。
- 多病例 manifest/QC/batch build/smoke/refinement 骨架。

同时已经新增了文献和公开代码对照材料：

- `paper_parameter_matrix.csv`
- `paper_parameter_matrix.json`
- `tool_code_matrix.csv`
- `tool_code_matrix.json`
- `parameter_alignment_report.md`
- `reproduction_route_calibration.md`
- `literature_tFUS_review/07_tFUS文献与公开代码参数对照.md`
- `literature_tFUS_review/08_参数对齐报告.md`
- `literature_tFUS_review/09_复现路线校准.md`
- `tFUS_platform_implementation_roadmap.md`

但目前还没有真正形成：

> 每做一个模块，都先从论文和公开代码里提取证据，再对比当前平台差距，最后决定怎么实现和怎么验收。

因此下一步要新增“证据驱动开发层”。

## 1. 核心目标

让平台后续每次开发都按以下闭环执行：

1. **Evidence Scan**  
   针对当前模块，筛选相关论文和公开工具。

2. **Consensus / Divergence**  
   总结参数共识、分歧和不能混用的实验方向。

3. **Platform Decision**  
   把证据转成平台设计决策，例如参数命名、默认值、profile、输出指标。

4. **Gap Feedback**  
   明确当前平台已有内容、缺口、风险、下一步校准路线。

这一步的意义是：  
不再凭感觉继续调参或写脚本，而是让论文、公开代码和当前平台状态一起驱动工程决策。

## 2. 为什么需要这一步

用户的真实目标不是单纯复现某一篇论文，而是：

- 综合多篇论文的实验内容和参数范围。
- 搜集和参考公开源代码/工具。
- 对比这些论文和工具与当前平台的差距。
- 最终搭建一个属于自己可用、可维护、可解释的 tFUS 仿真平台。

当前已有的文献矩阵是基础，但它还只是“资料库”。  
下一步要把它变成“工程决策引擎”。

## 3. 下一步需要实现的内容

### 3.1 新增 `EVIDENCE_DRIVEN_DEVELOPMENT.md`

这个文件用于规定项目后续开发规则。

内容应包括：

- 每个模块实现前必须先生成 evidence brief。
- evidence brief 必须包含相关论文、公开工具、共识、分歧、当前平台缺口、推荐决策。
- 不允许把 BBB、微泡、血栓、Histotripsy、热消融参数直接混入低强度神经调控 tFUS baseline。
- quick 结果只能用于 screening，不可直接称为论文级复现。
- 每次长任务必须遵守 `AGENTS.md` 的负反馈调节规则：
  - 目标
  - 成功标准
  - 预计耗时
  - 检查点
  - 偏差证据
  - 调整策略
  - 停止条件

### 3.2 新增 `generate_module_evidence_brief.py`

脚本功能：

- 读取：
  - `paper_parameter_matrix.csv`
  - `tool_code_matrix.csv`
  - `parameter_alignment_report.md`
  - `reproduction_route_calibration.md`
- 根据指定模块生成 evidence brief。

支持模块建议：

- `freefield_calibration`
- `ct_hu_mapping`
- `thermal_safety`
- `entry_planning`
- `kwave_simulation_quality`
- `multicase_pipeline`

命令格式：

```powershell
D:\AIprogram\python-envs\kwave312\Scripts\python.exe generate_module_evidence_brief.py --module freefield_calibration --output-dir outputs\evidence_briefs\freefield_calibration
```

输出：

```text
outputs/evidence_briefs/<module>/evidence_brief.md
outputs/evidence_briefs/<module>/evidence_brief.json
```

### 3.3 Evidence brief 必须包含的字段

Markdown 版应包含：

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

JSON 版建议包含：

```json
{
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
  "next_steps": []
}
```

## 4. 第一份 brief：freefield_calibration

第一轮建议先生成：

```powershell
D:\AIprogram\python-envs\kwave312\Scripts\python.exe generate_module_evidence_brief.py --module freefield_calibration --output-dir outputs\evidence_briefs\freefield_calibration
```

这份 brief 必须明确：

- 参考 TUSX 水槽验证思路。
- 参考 Gao 论文的 `500 kHz / aperture 25 mm / radius 30 mm / source pressure 1 MPa`。
- 当前 `aperture 30 mm / radius 35 mm` 是 tuned parameter，不是文献共识。
- `1 MPa` 是 source pressure，不是 free-field pressure，也不是 in situ pressure。
- 下一步自由场校准应输出：
  - axial profile
  - lateral profile
  - focus coordinate
  - FWHM
  - focal region
  - peak pressure relative to source pressure
- 不应直接把 Visible Human 或 079 经颅结果当作换能器模型校准依据。

## 5. 推荐给新对话的执行计划

可以直接把下面这段交给新对话执行：

```text
PLEASE IMPLEMENT THIS PLAN:

# 新增证据驱动开发层

## Summary
当前已有论文参数矩阵和公开工具矩阵，但还没有形成“每做一个模块都先查证据、对比差距、再调整平台”的机制。下一步新增证据驱动开发层，让文献和源代码参考真正进入工程流程。

## Key Changes
1. 新增 `EVIDENCE_DRIVEN_DEVELOPMENT.md`
   - 规定每个模块实现前必须完成：
     - Evidence Scan
     - Consensus / Divergence
     - Platform Decision
     - Gap Feedback
   - 明确 quick screening、standard、paper-grade 的区别。
   - 明确不能混用 BBB/血栓/Histotripsy/热消融参数到神经调控 baseline。

2. 新增 `generate_module_evidence_brief.py`
   - 读取：
     - `paper_parameter_matrix.csv`
     - `tool_code_matrix.csv`
     - `parameter_alignment_report.md`
     - `reproduction_route_calibration.md`
   - 支持模块：
     - `freefield_calibration`
     - `ct_hu_mapping`
     - `thermal_safety`
     - `entry_planning`
     - `kwave_simulation_quality`
     - `multicase_pipeline`
   - 输出：
     - `outputs/evidence_briefs/<module>/evidence_brief.md`
     - `outputs/evidence_briefs/<module>/evidence_brief.json`

3. 先生成第一份 brief：
   - module: `freefield_calibration`
   - 目的：为下一步自由场/水槽校准提供文献和工具依据。

## Commands
```powershell
D:\AIprogram\python-envs\kwave312\Scripts\python.exe generate_module_evidence_brief.py --module freefield_calibration --output-dir outputs\evidence_briefs\freefield_calibration
```

## Test Plan
- `EVIDENCE_DRIVEN_DEVELOPMENT.md` 存在，中文可读。
- `generate_module_evidence_brief.py` 语法检查通过。
- 输出包含：
  - `evidence_brief.md`
  - `evidence_brief.json`
- `freefield_calibration` brief 必须明确：
  - 参考 TUSX 水槽验证。
  - 参考 Gao 的 ap25/r30/f500 参数。
  - 当前 ap30/r35 是 tuned parameter。
  - 1 MPa 是 source pressure，不是 in situ pressure。
  - 下一步应先做自由场焦距、FWHM、轴向/横向曲线校准。
- 本阶段不运行 k-Wave，不改已有仿真结果。
```

## 6. 当前论文数量是否需要增加

短期判断：

- 现在已有论文和工具数量足够开始下一阶段。
- 当前更关键的问题不是继续无差别增加论文，而是把已有论文和工具按模块绑定到工程决策。

后续补论文的原则：

- 如果 `freefield_calibration` brief 显示证据不足，再补水槽/自由场/水听器验证论文。
- 如果 `ct_hu_mapping` brief 显示证据不足，再补 HU-density、HU-sound speed、HU-attenuation 文献。
- 如果 `thermal_safety` brief 显示证据不足，再补 Pennes、CEM43、tFUS heating 文献。
- 如果 `entry_planning` brief 显示证据不足，再补 PlanTUS、neuronavigation、entry planning 相关论文。

目标不是堆论文数量，而是让每个核心模块至少有：

- 2-3 篇论文依据。
- 1-2 个公开工具参考。
- 1 个当前平台差距描述。
- 1 个明确实现决策。

## 7. 成功后的工作方式

新增证据驱动开发层后，后续每个模块都应这样做：

```powershell
python generate_module_evidence_brief.py --module 模块名
```

然后根据生成的 brief 实现模块。

示例：

```powershell
python generate_module_evidence_brief.py --module freefield_calibration
python generate_module_evidence_brief.py --module ct_hu_mapping
python generate_module_evidence_brief.py --module thermal_safety
python generate_module_evidence_brief.py --module entry_planning
```

这样平台后续开发会形成闭环：

```text
论文/代码证据
-> 共识/分歧
-> 当前平台差距
-> 工程决策
-> 实现与验证
-> 新差距反馈
```

这才是真正的“多方面参考论文和源代码，然后对比差距并调整平台”。
