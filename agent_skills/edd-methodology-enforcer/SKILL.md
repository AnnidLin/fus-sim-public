---
name: edd-methodology-enforcer
description: 强制执行证据驱动开发 EDD 机制。要求在修改关键物理参数、材料映射、边界设置、仿真 preset 或数值计算逻辑前生成/更新 evidence_brief，执行后记录 gap_feedback。
---

# EDD 证据驱动开发合规官

当任务涉及以下内容时，启用本技能：

- CT-HU 到声速、密度、衰减映射。
- 换能器几何、source pressure、frequency、duty、PRF 等默认参数。
- k-Wave preset、PPW、PML、CFL 或网格质量。
- Pennes 热模型、热剂量、安全阈值。
- target/entry planning、source safety、avoidance。
- 将文献或公开工具结论转成平台默认配置。

## 执行前：Evidence Brief

任何关键模块实现前，必须先生成或更新：

```text
outputs/evidence_briefs/<module>/evidence_brief.md
outputs/evidence_briefs/<module>/evidence_brief.json
```

Evidence brief 只能记录执行前内容：

- 模块目标
- 相关论文
- 相关公开工具/代码
- 参数共识
- 参数分歧
- 当前平台已有内容
- 当前平台缺口
- 推荐工程决策
- 不应混用的参数或方向
- 验收标准
- 风险、检查点和停止条件

不要把执行后结果写成执行前证据。

## 参数来源

默认参数必须能追溯到至少一个来源：

- `paper_parameter_matrix.csv`
- `tool_code_matrix.csv`
- `parameter_alignment_report.md`
- `reproduction_route_calibration.md`
- 当前平台已有 summary/report

关键边界：

- `500 kHz`：可作为 Gao baseline，但不是唯一频率共识。
- `1 MPa`：必须标记为 source/excitation pressure，不是 free-field 或 in-situ pressure。
- `ap25/r30`：Gao baseline transducer。
- `ap30/r35`：current 079 tuned parameter，不是文献共识。
- `6% duty / 300 Hz / 67 ms / 2.5 s`：Gao protocol，不是通用 tFUS 协议。

## 禁止混用

BBB、微泡、血栓、Histotripsy、热消融等方向的高强度或不同目的参数，不得直接混入低强度神经调控 baseline。

如果未来要支持这些方向，必须单独建立 evidence brief、参数 profile 和风险说明。

## 执行后：Gap Feedback

任务完成、失败或暂停后，必须写入：

```text
outputs/evidence_briefs/<module>/gap_feedback.md
outputs/evidence_briefs/<module>/gap_feedback.json
```

Gap feedback 必须记录：

- 实际执行内容
- 修改文件
- 验证命令和结果
- 与 evidence brief 预期的偏差
- 失败/警告
- 调整策略
- 仍缺的证据
- 下一步建议

## 质量判断

本技能的目标不是让项目“看起来有文献”，而是让每个工程决策都能回答：

1. 参考了哪篇论文？
2. 借鉴了哪个公开工具？
3. 当前平台差距是什么？
4. 本轮实现解决了哪个差距？
5. 哪些结论仍不能写成论文级或医学安全结论？

