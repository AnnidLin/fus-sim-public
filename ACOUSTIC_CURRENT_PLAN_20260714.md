# 声场当前执行计划（2026-07-14）

## 总目标

优先把现有 D60 声场成果转化为可审阅、可写入论文的证据包，同时停止低效率的小时级仿真。任何新压力计算必须经过单独决策，不从本计划自动触发。

## 当前状态

| 工作项 | 状态 | 证据 |
|---|---|---|
| D60 Gate A 三条 source-safe 轨迹 | 完成 | 三条低/中/高难度轨迹已通过机器安全和委托视觉检查 |
| R74.435 dx0.75/dx0.5 诊断 | 完成 | 场幅值和宽度稳定，但细网格绝对焦点误差 5.472%，波形架构曾请求 110 GiB |
| 低内存记录架构 | 完成 | 单点波形 + 在线全域极值；小型 smoke 和 R78.330 dx0.75 均验证通过 |
| R78.330 dx0.75 源校准 | 完成 | refined focus error 1.364%，target/global 0.9910，1000 点波形完整 |
| R78.330 dx0.5 | 用户中止 | 仅 dry-run 有效；无压力场、无 summary，不支持收敛结论 |
| 声场阶段收口包 | 完成 | `outputs/acoustic_stage_closeout_20260714/` |
| Gate B 网格收敛 | **已完成（通过）** | `outputs/freefield_aperture_calibration/d60_grid_convergence_corrected_20260716/`；dx0.5 refined focus error 0.402%，8/8 acceptance 通过；engineering 级网格收敛观察成立 |
| P1 参考论文差距矩阵 | 完成 | `outputs/reference_paper_gap_matrix_20260715/` |
| P2 论文骨架与结果包 | 完成 | `outputs/paper_skeleton_20260715/` |
| P3 细网格恢复决策门 | 完成（待用户决策） | `outputs/fine_grid_decision_gate_20260715/`；默认 Option C |
| P4 D60 补充图包 | 完成 | `outputs/d60_supplementary_figures_20260715/` |
| P5 单点波形记录设计 | 完成 | `outputs/point_waveform_design_20260715/point_waveform_design.md` |
| P6 Methods/Results/Discussion 完整初稿 | 完成 | `outputs/manuscript_draft_20260715/` |
| P7 基于现有压力场的补充分析 | 完成 | `outputs/d60_supplementary_analysis_20260715/` |
| P8 投稿自包含包 | 完成 | `outputs/acoustic_paper_submission_package_20260715/` |

## 接下来按顺序执行

### P1：参考论文差距矩阵

状态：已完成。交付物见 `outputs/reference_paper_gap_matrix_20260715/`。

### P2：论文骨架与结果包

状态：已完成。交付物见 `outputs/paper_skeleton_20260715/`。

### P3：是否恢复精细网格的决策门

状态：**已完成 — Option A 成功（2026-07-17 06:31 收口）**。用户在 2026-07-16 夜间授权执行 Option A，dx0.5 corrected 单点波形补录成功完成，Gate B 通过。

- 运行结果：`runner_status=kwave_ok`，墙钟 23627.9 s（6.56 h），目标波形 1500 点完整且有限，产物在 `outputs/freefield_aperture_calibration/d60_r78p330_dx0p5_pointwave_20260716/run/`。
- Gate B 结论：`gate_b_dx075_dx05_pass`，8/8 acceptance 通过（`outputs/freefield_aperture_calibration/d60_grid_convergence_corrected_20260716/d60_grid_convergence_report.json`）。
- 关键指标：dx0.5 refined focus error **0.402%**（dx0.75 为 1.364%）；global peak 变化 0.852%；lateral 0.643%；axial 8.889%；focal displacement 0.855 mm；dx0.5 target/global = 1.0。
- 结论级别：engineering 级网格收敛观察。剩余 gaps：dx0.375、PML16、CFL0.1（paper-grade 必需，未授权）。CT pressure 仍未授权。
- 旧 2026-07-13 dx0.5 field-only 结果（refined focus error 5.472%）已由本结果取代为权威；两者 entry plan vintage 不同（20260713 vs 20260714），差异根因标注为开放问题，见 `outputs/evidence_briefs/freefield_d60_dx0p5_pointwave_gateb/gap_feedback.md`。
- 手稿生成器已全部切换为结局条件化措辞，watcher 已自动再生整条论文路线（13 步全部成功）。

### P4：D60 补充图包

状态：已完成。交付物见 `outputs/d60_supplementary_figures_20260715/`。

### P5：单点波形记录设计

目标：为 dx0.5 细网格补录提供低内存方案，使目标波形可在当前硬件上完成。

交付物：

- `outputs/point_waveform_design_20260715/point_waveform_design.md`
- 推荐 Option 1：两场独立运行（场域 + 单点波形），约 3.4 h；备选 Option 2：在线极值 + 单点传感器一次运行。
- 待用户确认后可在数小时内实施并验证。

### P6：Methods/Results/Discussion 完整初稿

状态：已完成。交付物见 `outputs/manuscript_draft_20260715/`。

目标：在现有证据基础上生成可直接进入 LaTeX 的完整初稿，所有数字可追溯到 JSON/NPZ/CSV。

交付物：

- `manuscript_final.md`：带 front matter 和数据可用性声明的最终 Markdown 稿。
- `manuscript_final.tex`：可直接编译的 LaTeX 稿（在 `latex_build_package/` 中）。
- `methods_equations.md`、`figure_captions.md`、`author_checklist.md`。
- `title_and_metadata.md`、`reference_figure_mapping.md`、`response_to_reviewers_template.md`。

### P7：基于现有压力场的补充分析

状态：已完成。交付物见 `outputs/d60_supplementary_analysis_20260715/`。

内容：

- 补充图 4：焦点平面压力等高线（baseline vs corrected dx0.75）。
- 补充图 5：-6 dB 焦点区域边界。
- 补充图 6：dx0.75 vs dx0.5 跨网格轴向轮廓叠图（近似对齐）。
- 补充表 3：三组的 -6 dB 焦点体积估算。

### P8：投稿自包含包

状态：已完成。交付物见 `outputs/acoustic_paper_submission_package_20260715/`。

内容：

- `manuscript/`：最终 Markdown + LaTeX。
- `tables/`：参数表、结果表、source metrics、焦点体积表。
- `figures/`：主图 Figure 1。
- `supplementary_figures/`：补充图 1–6。
- `submission_documents/`：cover letter、highlights、data availability、author contributions、conflicts、checklist、one-page summary 等。
- `point_waveform_design/`：低内存 dx0.5 波形记录设计。

## 夜间自主执行记录

- 8 小时自主工作计划：`ACOUSTIC_AUTONOMOUS_8H_PLAN_20260715.md`
- 最终夜间总结报告：`outputs/overnight_work_summary_20260715/final_8h_report.md`
- 状态快照：`outputs/overnight_work_summary_20260715/STATUS_SNAPSHOT_*.md`

## 当前允许的结论

- 支持：R78.330 在 dx0.75 均匀自由场中显著改善 D60 源焦点校准。
- 支持（2026-07-17 新增）：R78.330 在 dx0.75 与 dx0.5 之间的 **engineering 级网格收敛观察**（Gate B 通过，dx0.5 refined focus error 0.402%，完整目标波形）。
- 不支持：dx0.375/PML16/CFL0.1 级细化、paper-grade 数值收敛、经颅效果、热安全或临床安全。

## 近期成功标准

- 参考论文差距矩阵完成且每项有来源页码/文件路径。
- Methods/Results 初稿中的所有数字可追溯到 JSON/NPZ/CSV。
- 不新增任何未经决策的长时仿真。
