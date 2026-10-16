> **2026-10-16：项目已暂停。下文为历史论文计划，不代表继续执行授权。当前状态见 PROJECT_STATUS.md。**

# fus-sim 论文执行主计划

> 版本：1.0  
> 冻结日期：2026-07-31  
> 状态：**当前唯一主动执行计划**  
> 适用对象：所有后续人工、Codex 与 DS（DeepSeek）任务；协作规则见 `AGENT_OPERATING_MODEL.md`

## 1. 项目主目标

从现在起，`fus-sim` 的主要目标是产出一篇边界清楚、证据可追溯、结果可复现的经颅超声计算方法论文。

首篇论文定位：

> **可复现的经颅超声相位校正全波仿真方法：数值敏感性、公共基准、跨平台复核与单病例 baseline–TR 配对证据。**

平台建设只服务于以下至少一项：

1. 回答论文研究问题；
2. 生成预定图表或数据表；
3. 通过论文证据门；
4. 提高复现性、审计性或投稿完整性。

不能映射到上述目标的功能、批量仿真、界面开发、热/BBB 扩展或临床功能暂停。

## 2. 冻结的研究问题与声明

### 主要研究问题

在冻结换能器几何、轨迹、材料模型、计算域、源幅值和数值协议后，时间反演（TR）是否改善目标区空间定位；这种改善对网格、PML、CFL、计算域、材料映射和求解平台有多敏感？

### 主要终点

1. `target_window_peak / global_peak`；
2. global peak 到预定目标的欧氏距离（mm）。

### 次要终点

- 目标窗峰值和全局峰值压力；
- 轴向、横向 `-6 dB` 宽度；
- brain/skull 分区峰值及热点位置；
- 归一化场空间重叠；
- 运行时间、峰值内存和失败率。

### 当前允许的核心声明

- 在 Case079、H3-large、250 kHz、匹配完整碗面中间域条件下，TR 改善了空间定位指标；
- 平台可以生成参数、输入、原始场、指标、哈希和失败记录均可追溯的计算证据；
- 后续 benchmark 与敏感性结果可以说明结论在何种数值和材料假设下稳定。

### 当前禁止的声明

- 绝对压力已经数值收敛；
- 预测压力或温升具有实验准确性；
- 临床安全、治疗有效或可用于患者剂量；
- 单病例结果可推广到人群；
- `simple_hu300` 或其他 mapping 已被证明最准确；
- 平台已达到临床规划软件成熟度。

详细冻结见 `paper/PAPER_ANALYSIS_FREEZE_20260731.md`。

## 3. 当前论文主结果

主要演示单元为 Case079、H3 trajectory、aperture 60 mm、radius 74.435 mm、250 kHz、1 MPa source、2 cycles、PML12、CFL0.2、standard preset、lat30/post16 完整碗面中间域：

| 指标 | Baseline | TR | 解释 |
|---|---:|---:|---|
| target/global | 0.477400 | 0.984864 | TR 改善目标相对占优程度 |
| global peak 到目标距离 | 57.379 mm | 2.487 mm | TR 将主峰移入目标邻域 |
| global peak | 3.961692 MPa | 2.593355 MPa | 绝对幅值下降；不是当前主要终点 |

该结果是**单病例、中间域、工程级空间定位证据**。绝对压力在不同域之间变化约 `18–31%`，因此幅值不作为当前核心结论。

权威产物：

- `outputs/h3_large_full_bowl_matched_standard_20260730/comparison/matched_comparison.json`
- `outputs/evidence_briefs/freq250_h3_large_full_bowl_intermediate_domain_20260730/gap_feedback.json`

## 4. 论文证据门与执行顺序

后续任务必须按依赖顺序推进。除非主计划正式变更，不得跳过前置门启动长仿真。

### PUB.0 — 分析冻结：已完成

交付物：

- 本主计划；
- `paper/PAPER_ANALYSIS_FREEZE_20260731.md`；
- `paper/MANUSCRIPT_EVIDENCE_MAP.md`；
- 两个主要终点、统计单位、声明边界与变更流程。

退出条件：上述文件进入版本控制，项目入口文档全部指向本计划。

### PUB.1 — ITRUSST 公共 benchmark：已完成（公共工程证据级）

目标：先证明求解器、坐标、源定义和指标实现没有系统性偏差。

范围：

1. 读取并锁定 ITRUSST benchmark 数据版本与许可；
2. 建立 benchmark 输入适配器；
3. 优先覆盖 focused-bowl 的 planar、multilayer 和 whole-skull 代表单元；
4. 建立机器可读比较器；
5. 输出焦压、焦点位置、焦域尺寸、场差异和资源消耗；
6. 保存配置、原始输出、哈希和失败记录。

2026-08-03 检查点：官方数据/代码来源、许可、物理参数、网格、掩膜和
指标契约已冻结，focused-bowl source 1 的适配器、比较器和 harmonic
pressure-amplitude 导出已实现。通过 HTTP Range 仅提取并校验了
BM1/BM3/BM4 三份官方 k-Wave 参考场（约 0.6 MB），没有下载 25.3 GB
整包。BM1 轴对称 PPW12 复现已与官方 PPW60 场完成比较：相对 L2
误差 3.2626%、L∞ 误差 4.6716%、峰值差 0.4739%、焦点位置差 0.5 mm。
Cartesian 2-D 诊断的 L2 误差为 62.13%，证明轴对称坐标一致性是关键，
不得用后处理标量归一化掩盖坐标错误。2026-08-04 BM3 轴对称
PPW12/PPP96 已完成：相对 L2 15.7682%、L∞ 12.2911%、峰值差 0.2293%、
焦点位置差 2.0 mm；幅值接近但场差异与焦点偏差仍需在手稿中透明解释。
2026-08-07 BM4 多层轴对称 PPW12/PPP144 在六线程、BelowNormal 设备门下
完成，监控墙钟 1280.22 s、返回码 0。严格位于 36.5 mm 内界面之后的
23,547 个体素全部有限且为正。与官方 PPW60 比较：相对 L2 27.1000%、
L∞ 19.7000%、峰值差 13.5335%、焦点位置差 1.5 mm。BM1/BM3/BM4
三案例汇总及官方/候选/差值图已生成于
`outputs/itrusst_phase_a_summary_20260807/`。PUB.1 的三单元退出门已满足，
但 BM3/BM4 的场差异必须透明报告，不能解释为论文级数值收敛。BM7
只是三维颅骨子集；whole-skull 代表仍须使用另行资源门控的 BM8 或 BM9。详见
`outputs/evidence_briefs/pub1_itrusst_benchmark_20260803/`。

退出条件：

- 至少三个预定 benchmark 单元完整；
- 结果可由一条受控命令重建；
- 与公共参考结果的差异得到解释；
- 不把 ITRUSST 跨模型中位差直接冒充本项目预注册验收线。

### PUB.2 — 250 kHz CT 数值敏感性

前置：PUB.0、PUB.1 完成；新 EDD 与资源门通过。

范围：

- dx 至少三个层级；
- PML、CFL、计算域各至少一个单变量扰动；
- baseline 与 TR 保持匹配；
- 优先小域/field-only 预实验，满足升级门后才运行长链。

退出条件：

- 两个主要终点的变化范围明确；
- 绝对压力若不稳定，明确报告不确定性且不使用收敛措辞；
- 所有长任务具备 dry-run、后台监控、停滞诊断和完成验证。

### PUB.3 — 材料映射敏感性

前置：材料证据 brief、alpha semantics 和测试完成。

范围：

- `simple_hu300` 作为透明基线；
- 至少一个文献支持的连续 HU mapping；
- 比较焦压、焦点、热点和主要终点；
- 无实验真值时只报告敏感性，不给出准确性排名。

退出条件：mapping 差异可复现，输入与参数语义完整，结论边界进入手稿。

### PUB.4 — 跨平台交换规范

范围：

- 统一坐标系、单位、仿射、目标、轨迹和换能器参考点；
- 统一 source/free-field/in-situ 压力定义；
- 定义介质场、源掩膜、场输出和哈希格式；
- 明确 scalp/transducer offset、耦合介质和裁剪域；
- 建立导入后的完整性验证。

退出条件：相同输入能够被本平台与外部工具无歧义解释。

### PUB.5 — PRESTUS/BabelBrain 复核

前置：PUB.3、PUB.4 完成；软件、输入与许可兼容。

两层设计：

1. PRESTUS：比较预处理、材料映射和同一 k-Wave 后端 workflow；
2. BabelBrain：使用 BabelViscoFDTD 做独立求解器复核。

退出条件：

- 区分 solver 差异和 input/mapping 差异；
- 报告归一化空间一致性和绝对幅值差；
- 没有实验真值时不声称某平台更准确。

### PUB.6 — 独立公开病例

范围：

- 保留 NLM 72m 为尸检工程代理；
- 增加至少一个许可明确、质量合格的公开头颅影像；
- 使用冻结流程验证失败率、坐标正确性和主要终点方向。

退出条件：证明流水线不是只对 Case079 可运行。总体推断仍需后续根据先导方差设计样本量。

### PUB.7 — 手稿与投稿包

前置：PUB.0–PUB.6 的核心门完成，或对未完成门给出透明限制。

交付物：

- 主文、摘要和结构化方法；
- 主图、补充图和机器可读表；
- ITRUSST reporting checklist；
- 环境、配置、哈希、ledger、registry 和复现清单；
- 数据许可、代码版本和失败记录；
- 目标期刊适配后的投稿包。

### PUB.8 — 定量准确性/安全扩展：外部资源分支

仅在获得实验资源后启动：

- 自由场水听器；
- 颅骨或等效仿体透射测量；
- 若声明热效应，增加温度测量；
- 若进入 BBB/临床剂量，增加微泡、PCD、硬件校准和伦理/临床输入。

PUB.8 不是首篇计算方法论文的启动前提。

## 5. 图表与结果映射

| 论文产物 | 内容 | 当前状态 | 解锁门 |
|---|---|---|---|
| Figure 1 | 工作流、治理与数据流 | 可制作 | PUB.0 |
| Figure 2 | ITRUSST benchmark | BM1/BM3/BM4 数据、汇总及字段图已生成 | PUB.1 完成 |
| Figure 3 | Case079 baseline–TR 压力场与焦点 | 数据已有 | PUB.0 |
| Figure 4 | dx/PML/CFL/domain 敏感性 | 缺失 | PUB.2 |
| Figure 5 | binary vs continuous HU mapping | 缺失 | PUB.3 |
| Figure 6 | PRESTUS/BabelBrain 跨平台比较 | 缺失 | PUB.5 |
| Table 1 | 冻结参数与定义 | 部分已有 | PUB.0/PUB.4 |
| Table 2 | 主要和次要终点 | 主病例已有 | PUB.2/PUB.6 |
| Table 3 | 平台、资源与失败模式 | 对标矩阵已有 | PUB.5 |
| Supplement | ITRUSST checklist、配置、哈希、失败记录 | 部分已有 | PUB.7 |

逐项证据位置见 `paper/MANUSCRIPT_EVIDENCE_MAP.md`。

## 6. 后续代理强制执行流程

每个新任务必须执行：

1. 读取 `AI_PROJECT_SNAPSHOT.md` 和本主计划；
2. 把任务映射到一个 `PUB.x` 编号；
3. 在 `AI_TODO.md` 标明状态、负责人和退出条件；
4. 检查是否改变物理、材料、边界、preset 或数值逻辑；若是，先写 Evidence Brief；
5. 仿真前执行 dry-run 资源门，长任务后台运行并监控；
6. 结果必须生成机器可读 JSON/CSV，不从日志手工抄数；
7. 用原始 NPZ/JSON 交叉核验图表与文字；
8. 更新 gap feedback、`paper/MANUSCRIPT_EVIDENCE_MAP.md`、快照和任务板；
9. 运行相关测试、治理验证和工作树检查后再声明完成；
10. 创建边界清楚的本地提交。

若任务不能映射到 `PUB.0–PUB.8`，必须先停止并修改本主计划，不能绕过计划直接执行。

## 7. 计划变更规则

以下变化需要新版本计划和明确理由：

- 修改主要研究问题或主要终点；
- 更换主要病例、频率、换能器或 TR 定义；
- 将热、BBB、临床或硬件结果纳入首篇论文核心；
- 把单病例观察升级为总体结论；
- 新增长时间、高资源但不对应既定图表或证据门的仿真。

变更记录必须说明原计划、新证据或阻塞、修改内容、对已完成分析的影响，以及是否构成结果后改终点。

## 8. 完成定义

“论文阶段完成”必须同时满足：

- 核心研究问题得到回答；
- benchmark、敏感性和外部复核边界清楚；
- 图表全部由可追溯数据自动生成；
- 主要结果可由独立命令复现；
- 统计单位、病例限制和失败记录透明；
- ITRUSST 报告项完成或解释缺失；
- 所有引用经过核验；
- 不包含超出证据的临床或安全声明；
- 测试、治理验证和最终复现包通过。

## 9. 支撑文件

- 平台对标：`literature_tFUS_review/06_报告与数据/reports/PLATFORM_BENCHMARK_AND_PUBLICATION_ROUTE_20260731.md`
- 平台矩阵：`literature_tFUS_review/06_报告与数据/platform_comparison_20260731.csv`
- 分析冻结：`paper/PAPER_ANALYSIS_FREEZE_20260731.md`
- 手稿证据图：`paper/MANUSCRIPT_EVIDENCE_MAP.md`
- 当前状态：`AI_PROJECT_SNAPSHOT.md`
- 任务板：`AI_TODO.md`

旧的 BBB、热仿真和历史 acoustic plans 仅保留为证据与背景，不再作为主动执行入口。
