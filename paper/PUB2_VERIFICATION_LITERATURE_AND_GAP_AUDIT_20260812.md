# PUB.2 仿真验证：文献框架、现状审计与补证路线

## 先用最简单的话说明

仿真论文里的“验证”至少包含四件不同的事：

1. **代码验证（code verification）**：程序有没有正确实现方程和算法，也就是“方程有没有算对”。
2. **计算验证（calculation/solution verification）**：这一次计算受到网格、时间步长和边界多大影响，也就是“这组离散参数够不够精确”。
3. **现实验证（validation）**：模型结果与水听器、体模或离体颅骨测量有多接近，也就是“模型像不像真实世界”。
4. **不确定性量化（UQ）**：CT、声速、衰减、颅骨厚度和定位误差变化后，结论是否仍成立。

可复现性则回答第五个问题：别人能否用相同输入重新得到相同结果。它很重要，但**可复现不等于真实准确**。

## 本项目应采用的模型用途

### 问题（Question of Interest）

在一个冻结的 Case079 CT 声学模型中，相比完全匹配的 baseline，full-wave time reversal 是否提高模拟焦点的空间定位？

### 适用范围（Context of Use, COU）

模型仅用于比较同一计算介质、同一换能器和同一目标下 baseline 与 TR 的**相对定位差异**，主要指标为目标/全局峰值比和全局峰至目标距离。

### 明确排除

- 不用当前模型预测真实人体绝对颅内压力；
- 不据此判断疗效或安全；
- 不外推到其他个体；
- 不声称已完成正式数值收敛。

这是根据 FDA 2023 风险知情框架做出的关键收窄。若论文坚持这个 COU，所需验证强度显著低于临床规划或安全决策模型；如果扩大到绝对压力、跨人群或安全结论，验证要求必须同步升级。

## 权威框架如何要求

FDA 将模型可信度定义为：针对特定 COU，通过证据建立对模型预测能力的信任。其建议流程是先定义问题、COU 和模型风险，再预先设定可信度目标，生成证据，最后进行充分性判断。FDA 明确区分代码验证、计算验证、实验/体内/群体验证及 COU 计算中的 UQ [1]。ASME V&V 40 同样强调，验证强度应与模型在决策中的影响和错误决策后果相称 [2]。

对经颅超声，ITRUSST 报告共识要求透明报告换能器、驱动条件、自由场、脉冲时序、估计的脑内暴露量及其假设 [3]。国际跨求解器基准提供了从水、平板骨到全颅骨的冻结测试问题；其跨模型比较中，焦点压力和位置差异的中位数通常小于 10% 和 1 mm，但这些数值是文献背景分布，不应事后直接当作本项目的自动合格线 [4]。

## 当前 PUB.2 证据审计

| 证据层 | 当前证据 | 判断 | 含义 |
|---|---|---|---|
| 问题与 COU | 已冻结为单病例、模型内 baseline–TR 相对定位比较 | 通过 | 足以开始保守论文 |
| 软件单元与流程测试 | 328 项完整回归通过，含4项新误差分解/合同护栏测试 | 通过 | 支持实现与治理可靠性 |
| 外部代码基准 | ITRUSST Phase A BM1/BM3/BM4 已运行 | 部分通过 | BM1接近跨模型背景；BM3/BM4仍有较大场差异或位置差异 |
| BM1 | 峰值差 0.47%，焦点位置差 0.5 mm，rel. L2 3.26% | 良好 | 支持自由场/简单问题实现 |
| BM3 | 正式指标：峰值差 0.23%，位置差 2.0 mm，rel. L2 15.77%；后验分解：主瓣 L2 4.33%，低于−12 dB区域29.51% | 已诊断、仍不通过位置目标 | 差异主要不是整体增益或小位移，而在旁瓣/背景场形 |
| BM4 | 正式指标：峰值差 13.53%，位置差 1.5 mm，rel. L2 27.10%；后验最优增益0.833，缩放后 L2 18.43% | 已诊断、未通过项目目标 | 整体幅值/衰减是主要分量之一，但仍有旁瓣和场形残差 |
| PML 计算验证 | baseline/TR 的 PML12–16 均完成，定位距离不变，rel. L2 ≤ 5.1×10−5 | 通过（限定） | 排除了所测试 PML 厚度导致主结论的可能性 |
| 当前 250-kHz CFL | fresh recovery 完成；baseline L2/L∞ 0.654%/1.375%，目标压力−0.770%，定位不变 | baseline通过 | 尚未覆盖 TR 时间步敏感性 |
| 当前 250-kHz 网格 | 只有 dx=0.75 mm 的正式 baseline/TR | 缺失 | 旧 500-kHz、旧裁剪域的 dx0.75/0.5 不能迁移为当前收敛证据 |
| 域尺寸 | PML 厚度变化已测；物理裁剪域扩大未测 | 缺失 | PML 灵敏度不等于域尺寸独立性 |
| 模型输入 UQ | `simple_hu300` 单一映射；未传播声速、衰减、CT和厚度不确定性 | 缺失 | 当前绝对压力不能作为预测值 |
| 求解器一般实验验证 | k-Wave 已在水和分层吸收介质中被定量验证 | 间接支持 | 支持求解器物理基础，但不是 Case079 验证 |
| 经颅实验对照 | 项目没有与同一换能器/颅骨/CT配准的水听器数据 | 缺失 | 不能声称真实世界准确度 |
| 独立病例 | Case079 一例 | 缺失 | 不能声称普适性 |
| 可复现性 | ledger、registry、manifest、最终包和图表哈希均通过 | 强 | 是当前最成熟的证据层 |

## 为什么现有结果仍然有论文价值

当前结果支持的是一个**计算系统内部的相对比较**：在完全匹配的模型里，TR 把全局峰从距目标 57.38 mm 移到 2.49 mm，并将目标/全局峰比从 0.4774 提升到 0.9849。PML 单变量扰动没有改变这个结论。

这足以支持“在 Case079 冻结模型中，TR 改善了模拟定位”的技术结论。它不能支持“真实人体焦点误差为 2.49 mm”，因为输入声学属性、真实换能器输出和颅骨实验对照尚未验证。

## 需要预注册的验证目标

以下是本项目建议采用的**前瞻性项目门槛**，不是从文献中冒充出来的统一行业标准：

### 主结论保持条件

- 每个敏感性单元中，TR 后全局峰仍落在预定义的 5-mm 目标窗内；
- TR 的目标/全局峰比仍高于 baseline；
- 不允许通过改变目标、裁剪规则或近场排除规则来“修复”失败结果。

### 计算验证目标

- CFL0.2 与 CFL0.1：峰至目标距离差不超过一个当前网格单元（0.75 mm），目标/全局峰比相对差不超过 5%；
- PML12 与 PML16：已满足上述定位保持条件；继续保留完整场差异而不只看标量；
- 网格：至少完成匹配的 dx0.75 与 dx0.5 baseline/TR；如指标变化超过 5% 或峰位置变化超过一个粗网格单元，则增加第三层网格并报告非单调性，而不是挑选更好看的结果；
- 物理域：扩大裁剪域后，主结论仍满足相同定位条件。

### 外部基准目标

- 重新分析 BM1/BM3/BM4，并在看结果前冻结判据；
- BM3/BM4 若不能达到预定的焦点位置和压力误差目标，应保留为已知局限并查明来源，而不能将 Phase A 整体写成“全部通过”；
- 优先增加一个公开、带水听器测量的经颅验证单元，而不是先增加大量只在同一模型中循环的病例。

## 最小成本、最高信息增益路线

### 第 1 层：不启动求解器

1. 冻结本报告中的 COU、指标和门槛。
2. 用现有 BM1/BM3/BM4 场重新做误差空间图和差异归因，重点检查源定义、坐标、比较窗和材料参数。
3. 将 FDA/ASME 风格的可信度矩阵加入论文补充材料。
4. 把绝对压力相关语句统一改为“simulated temporal peak magnitude”。

本层已在 2026-08-12 完成：误差分解见 `outputs/itrusst_phase_a_diagnostic_20260812/`；冻结门槛见 `paper/PUB2_VERIFICATION_CONTRACT_20260812.md/json`。后验拟合只用于归因，不替换正式 benchmark 指标。

### 第 2 层：完成当前配置的数值验证

1. Windows 重启状态干净后，执行一个 matched CFL0.1 baseline/TR 链。
2. 完成一个扩大物理域的 matched baseline/TR 单变量链。
3. 完成 dx0.5 matched baseline/TR；只有结果显示不稳定时才追加第三网格层。

所有长任务必须继续遵守 CPU、内存、空闲内存和单求解器门限。

### 第 3 层：现实验证

优先考虑 Krokhmal 等 2025 公开的离体人颅骨水听器数据集。该数据覆盖 270 kHz、500 kHz、750 kHz 和 1 MHz，并提供自由场源表征与四个人颅骨后的测量；270 kHz 与本项目 250 kHz 最接近 [7,8]。公开 API 核验显示 v2 为 CC BY 4.0、22 文件、约8.14 GB；只取270 kHz自由场、四颅骨测量及四份CT约2.31 GB。详细选择和风险控制见 `paper/PUB2_PUBLIC_HYDROPHONE_VALIDATION_FEASIBILITY_20260812.md`。这不能直接验证 Case079，但可以验证本项目从 CT/源定义到经颅场预测的完整方法链。

如果无法执行公开数据复现，则必须把论文定位保持为计算方法案例，并明确“没有 model-specific experimental validation”。

### 第 4 层：跨病例与UQ

1. 在不调参条件下增加至少 3–5 个独立头模，报告全部成功与失败。
2. 对声速、密度、衰减、CT平滑/颅骨厚度和定位误差做敏感性或概率传播。
3. 特别优先声速和颅骨几何；既有研究显示这些因素可显著改变焦点压力与位置 [9,10]。

## 投稿充分性结论

| 论文主张 | 当前是否足够 | 结论 |
|---|---|---|
| Case079 中 TR 改善模拟定位 | 条件性足够 | 可写、可作为技术案例投稿；必须披露验证缺口 |
| 结果已数值收敛 | 不足 | CFL、网格和域尺寸未闭环 |
| k-Wave/PUB.2 对真实颅内压力预测准确 | 不足 | 无匹配实验验证和输入UQ |
| 方法适用于一般人群 | 不足 | 单病例 |
| 临床有效或安全 | 严禁 | 当前 COU 完全不覆盖 |

当前最准确的表述不是“仿真已经验证”，而是：

> 软件与复现链验证较强；PML 单变量计算验证已通过；外部代码基准部分完成；当前配置的 CFL、网格、域尺寸、输入不确定性和现实实验验证仍不完整。因此，证据足以支持一个单病例模型内定位改善结论，但不足以支持收敛、绝对压力、普适性或临床主张。

## 核心参考资料

1. U.S. FDA. *Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions* (2023). https://www.fda.gov/media/154985/download
2. ASME. *V&V 40-2018: Assessing Credibility of Computational Modeling through Verification and Validation: Application to Medical Devices*. https://webstore.ansi.org/standards/asme/asme402018
3. Martin, E. *et al.* ITRUSST consensus on standardised reporting for transcranial ultrasound stimulation. *Brain Stimulation* **17**, 607–615 (2024). https://doi.org/10.1016/j.brs.2024.04.013
4. Aubry, J.-F. *et al.* Benchmark problems for transcranial ultrasound simulation: Intercomparison of compressional wave models. *J. Acoust. Soc. Am.* **152**, 1003–1019 (2022). https://doi.org/10.1121/10.0013426
5. Aubry, J.-F. *et al.* Benchmark dataset, version 1.0. Zenodo (2022). https://doi.org/10.5281/zenodo.6020543
6. Martin, E., Jaros, J. & Treeby, B. Experimental validation of k-Wave: nonlinear wave propagation in layered, absorbing fluid media. *IEEE TUFFC* **67**, 81–91 (2020). https://doi.org/10.1109/TUFFC.2019.2941795
7. Krokhmal, A., Simcock, I. C., Treeby, B. E. & Martin, E. A comparative study of experimental and simulated ultrasound beam propagation through cranial bones. *Phys. Med. Biol.* **70**, 025007 (2025). https://doi.org/10.1088/1361-6560/ada19d
8. Krokhmal *et al.* Open hydrophone/skull validation dataset. UCL Research Data Repository (2024). https://doi.org/10.5522/04/28025240
9. Robertson, J. L., Martin, E., Cox, B. & Treeby, B. Sensitivity of simulated transcranial ultrasound fields to acoustic medium property maps. *Phys. Med. Biol.* **62**, 2559–2580 (2017). https://doi.org/10.1088/1361-6560/aa5e98
10. Stanziola, A., Pineda-Pardo, J. A. & Treeby, B. Transcranial ultrasound simulation with uncertainty estimation. *JASA Express Lett.* **3**, 052001 (2023). https://doi.org/10.1121/10.0019380
11. Chen, M. *et al.* Numerical and experimental evaluation of low-intensity transcranial focused ultrasound wave propagation using human skulls for brain neuromodulation. *Medical Physics* **50**, 38–49 (2023). https://doi.org/10.1002/mp.16090
12. Li, Z., Yu, K., Kosnoff, J. & He, B. Improving targeting specificity of transcranial focused ultrasound in subject-specific head models using a random array transducer: a k-Wave simulation study. *IEEE Access* **13**, 113179–113193 (2025). https://doi.org/10.1109/ACCESS.2025.3584245
