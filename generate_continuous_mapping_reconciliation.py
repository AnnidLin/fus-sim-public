from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


DEFAULT_PATHS = {
    "continuous_profile": Path("acoustic_mapping_profiles/continuous_skull.json"),
    "builder_code": Path("build_ct_acoustic_model.py"),
    "continuous_model_summary": Path("outputs/ct_acoustic_model_3d_profile_continuous/summary.json"),
    "continuous_model_npz": Path("outputs/ct_acoustic_model_3d_profile_continuous/acoustic_model_3d.npz"),
    "binary_run_summary": Path("outputs/ct_comparison_runs/079_binary_standard/summary.json"),
    "binary_runner_status": Path("outputs/ct_comparison_runs/079_binary_standard/runner_status.json"),
    "binary_pressure_npz": Path("outputs/ct_comparison_runs/079_binary_standard/pressure_max_mpa.npz"),
    "continuous_run_summary": Path("outputs/ct_comparison_runs/079_continuous_standard/summary.json"),
    "continuous_runner_status": Path("outputs/ct_comparison_runs/079_continuous_standard/runner_status.json"),
    "continuous_pressure_npz": Path("outputs/ct_comparison_runs/079_continuous_standard/pressure_max_mpa.npz"),
    "comparison_report": Path("outputs/continuous_vs_binary_comparison/comparison_report.md"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("/", "\\")
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8-sig")


def file_info(path: Path, artifact_type: str, classification: str, notes: str) -> dict[str, Any]:
    exists = path.exists()
    stat = path.stat() if exists else None
    return {
        "artifact_id": path.stem,
        "path": rel(path),
        "exists": exists,
        "artifact_type": artifact_type,
        "classification": classification,
        "size_bytes": stat.st_size if stat else None,
        "modified_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).replace(microsecond=0).isoformat()
        if stat
        else None,
        "notes": notes,
    }


def extract_continuous_formula_audit(builder_path: Path, profile: dict[str, Any] | None) -> dict[str, Any]:
    code = read_text(builder_path)
    function_match = re.search(
        r"def continuous_property_volume\([\s\S]*?\n\n\ndef ",
        code,
    )
    function_text = ""
    if function_match:
        function_text = function_match.group(0).rsplit("\n\n\ndef ", 1)[0]

    cont = {}
    if profile:
        cont = profile.get("continuous_mapping", {}) or {}

    return {
        "builder_path": rel(builder_path),
        "function_present": "def continuous_property_volume" in code,
        "save_model_uses_continuous_profile": "continuous_property_volume(hu, labels" in code,
        "profile_mapping_type": profile.get("mapping_type") if profile else None,
        "profile_review_status": profile.get("review_status") if profile else None,
        "continuous_mapping_config": cont,
        "implemented_formula_summary": {
            "base_values": "Start from binary material_property_volume(labels, attribute, materials).",
            "active_only_for": "profile.mapping_type == 'continuous_skull'.",
            "skull_mask": "Only voxels with skull label receive continuous interpolation.",
            "hu_clamp": "HU is clipped to hu_min..hu_max before interpolation.",
            "interpolation": "t=(clipped_hu-hu_min)/(hu_max-hu_min); property=p_min+t*(p_max-p_min).",
            "attributes": [
                "sound_speed_m_s from sound_speed_range_m_s",
                "density_kg_m3 from density_range_kg_m3",
                "alpha_db_mhz_cm from alpha_range_db_mhz_cm",
            ],
        },
        "implementation_risks": [
            "The interpolation formula is implemented, but the exact paper/code formula has not been traced.",
            "Alpha is interpolated linearly in dB/MHz/cm; frequency exponent and unit conventions remain unaudited.",
            "The profile notes are stale because they still claim the builder does not apply continuous_mapping.",
            "A focal waveform near-identical to binary does not validate skull-path mapping physics.",
        ],
        "source_excerpt_for_audit": function_text[:4000],
        "status": "implementation_exists_but_validation_blocked",
    }


def summarize_run_status(status: dict[str, Any] | None) -> dict[str, Any]:
    if not status:
        return {"exists": False, "status": "missing"}
    execution = status.get("execution", {}) if isinstance(status.get("execution"), dict) else {}
    return {
        "exists": True,
        "status": status.get("status"),
        "preset": status.get("preset"),
        "execute": status.get("execute"),
        "uses_start_process": status.get("uses_start_process"),
        "uses_powershell_job": status.get("uses_powershell_job"),
        "runtime_s": execution.get("runtime_s"),
        "core_output_exists": execution.get("core_output_exists"),
    }


def summary_slice(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {"exists": False}
    return {
        "exists": True,
        "description": summary.get("description"),
        "grid_shape": summary.get("grid_shape"),
        "dx_m": summary.get("dx_m"),
        "target_index_ijk": summary.get("target_index_ijk"),
        "mapping_profile": summary.get("mapping_profile"),
        "voxel_counts": summary.get("voxel_counts"),
        "hu_range": summary.get("hu_range"),
        "sound_speed_range_m_s": summary.get("sound_speed_range_m_s"),
        "density_range_kg_m3": summary.get("density_range_kg_m3"),
        "alpha_range_db_mhz_cm": summary.get("alpha_range_db_mhz_cm"),
        "simulation_quality": summary.get("simulation_quality"),
    }


def build_inventory(paths: dict[str, Path]) -> list[dict[str, Any]]:
    rows = [
        file_info(paths["continuous_profile"], "profile", "review_pending_config", "Continuous profile remains not default."),
        file_info(paths["builder_code"], "source_code", "implementation_evidence", "Contains current CT model builder implementation."),
        file_info(paths["continuous_model_summary"], "model_summary", "exploratory_evidence", "Continuous model summary exists; not a validated baseline."),
        file_info(paths["continuous_model_npz"], "model_npz", "exploratory_output", "Existing model artifact; do not delete or promote."),
        file_info(paths["binary_run_summary"], "simulation_summary", "baseline_comparison_run", "Binary standard run summary for comparison context."),
        file_info(paths["binary_runner_status"], "runner_status", "execution_evidence", "Runner status for binary comparison run."),
        file_info(paths["binary_pressure_npz"], "pressure_npz", "existing_output", "Existing pressure field; not generated by this task."),
        file_info(paths["continuous_run_summary"], "simulation_summary", "exploratory_comparison_run", "Continuous standard run summary; exploratory only."),
        file_info(paths["continuous_runner_status"], "runner_status", "execution_evidence", "Runner status for continuous comparison run."),
        file_info(paths["continuous_pressure_npz"], "pressure_npz", "existing_output", "Existing pressure field; not generated by this task."),
        file_info(paths["comparison_report"], "comparison_report", "superseded_exploratory_report", "Must be read with superseding_notice.md."),
    ]
    return rows


def write_inventory(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_state_report(data: dict[str, Any]) -> str:
    return f"""# Continuous CT-HU Mapping 状态纠偏报告

## 结论

当前 `continuous_skull` 路线的正确状态是：**已有 exploratory model 和 exploratory standard comparison run，但尚未成为 validated baseline**。

因此，`outputs/continuous_vs_binary_comparison/comparison_report.md` 中的数值只能作为探索性现场记录，不能作为 paper-grade、最终物理结论或默认模型依据。

## 状态冲突

- Profile 状态：`{data['profile_review_status']}`
- Continuous model 是否存在：`{data['continuous_model']['exists']}`
- Binary runner 状态：`{data['binary_run_status']['status']}`
- Continuous runner 状态：`{data['continuous_run_status']['status']}`
- 既有 comparison report：`{data['comparison_report_exists']}`

冲突点在于：profile 仍是 review pending，但模型和 pressure run 已经存在。runner 的 `kwave_ok` 只能说明该 exploratory run 执行完成，不能反推 continuous mapping 公式已经验证。

## 已有输出归类

- `outputs/ct_acoustic_model_3d_profile_continuous/`：exploratory continuous model。
- `outputs/ct_comparison_runs/079_continuous_standard/`：exploratory standard run。
- `outputs/continuous_vs_binary_comparison/comparison_report.md`：superseded exploratory comparison，需要同时阅读 `superseding_notice.md`。

## Continuous 模型概要

- grid shape：`{data['continuous_model'].get('grid_shape')}`
- dx：`{data['continuous_model'].get('dx_m')}` m
- target：`{data['continuous_model'].get('target_index_ijk')}`
- HU range：`{data['continuous_model'].get('hu_range')}`
- sound speed range：`{data['continuous_model'].get('sound_speed_range_m_s')}` m/s
- density range：`{data['continuous_model'].get('density_range_kg_m3')}` kg/m3
- alpha range：`{data['continuous_model'].get('alpha_range_db_mhz_cm')}` dB/MHz/cm

## 可信度判断

当前可信度：**exploratory only**。

理由：

1. 连续公式已经在代码中实现，但公式来源、单位和 HU clamp 还没有完成证据抽取。
2. profile 自身仍写着 `review_pending_do_not_use_as_default`。
3. binary/continuous standard run 的近似一致只说明该组合下差异很小，不能证明 continuous mapping 物理正确。
4. 当前结果仍不是 paper-grade：缺少完整网格收敛、边界/PML 复核、公式来源审计和多病例验证。

## 当前主线

下一步只能进入：

1. 源码/论文公式抽取；
2. model-build-only validation；
3. profile notes 与 summary schema 的一致性修复。

在这些完成前，不应继续跑新的 CT pressure 对照。
"""


def make_formula_report(audit: dict[str, Any]) -> str:
    cont = audit.get("continuous_mapping_config", {})
    return f"""# Continuous CT-HU Mapping 实现公式审计

## 当前实现状态

- builder：`{audit['builder_path']}`
- `continuous_property_volume()` 存在：`{audit['function_present']}`
- `save_model()` 调用 continuous property：`{audit['save_model_uses_continuous_profile']}`
- profile mapping type：`{audit['profile_mapping_type']}`
- profile review status：`{audit['profile_review_status']}`

## 当前 profile 配置

- HU clamp：`{cont.get('hu_min')}` 到 `{cont.get('hu_max')}`
- sound speed range：`{cont.get('sound_speed_range_m_s')}` m/s
- density range：`{cont.get('density_range_kg_m3')}` kg/m3
- alpha range：`{cont.get('alpha_range_db_mhz_cm')}` dB/MHz/cm

## 当前实际公式

代码当前逻辑为：

1. 先按 label 生成 binary material property volume。
2. 只有当 `mapping_type == "continuous_skull"` 时进入连续映射。
3. 只对 skull label 体素应用连续插值。
4. HU 先 clamp 到 `hu_min..hu_max`。
5. 对 sound speed、density、alpha 分别做线性插值：

```text
t = (clip(HU, hu_min, hu_max) - hu_min) / (hu_max - hu_min)
property = range_min + t * (range_max - range_min)
```

## 单位和证据风险

- 线性插值公式已经实现，但尚未从论文或公开代码抽取并核验。
- `alpha_db_mhz_cm` 被线性插值，但频率指数、吸收单位和 k-Wave 参数含义仍需审计。
- `hu_max=2000` 只是当前 profile 设置，不应自动成为平台默认。
- 既有 comparison report 的 focal voxel 参数相同，不能证明 skull path 上连续映射正确。
- profile notes 仍写着 builder 未应用 continuous mapping，已经与当前代码状态不一致，需要后续修正。

## 审计结论

当前状态：`implementation_exists_but_validation_blocked`。

允许作为探索性工程记录；不允许作为 validated continuous CT-HU baseline。
"""


def make_superseding_notice() -> str:
    return """# Superseding Notice: continuous_vs_binary_comparison

本说明覆盖并限定以下既有报告的解释边界：

```text
outputs/continuous_vs_binary_comparison/comparison_report.md
```

## 当前解释边界

该 comparison report 只能作为 **exploratory comparison** 阅读。它不能被引用为：

- validated continuous CT-HU mapping 结论；
- paper-grade reproduction；
- 医学安全或物理定量结论；
- 将 `continuous_skull` 升级为默认 profile 的证据。

## 为什么需要覆盖说明

仓库中已经存在 continuous model 和 standard runner pressure run，但 `continuous_skull.json` 仍然标记为 `review_pending_do_not_use_as_default`。这说明已有仿真先于完整 evidence gate 完成。

此外，报告中“约 0.3% 内差异”的结果只说明当前 exploratory 配置下 waveform metrics 接近。它不能证明 HU-to-sound-speed、HU-to-density、HU-to-attenuation 公式正确，也不能证明 skull path 物理建模可靠。

## 后续允许动作

下一步只能做：

1. 源论文/公开代码公式抽取；
2. attenuation 单位与频率指数审计；
3. model-build-only validation；
4. 修复 profile notes 与实际代码状态不一致的问题。

在上述步骤完成前，不应继续用 continuous profile 做新的 CT pressure 对照。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile exploratory continuous CT-HU mapping outputs.")
    parser.add_argument("--output-dir", default="outputs/ct_hu_mapping_reconciliation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {key: ROOT / value for key, value in DEFAULT_PATHS.items()}
    profile = read_json(paths["continuous_profile"])
    continuous_model_summary = read_json(paths["continuous_model_summary"])
    binary_summary = read_json(paths["binary_run_summary"])
    continuous_summary = read_json(paths["continuous_run_summary"])
    binary_status = read_json(paths["binary_runner_status"])
    continuous_status = read_json(paths["continuous_runner_status"])

    inventory = build_inventory(paths)
    write_inventory(out_dir / "output_inventory.csv", inventory)

    formula_audit = extract_continuous_formula_audit(paths["builder_code"], profile)
    write_json(out_dir / "implemented_formula_audit.json", formula_audit)
    write_md(out_dir / "implemented_formula_audit.md", make_formula_report(formula_audit))

    state_report = {
        "generated_at": now_iso(),
        "status": "exploratory_outputs_exist_but_not_validated_baseline",
        "authoritative_next_action": [
            "source_formula_extraction",
            "model_build_only_validation",
            "profile_note_and_summary_consistency_fix",
        ],
        "profile_review_status": profile.get("review_status") if profile else None,
        "profile_notes_are_stale": bool(
            profile
            and any("does not yet apply" in str(note) for note in profile.get("notes", []))
            and formula_audit["save_model_uses_continuous_profile"]
        ),
        "continuous_model": summary_slice(continuous_model_summary),
        "binary_run_summary": summary_slice(binary_summary),
        "continuous_run_summary": summary_slice(continuous_summary),
        "binary_run_status": summarize_run_status(binary_status),
        "continuous_run_status": summarize_run_status(continuous_status),
        "comparison_report_exists": paths["comparison_report"].exists(),
        "comparison_report_classification": "superseded_exploratory_report",
        "key_conclusions": [
            "Existing continuous outputs are exploratory.",
            "continuous_skull remains review_pending_do_not_use_as_default.",
            "Runner kwave_ok does not validate the CT-HU formula.",
            "The existing comparison report must not be interpreted as paper-grade or final physical evidence.",
        ],
        "inventory": inventory,
    }
    write_json(out_dir / "state_reconciliation_report.json", state_report)
    write_md(out_dir / "state_reconciliation_report.md", make_state_report(state_report))
    write_md(out_dir / "superseding_notice.md", make_superseding_notice())

    print(f"Wrote reconciliation package to {rel(out_dir)}")


if __name__ == "__main__":
    main()
