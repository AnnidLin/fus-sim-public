# NLM Additional Head CT/T2 刚体配准记录（2026-07-22）

## 状态

- 已生成 T2→CT 的 6 自由度刚体候选变换。
- 自动定量门通过。
- Codex/专家人工三向视觉质控尚未记为通过。
- `registered_anatomical_roi_ready = false`；不得据此宣称真实病灶或临床靶点。

## 首轮失败与根因

首轮使用 Otsu 阈值生成 T2 掩膜。该阈值为约 330，只保留 T2 内部高信号组织（约 6.2 万个粗网格体素），却与 CT 的整头掩膜（约 16.5 万体素）比较，导致掩膜语义不一致：Dice 约 0.547，自动门失败。

诊断比较表明，T2 正值第 10 百分位阈值约 3.61，可得到与 CT 同语义的外部头部支持掩膜。合成边界回归还发现严格 `>` 会排除恰好位于分位阈值的外层体素，因此最终规则使用 `>=`，而零填充仍被排除。

## 修正后结果

- 初始 NMI：1.100223
- 优化后 NMI：1.150652
- NMI 增量：0.050429
- 初始 Dice：0.859257
- 优化后 Dice：0.855744
- Dice 变化：-0.003513
- 联合分数（NMI + 0.35 × Dice）：1.400963 → 1.450163
- 变换幅度门：通过
- 自动定量门：通过

Dice 的 0.0035 小幅变化处于 0.02 容差内，同时最终 Dice 高于 0.80；互信息和联合目标均改善。因此自动门不要求两个指标逐项严格上升，而要求 NMI 明确改善、Dice 保持高水平、轮廓变化受限且变换合理。

## 产物

- `outputs/nlm_ct_t2_registration_20260722/t2_to_ct_rigid_transform.json`
- `outputs/nlm_ct_t2_registration_20260722/t2_registered_to_ct_coarse.nii.gz`
- `outputs/nlm_ct_t2_registration_20260722/registration_report.json`
- `outputs/nlm_ct_t2_registration_20260722/registration_qc_report.json`
- `outputs/nlm_ct_t2_registration_20260722/registration_orthogonal_qc.png`

## 保留门

1. 当前配准影像是 4 mm 粗网格质控产物，不是最终 CT 原生网格 T2。
2. 专家人工视觉 QC 未完成，因此不生成 `registered_anatomical` ROI。
3. 公开尸体数据不构成临床验证。
4. 本阶段没有启动压力仿真或 k-Wave。
