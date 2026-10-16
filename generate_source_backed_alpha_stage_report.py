from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def exists(path: Path) -> bool:
    return path.exists()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def nested(data: dict[str, Any] | None, keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def load_inputs() -> dict[str, Any]:
    paths = {
        "source_options_gap": PROJECT_ROOT
        / "outputs/evidence_briefs/source_backed_alpha_profile_options/gap_feedback.json",
        "no_dispersion_gap": PROJECT_ROOT
        / "outputs/evidence_briefs/no_dispersion_model_build_validation/gap_feedback.json",
        "fit_alpha_gap": PROJECT_ROOT / "outputs/evidence_briefs/fit_alpha_power_migration/gap_feedback.json",
        "formula_audit_gap": PROJECT_ROOT
        / "outputs/evidence_briefs/fit_alpha_power_formula_audit/gap_feedback.json",
        "entry_path_gap": PROJECT_ROOT / "outputs/evidence_briefs/entry_path_property_profile/gap_feedback.json",
        "matlab_gap": PROJECT_ROOT / "outputs/evidence_briefs/fit_alpha_power_matlab_crosscheck/gap_feedback.json",
        "fit_alpha_dry_run": PROJECT_ROOT
        / "outputs/fit_alpha_power_migration/079_fit_alpha_power_2_dry_run/quality_dry_run_summary.json",
        "entry_path_summary": PROJECT_ROOT
        / "outputs/entry_path_property_profiles/079_candidate_006_fit_alpha_power_2/entry_path_property_summary.json",
        "matlab_crosscheck": PROJECT_ROOT / "outputs/fit_alpha_power_matlab_crosscheck/crosscheck_summary.json",
        "fit_alpha_model_summary": PROJECT_ROOT
        / "outputs/ct_acoustic_model_3d_profile_prestus_fit_alpha_power_2/summary.json",
    }
    return {
        "paths": {name: rel(path) for name, path in paths.items()},
        "exists": {name: exists(path) for name, path in paths.items()},
        "data": {name: read_json(path) for name, path in paths.items()},
    }


def summarize_entry_path(entry_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not entry_summary:
        return {"available": False}
    model_summaries = entry_summary.get("model_summaries", {})
    result: dict[str, Any] = {
        "available": True,
        "target_index_ijk": entry_summary.get("target_index_ijk"),
        "entry_index_ijk": entry_summary.get("entry_index_ijk"),
        "source_center_index_ijk": entry_summary.get("source_center_index_ijk"),
        "sample_count": entry_summary.get("sample_count"),
        "model_count": len(model_summaries) if isinstance(model_summaries, dict) else None,
        "skull_sample_count_by_model": {},
        "fit_alpha_path_observation": None,
    }
    if isinstance(model_summaries, dict):
        for name, stats in model_summaries.items():
            result["skull_sample_count_by_model"][name] = stats.get("skull_samples")
        fit_stats = model_summaries.get("prestus_fit_alpha_power_2", {})
        if fit_stats:
            result["fit_alpha_path_observation"] = {
                "sound_speed_skull_range_m_s": fit_stats.get("sound_speed_skull"),
                "density_skull_range_kg_m3": fit_stats.get("density_skull"),
                "alpha_skull_range_prefactor": fit_stats.get("alpha_skull"),
            }
    return result


def build_summary(inputs: dict[str, Any]) -> dict[str, Any]:
    data = inputs["data"]
    fit_gap = data["fit_alpha_gap"]
    dry = data["fit_alpha_dry_run"]
    entry_summary = data["entry_path_summary"]
    matlab_summary = data["matlab_crosscheck"]

    migration_pressure_allowed = nested(
        fit_gap, ["key_results", "pressure_allowed_by_alpha_semantics"], default=None
    )
    dry_pressure_allowed = nested(
        dry, ["model", "alpha_semantics", "pressure_allowed_by_alpha_semantics"], default=None
    )
    metadata_pressure_allowed = nested(
        dry, ["model", "alpha_semantics", "alpha_pressure_allowed_metadata"], default=None
    )
    status_conflicts = []
    if migration_pressure_allowed is not None and dry_pressure_allowed is not None:
        if bool(migration_pressure_allowed) != bool(dry_pressure_allowed):
            status_conflicts.append(
                {
                    "field": "pressure_allowed_by_alpha_semantics",
                    "gap_feedback_value": migration_pressure_allowed,
                    "dry_run_summary_value": dry_pressure_allowed,
                    "judgement": "treat_as_unresolved_conflict_do_not_promote",
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "source-backed alpha mapping stage report only; no k-Wave, no CT rebuild",
        "inputs": {"paths": inputs["paths"], "exists": inputs["exists"]},
        "completed_steps": [
            "source-backed alpha profile options generated",
            "no-dispersion experimental model-build validation completed",
            "PRESTUS fit-alpha-power=2 model-build validation completed",
            "fitPowerLawParamsMulti formula/unit audit completed",
            "079 candidate_006 entry-path property profile and plots generated",
            "MATLAB/Python cross-check package generated",
        ],
        "current_baseline": {
            "profile": "simple_hu300",
            "status": "current reproducible baseline for 079 standard-review",
            "reason": "source-backed alpha routes remain exploratory or review-pending",
        },
        "source_backed_routes": {
            "no_dispersion": {
                "status": nested(
                    data["no_dispersion_gap"], ["current_judgement"], "experimental dry-run/model-build only"
                ),
                "pressure_allowed": nested(
                    data["no_dispersion_gap"], ["key_results", "pressure_allowed_by_alpha_semantics"], False
                ),
            },
            "prestus_fit_alpha_power_2": {
                "profile_id": nested(fit_gap, ["key_results", "profile_id"], "prestus_fit_alpha_power_2"),
                "review_status": nested(fit_gap, ["key_results", "review_status"], "review_pending"),
                "alpha_range_db_mhz2_cm": nested(fit_gap, ["key_results", "alpha_range_db_mhz2_cm"]),
                "dry_run_ppw": nested(fit_gap, ["key_results", "dry_run_ppw_min_sound_speed"]),
                "pressure_allowed_gap_feedback": migration_pressure_allowed,
                "pressure_allowed_dry_run_summary": dry_pressure_allowed,
                "alpha_pressure_allowed_metadata": metadata_pressure_allowed,
            },
        },
        "entry_path_summary": summarize_entry_path(entry_summary),
        "matlab_crosscheck": {
            "package_ready": inputs["exists"]["matlab_crosscheck"],
            "matlab_available": nested(matlab_summary, ["matlab_available"], False),
            "matlab_executed": nested(matlab_summary, ["matlab_executed"], False),
            "case_count": nested(matlab_summary, ["case_count"]),
            "recommended_next_step": "如果有 MATLAB 环境，运行 `run_fit_alpha_crosscheck.m`，然后把 `matlab_outputs.csv` 导回本项目做误差比对。",
        },
        "state_conflicts": status_conflicts,
        "current_gaps": [
            "MATLAB cross-check has not been executed on this machine.",
            "fit-alpha-power=2 route has model-build and formula audit evidence, but not a validated pressure baseline gate.",
            "entry-path review suggests low-HU skull-edge samples can map to near-water/soft-tissue c/rho under PRESTUS-style routes.",
            "alpha prefactor in dB/(MHz^2 cm) must not be directly compared with binary dB/(MHz cm) coefficients.",
            "Any conflict between dry-run metadata and gap_feedback must be resolved before pressure authorization.",
        ],
        "next_recommendation": {
            "primary": "先解决 alpha pressure gate：执行或导入 MATLAB 交叉测试结果，或者建立 profile promotion checklist，并在 checklist 通过前保持 pressure blocked。",
            "secondary": "如果希望加快主线，先把 source-backed alpha 冻结为 exploratory，回到 simple_hu300 baseline 做 standard/paper-grade 路线复核。",
            "not_now": [
                "不要为 source-backed alpha 路线启动新的 k-Wave pressure 仿真。",
                "不要把 prestus_fit_alpha_power_2 升级为默认 profile。",
                "不要覆盖已有 CT、pressure 或 thermal 输出。",
            ],
        },
    }


def build_markdown(summary: dict[str, Any]) -> str:
    fit = summary["source_backed_routes"]["prestus_fit_alpha_power_2"]
    entry = summary["entry_path_summary"]
    matlab = summary["matlab_crosscheck"]
    conflicts = summary["state_conflicts"]
    conflict_text = (
        "\n".join(
            f"- `{item['field']}`: gap_feedback={item['gap_feedback_value']}, "
            f"dry_run_summary={item['dry_run_summary_value']}；处理：{item['judgement']}"
            for item in conflicts
        )
        if conflicts
        else "- 未发现可自动判定的字段冲突；仍按 review-pending 处理。"
    )

    return "\n".join(
        [
            "# Source-backed alpha mapping 阶段报告",
            "",
            "> 范围：只汇总现有证据和状态，不运行 k-Wave，不重建 CT，不覆盖既有声压或热结果。",
            "",
            "## 当前进度",
            "",
            "- 已完成 source-backed alpha 两条路线的方案拆分：`no_dispersion` 与 `prestus_fit_alpha_power_2`。",
            "- 已完成 `prestus_fit_alpha_power_2` 的 079 model-build-only 输出、dry-run quality 和公式审计。",
            "- 已完成 079 `candidate_006` entry-path 材料属性剖面和可视化。",
            "- 已生成 MATLAB/Python 交叉测试包，但本机没有执行 MATLAB 侧结果。",
            "",
            "## 当前可用基线",
            "",
            "- 当前可复现 baseline 仍是 `simple_hu300`。",
            "- `prestus_fit_alpha_power_2` 与 `no_dispersion` 均不能自动替代 baseline。",
            "",
            "## fit-alpha-power=2 状态",
            "",
            f"- profile: `{fit['profile_id']}`",
            f"- review status: `{fit['review_status']}`",
            f"- alpha range: `{fit['alpha_range_db_mhz2_cm']}` dB/(MHz^2 cm) prefactor",
            f"- dry-run PPW: `{fit['dry_run_ppw']}`",
            f"- pressure_allowed in gap feedback: `{fit['pressure_allowed_gap_feedback']}`",
            f"- pressure_allowed in dry-run summary: `{fit['pressure_allowed_dry_run_summary']}`",
            f"- alpha_pressure_allowed metadata: `{fit['alpha_pressure_allowed_metadata']}`",
            "",
            "## 状态冲突",
            "",
            conflict_text,
            "",
            "结论：只要存在 pressure gate 状态不一致，就按更保守策略处理：`review_pending / do not promote / no new pressure run`。",
            "",
            "## Entry-path 发现",
            "",
            f"- target index: `{entry.get('target_index_ijk')}`",
            f"- entry index: `{entry.get('entry_index_ijk')}`",
            f"- source center: `{entry.get('source_center_index_ijk')}`",
            f"- sampled points: `{entry.get('sample_count')}`",
            f"- skull sample counts: `{entry.get('skull_sample_count_by_model')}`",
            f"- fit-alpha path observation: `{entry.get('fit_alpha_path_observation')}`",
            "",
            "解释：该路径上的 PRESTUS-style route 在低 HU 颅骨边缘可能给出接近水/软组织的声速和密度。这个现象需要进一步审查，不应被写成 validated skull mapping。",
            "",
            "## MATLAB 交叉测试",
            "",
            f"- package ready: `{matlab['package_ready']}`",
            f"- MATLAB available: `{matlab['matlab_available']}`",
            f"- MATLAB executed: `{matlab['matlab_executed']}`",
            f"- case count: `{matlab['case_count']}`",
            f"- next: {matlab['recommended_next_step']}",
            "",
            "## 现阶段差距",
            "",
            *[f"- {item}" for item in summary["current_gaps"]],
            "",
            "## 下一步建议",
            "",
            f"- 首选：{summary['next_recommendation']['primary']}",
            f"- 若要加快主线：{summary['next_recommendation']['secondary']}",
            "- 暂不做：",
            *[f"  - {item}" for item in summary["next_recommendation"]["not_now"]],
            "",
        ]
    )


def write_gap_feedback(output_dir: Path, summary: dict[str, Any]) -> None:
    brief_dir = PROJECT_ROOT / "outputs/evidence_briefs/source_backed_alpha_stage_report"
    brief_dir.mkdir(parents=True, exist_ok=True)
    feedback = {
        "module": "source_backed_alpha_stage_report",
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read existing source-backed alpha reports and summaries",
            "generated stage report",
            "identified state conflicts and current gaps",
        ],
        "not_executed": [
            "k-Wave pressure simulation",
            "CT acoustic model rebuild",
            "thermal simulation",
            "profile default promotion",
        ],
        "outputs": {
            "stage_report": rel(output_dir / "source_backed_alpha_stage_report.md"),
            "stage_summary": rel(output_dir / "source_backed_alpha_stage_summary.json"),
        },
        "state_conflicts": summary["state_conflicts"],
        "current_judgement": "source-backed alpha routes remain exploratory/review-pending; simple_hu300 remains baseline",
        "recommended_next_step": summary["next_recommendation"]["primary"],
    }
    (brief_dir / "gap_feedback.json").write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = "\n".join(
        [
            "# Gap Feedback：source-backed alpha mapping 阶段报告",
            "",
            "## 实际执行",
            "",
            "- 读取现有 source-backed alpha 相关 gap_feedback、dry-run summary、entry-path summary 和 cross-check summary。",
            "- 生成阶段报告与 JSON summary。",
            "",
            "## 未执行",
            "",
            "- 未运行 k-Wave。",
            "- 未重建 CT 声学模型。",
            "- 未提升任何 profile 为默认。",
            "",
            "## 当前判断",
            "",
            "source-backed alpha routes 仍为 exploratory/review-pending；`simple_hu300` 仍是当前可复现 baseline。",
            "",
            "## 下一步",
            "",
            summary["next_recommendation"]["primary"],
            "",
        ]
    )
    (brief_dir / "gap_feedback.md").write_text(md, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a source-backed alpha mapping stage report.")
    parser.add_argument("--output-dir", default="outputs/source_backed_alpha_stage_report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs()
    summary = build_summary(inputs)
    (output_dir / "source_backed_alpha_stage_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "source_backed_alpha_stage_report.md").write_text(
        build_markdown(summary), encoding="utf-8-sig"
    )
    write_gap_feedback(output_dir, summary)
    print(f"Wrote {output_dir / 'source_backed_alpha_stage_report.md'}")
    print(f"Wrote {output_dir / 'source_backed_alpha_stage_summary.json'}")


if __name__ == "__main__":
    main()
