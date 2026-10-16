# fus-sim 平台对标与论文产出路线（2026-07-31）

> 结论级别：外部资料核验 + 当前工作区证据审计。  
> 当前结论仅支持研究软件与计算方法路线，不支持临床规划、剂量安全或治疗有效性声明。

## 1. 结论先行

当前技术路径**方向正确，但论文定位需要收窄**。

- 正确之处：平台已经形成了影像衍生介质、冻结物理参数、k-Wave 全波仿真、baseline/TR 配对比较、资源门控、原始场保存、哈希与治理登记的完整链条。
- 已有可写结果：在 Case079、H3-large、250 kHz、完整碗面中间域的匹配比较中，TR 将 target/global 从 `0.477400` 提高到 `0.984864`，将全局峰到目标的距离从 `57.379 mm` 降到 `2.487 mm`。
- 关键限制：绝对压力随计算域变化约 `18–31%`，当前 skull mapping 仍以 `simple_hu300` 为主，只有一个主要 CT 个案，没有水听器/颅骨实验真值，也没有独立平台复核。因此不能把当前结果写成“精确剂量预测”“临床安全”或“普适疗效”。

最适合的首篇论文不是临床应用论文，而是：

> **可复现的经颅超声相位校正计算方法论文：以公开基准、数值敏感性、跨平台核验和单病例 baseline–TR 配对实验为核心。**

这条路线能把本项目真正有差异化的部分——严格匹配比较、运行治理、失败证据保留、完整碗面 TR 和可复现产物——转化为论文贡献，而不依赖当前不存在的医院或专家资源。

## 2. 同类平台与本项目的关系

| 工具 | 定位与主要能力 | 可产出结果 | 对本项目的价值 | 不能替代的部分 |
|---|---|---|---|---|
| k-Wave | 开源 k-space 伪谱声学求解器；支持异质介质、幂律吸收、PML 和 1D/2D/3D | 压力场、时域信号、热模型输入 | 当前求解核心；也是 ITRUSST 基准中的重要参照 | 不提供完整患者影像规划、轨迹管理和论文治理 |
| BabelBrain | 开源研究 GUI；MRI/CT/ZTE 预处理，BabelViscoFDTD 声学、热仿真、多 GPU、3D Slicer/导航集成 | 声压、强度、温升及影像空间结果 | **首选独立求解器对标**；可检验本项目结果是否依赖 k-Wave 后端 | 不能自动证明哪一方更接近真实值，仍需实验真值 |
| PRESTUS | 开源 MATLAB 工作流；T1 分割、CT/pseudo-CT 连续 skull mapping、k-Wave 声学/热、HPC、个体/MNI NIfTI | 个体与组水平声学/热结果 | **首选预处理/材料映射对标**；与本项目同为 k-Wave，便于隔离 workflow 差异 | 不是独立声学求解器复核 |
| TUSX | 开源 MATLAB 经颅超声仿真工具箱 | 影像到声学仿真的研究结果 | 可作为轻量、透明工作流参照 | 官网公开能力描述较少，当前不宜作为唯一主对标 |
| k-Plan | 研究用途的云端规划平台；自动影像转换、相位校正、声学/热计算、设备库、ITRUSST 风格报告 | 压力、强度、温升、CEM43、PDF 计划报告 | **首选产品形态与报告体验对标** | 云端/专有结果格式降低算法透明性，不适合作为唯一可复现基准 |
| fus-sim | Python/k-Wave；CT 衍生模型、baseline/TR、轨迹×换能器析因、资源门控、证据登记和复现清单 | 原始压力场、焦点指标、配对/敏感性报告、治理产物 | 适合做开放、可审计的计算方法研究 | 当前缺少成熟影像分割、连续 skull mapping 验证、多病例、独立求解器和实验真值 |

### 推荐的对标组合

1. **ITRUSST 公共 benchmark**：验证求解器与数值设置，不使用患者数据。
2. **PRESTUS**：比较同一输入下的分割、材料映射、网格和报告差异。
3. **BabelBrain**：在冻结输入后做独立声学后端复核。
4. **k-Plan**：只比较工作流、输出指标和报告规范；若无法稳定访问或导出，不作为论文核心依赖。

不要只做“fus-sim 与另一个平台谁数值更高”。2026 年的 BabelBrain–k-Plan 比较已经表明：相同受试者、轨迹和协议仍可能产生显著不同的强度与温升估计，而没有水听器与温度真值时无法判断哪一个更准确。论文应把**差异来源分解**作为问题：求解器、材料映射、域/网格、换能器定义、轨迹坐标和耦合距离分别占多少。

## 3. 当前路径是否正确：证据化判断

| 维度 | 当前状态 | 判断 |
|---|---|---|
| 科学问题 | 已有 baseline/TR 和轨迹×换能器比较，但问题曾被多次扩展 | 需要冻结为“TR 空间定位改善及其稳健性” |
| 配对设计 | H3-large baseline/TR 参数、网格、源掩膜和哈希可核对 | 正确，是当前最强资产 |
| 主要终点 | target/global、峰到目标距离、绝对压力均已保存 | 前两项适合作为主要终点；绝对 MPa 暂列次要终点 |
| 数值验证 | 自由场 dx 链较完整；250 kHz CT 全碗面尚无专属 dx/PML/CFL/domain 收敛 | 不足以支持 paper-grade 绝对压力 |
| 材料模型 | `simple_hu300` 可复现，但物理真实性有限 | 必须增加连续 HU mapping 或明确的 mapping sensitivity |
| 外部验证 | 有公开 NLM 代理病例，无独立求解器或实验真值 | 只能支持工程复现，不能支持准确性 |
| 样本层级 | 主要结果来自 Case079；多轨迹不是多受试者 | 不能做总体推断 |
| 报告与治理 | ledger、registry、manifest、哈希、失败归档较强 | 可形成方法论文中的可复现贡献 |

综合判断：

- **做平台原型：路径正确。**
- **做计算方法/可复现性论文：可行，但必须先补 benchmark、数值敏感性和外部复核。**
- **做定量剂量或临床安全论文：当前路径和数据均不足。**

## 4. 建议冻结的首篇论文

### 工作题目

**A reproducible full-wave workflow for transcranial ultrasound phase correction: numerical sensitivity, public benchmarking, and cross-platform evaluation**

中文工作题目：

**经颅超声相位校正的可复现全波仿真流程：数值敏感性、公共基准与跨平台评估**

### 核心研究问题

在冻结的换能器几何、轨迹、材料模型、计算域和源幅值下，时间反演是否稳定改善目标区空间定位；该结论对网格、PML、CFL、计算域、材料映射和求解平台有多敏感？

### 预注册主要终点

1. target-window peak / global peak；
2. global peak 到目标的欧氏距离（mm）。

### 次要终点

- 目标窗与全局峰压力；
- 轴向/横向 `-6 dB` 宽度；
- skull/brain 区域峰值和热点位置；
- 运行时间、峰值内存、失败率；
- 跨配置、跨平台的相对差和空间重叠。

绝对压力在通过 CT 专属数值敏感性与外部验证前不得作为首要结论。

## 5. 最低可发表证据包

### Gate P0 — 问题与分析冻结

- 冻结 Case079 H3-large 250 kHz baseline/TR 为主要演示；
- 冻结两个主要终点和允许/禁止声明；
- 写明病例、轨迹和运行失败的纳入排除规则；
- 不在看到结果后更换主要指标。

### Gate P1 — ITRUSST 公共基准

- 至少复现 focused-bowl 的平板、多层骨和 whole-skull 代表性 benchmark；
- 保存输入、网格、介质、源、压力场和差异报告；
- 与公共参考结果比较焦压、焦点位置和焦域尺寸；
- ITRUSST 多模型结果中的“焦压中位差小于 10%、焦点位置中位差小于 1 mm”只能作为公开参照，不应直接冒充本项目预先通过的验收线。

### Gate P2 — 250 kHz CT 数值敏感性

- 网格至少 3 个层级；
- PML、CFL、计算域各至少一个单变量扰动；
- 优先使用分阶段、小域和 field-only 设计估计趋势，再决定是否启动 50–92 小时全域链；
- 若主要终点稳定但绝对压力不稳定，论文只声明“空间定位稳健”，并公开幅值不确定性。

### Gate P3 — 材料映射敏感性

- 保留 `simple_hu300` 作为透明基线；
- 增加一个有文献依据、alpha semantics 完整的连续 HU 映射；
- 比较映射对焦压、峰位置、热点和 transmission 指标的影响；
- 没有实验真值时只报告敏感性，不排名“准确性”。

### Gate P4 — 跨平台复核

- 层 1：相同公共 benchmark，比较 fus-sim/k-Wave 与 BabelViscoFDTD 或公开参考解；
- 层 2：相同 Case079 冻结输入，优先 PRESTUS 做 workflow/mapping 复核；
- 记录坐标约定、换能器参考点、scalp offset、网格和属性映射，避免把输入不一致误判为 solver 差异；
- 使用一致的 NIfTI/NPZ 中间交换格式和哈希。

### Gate P5 — 独立病例

- NLM 72m 只能作为公开尸检工程代理；
- 再引入具有明确许可、影像质量和头颅覆盖的公开 CT/pseudo-CT 个案；
- 第一阶段只验证流水线鲁棒性，不做总体推断；
- 后续根据先导病例的方差做正式样本量/功效设计。病例是统计单位，体素和轨迹不能伪装成独立受试者。

### Gate P6 — 实验验证分叉

- 若目标是“软件/benchmark 方法论文”，可以在无实验真值情况下投稿，但必须限制为数值一致性与可复现性；
- 若目标是“定量压力准确性/安全剂量论文”，必须增加自由场水听器和颅骨/仿体透射实验，必要时增加温度测量；
- 没有这些数据时，不得声称临床准确、安全或可直接驱动硬件。

### Gate P7 — 报告与开放科学

- 按 ITRUSST 清单报告换能器与驱动、自由场参数、脉冲时序、in-situ 暴露和强度；
- 发布版本化代码、环境锁定、输入许可说明、运行清单、配置哈希、失败记录和生成脚本；
- 结果表由机器可读 JSON/CSV 自动生成，图表不得手工抄数；
- 清楚区分 peer-reviewed 文献、预印本、软件说明和本项目推断。

## 6. 建议的论文图表

1. **Figure 1**：可复现工作流与证据链；
2. **Figure 2**：ITRUSST benchmark 与公共参考解比较；
3. **Figure 3**：Case079 baseline–TR 三正交面压力图与焦点位置；
4. **Figure 4**：dx/PML/CFL/domain 敏感性；
5. **Figure 5**：binary vs continuous mapping；
6. **Figure 6**：fus-sim vs BabelBrain/PRESTUS 的空间与幅值差异；
7. **Table 1**：冻结的物理与数值参数；
8. **Table 2**：主要/次要终点与置信区间；
9. **Table 3**：平台能力、输入差异、运行资源与失败模式；
10. **Supplement**：ITRUSST reporting checklist、哈希、失败记录和完整配置。

## 7. 实施优先级

### 立即做，不启动长仿真

1. 冻结论文问题、终点和 claim policy；
2. 建立 ITRUSST benchmark 适配器与结果比较器；
3. 建立平台中间交换规范；
4. 补连续 HU mapping 的证据与测试；
5. 用现有 H3 数据生成论文 Figure 3 草图和结果表。

### 下一批有限计算

1. ITRUSST 小到大三类 benchmark；
2. 250 kHz full-bowl 的单变量 domain/PML/CFL 预实验；
3. PRESTUS 同后端 workflow 对比；
4. 通过资源门后再做 BabelBrain 独立后端比较。

### 需要新资源后再做

- 多病例正式统计；
- 水听器/颅骨/温度实验；
- BBB 微泡、PCD 闭环和患者剂量；
- 临床或治疗效果声明。

## 8. 外部依据

1. Treeby BE, Cox BT. k-Wave: MATLAB toolbox for the simulation and reconstruction of photoacoustic wave fields. *J Biomed Opt.* 2010. DOI: https://doi.org/10.1117/1.3360308
2. Aubry J-F, et al. Benchmark problems for transcranial ultrasound simulation: Intercomparison of compressional wave models. *J Acoust Soc Am.* 2022. DOI: https://doi.org/10.1121/10.0013426
3. Martin E, et al. ITRUSST consensus on standardised reporting for transcranial ultrasound stimulation. *Brain Stimul.* 2024. PubMed: https://pubmed.ncbi.nlm.nih.gov/38670224/
4. Pichardo S. BabelBrain: An Open-Source Application for Prospective Modeling of Transcranial Focused Ultrasound for Neuromodulation Applications. *IEEE TUFFC.* 2023. DOI: https://doi.org/10.1109/TUFFC.2023.3274046
5. BabelBrain repository and current capability notes: https://github.com/ProteusMRIgHIFU/BabelBrain
6. PRESTUS v0.6.0 software record: https://doi.org/10.5281/zenodo.20392907
7. TUSX project page: https://www.tusx.org/
8. k-Plan product and research-use documentation: https://k-plan.io/ and https://dispatch.k-plan.io/static/docs/
9. Brandts SD, et al. Empirical limitations of current low-intensity focused ultrasound simulation platforms. *Brain Stimul.* 2026. DOI: https://doi.org/10.1016/j.brs.2026.103156

## 9. 最终决策

下一阶段不应继续无边界地增加 Case079 长仿真。应把工作拆成：

1. **公共 benchmark 证明 solver 没跑偏；**
2. **数值与 mapping 敏感性说明结论在什么范围内稳定；**
3. **BabelBrain/PRESTUS 说明结果是否依赖单一平台；**
4. **独立公开病例说明流水线不是 Case079 特例；**
5. **有实验资源后再升级到定量准确性与安全论文。**

这样即使短期没有合作医院，也能形成一篇边界清楚、可复现、可审稿的计算方法成果；医院和实验合作将决定后续能否升级为定量验证或临床转化论文，而不是首篇论文能否开始。
