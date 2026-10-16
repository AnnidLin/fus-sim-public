from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Check:
    check_id: str
    title: str
    status: str
    evidence: str
    source: str
    blocks_pressure: bool = False
    blocks_default: bool = False
    blocks_paper_grade: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "title": self.title,
            "status": self.status,
            "evidence": self.evidence,
            "source": self.source,
            "blocks_pressure": self.blocks_pressure,
            "blocks_default": self.blocks_default,
            "blocks_paper_grade": self.blocks_paper_grade,
        }


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any] | None, keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def as_bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def load_inputs() -> dict[str, dict[str, Any] | None]:
    paths = {
        "stage_summary": PROJECT_ROOT
        / "outputs/source_backed_alpha_stage_report/source_backed_alpha_stage_summary.json",
        "model_summary": PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_prestus_fit_alpha_power_2/summary.json",
        "dry_run_summary": PROJECT_ROOT
        / "outputs/fit_alpha_power_migration/079_fit_alpha_power_2_dry_run/quality_dry_run_summary.json",
        "entry_path_summary": PROJECT_ROOT
        / "outputs/entry_path_property_profiles/079_candidate_006_fit_alpha_power_2/entry_path_property_summary.json",
        "formula_audit": PROJECT_ROOT / "outputs/fit_alpha_power_formula_audit/formula_audit_report.json",
        "matlab_crosscheck": PROJECT_ROOT / "outputs/fit_alpha_power_matlab_crosscheck/crosscheck_summary.json",
        "fit_alpha_gap": PROJECT_ROOT / "outputs/evidence_briefs/fit_alpha_power_migration/gap_feedback.json",
    }
    return {name: read_json(path) for name, path in paths.items()}


def input_paths() -> dict[str, str]:
    return {
        "stage_summary": "outputs/source_backed_alpha_stage_report/source_backed_alpha_stage_summary.json",
        "model_summary": "outputs/ct_acoustic_model_3d_profile_prestus_fit_alpha_power_2/summary.json",
        "dry_run_summary": "outputs/fit_alpha_power_migration/079_fit_alpha_power_2_dry_run/quality_dry_run_summary.json",
        "entry_path_summary": "outputs/entry_path_property_profiles/079_candidate_006_fit_alpha_power_2/entry_path_property_summary.json",
        "formula_audit": "outputs/fit_alpha_power_formula_audit/formula_audit_report.json",
        "matlab_crosscheck": "outputs/fit_alpha_power_matlab_crosscheck/crosscheck_summary.json",
        "fit_alpha_gap": "outputs/evidence_briefs/fit_alpha_power_migration/gap_feedback.json",
    }


def check_inputs(data: dict[str, dict[str, Any] | None]) -> list[Check]:
    checks: list[Check] = []
    paths = input_paths()
    for name, payload in data.items():
        ok = payload is not None
        checks.append(
            Check(
                check_id=f"input.{name}",
                title=f"Required input exists: {name}",
                status="pass" if ok else "block",
                evidence="JSON parsed" if ok else "Missing or unreadable JSON",
                source=paths[name],
                blocks_pressure=not ok,
                blocks_default=not ok,
                blocks_paper_grade=not ok,
            )
        )
    return checks


def check_alpha_semantics(data: dict[str, dict[str, Any] | None]) -> list[Check]:
    stage_conflicts = nested(data["stage_summary"], ["state_conflicts"], [])
    gap_allowed = as_bool_or_none(
        nested(data["fit_alpha_gap"], ["key_results", "pressure_allowed_by_alpha_semantics"])
    )
    dry_allowed = as_bool_or_none(
        nested(data["dry_run_summary"], ["model", "alpha_semantics", "pressure_allowed_by_alpha_semantics"])
    )
    dry_metadata_allowed = as_bool_or_none(
        nested(data["dry_run_summary"], ["model", "alpha_semantics", "alpha_pressure_allowed_metadata"])
    )
    model_allowed = as_bool_or_none(
        nested(data["model_summary"], ["mapping_profile", "alpha_semantics", "pressure_allowed"])
    )
    formula_allowed = as_bool_or_none(nested(data["formula_audit"], ["pressure_decision", "pressure_allowed"]))

    observed = {
        "gap_feedback": gap_allowed,
        "dry_run_summary": dry_allowed,
        "dry_run_metadata": dry_metadata_allowed,
        "model_summary": model_allowed,
        "formula_audit": formula_allowed,
    }
    non_null = {key: value for key, value in observed.items() if value is not None}
    conflict = len(set(non_null.values())) > 1 or bool(stage_conflicts)
    missing = [key for key, value in observed.items() if value is None]

    checks = [
        Check(
            check_id="alpha_semantics.no_pressure_allowed_conflict",
            title="Alpha pressure-allowed fields are consistent",
            status="block" if conflict else ("warn" if missing else "pass"),
            evidence=f"observed={observed}; stage_conflicts={stage_conflicts}; missing={missing}",
            source="fit_alpha_gap + dry_run_summary + model_summary + formula_audit + stage_summary",
            blocks_pressure=conflict or bool(missing),
            blocks_default=conflict or bool(missing),
            blocks_paper_grade=True,
        )
    ]
    return checks


def check_formula_audit(data: dict[str, dict[str, Any] | None]) -> list[Check]:
    status = nested(data["formula_audit"], ["status"])
    pressure_allowed = as_bool_or_none(nested(data["formula_audit"], ["pressure_decision", "pressure_allowed"]))
    formula_checks = nested(data["formula_audit"], ["formula_checks"], {})
    all_formula_checks = isinstance(formula_checks, dict) and all(bool(v) for v in formula_checks.values())
    ok = status == "formula_migration_consistent_model_build_only" and all_formula_checks
    check_status = "warn" if ok and pressure_allowed is False else "block"
    return [
        Check(
            check_id="formula_audit.model_build_only",
            title="Formula audit is consistent but model-build-only",
            status=check_status,
            evidence=f"status={status}; formula_checks={formula_checks}; pressure_allowed={pressure_allowed}",
            source="outputs/fit_alpha_power_formula_audit/formula_audit_report.json",
            blocks_pressure=pressure_allowed is not False,
            blocks_default=True,
            blocks_paper_grade=True,
        )
    ]


def check_matlab_crosscheck(data: dict[str, dict[str, Any] | None]) -> list[Check]:
    matlab_available = as_bool_or_none(nested(data["matlab_crosscheck"], ["matlab_available"]))
    matlab_executed = as_bool_or_none(nested(data["matlab_crosscheck"], ["matlab_executed"]))
    comparison = nested(data["matlab_crosscheck"], ["comparison"])
    comparison_passed = as_bool_or_none(nested(data["matlab_crosscheck"], ["comparison", "passed"]))
    executed_and_passed = matlab_executed is True and comparison_passed is True
    return [
        Check(
            check_id="matlab_crosscheck.executed_and_passed",
            title="MATLAB/Python cross-check executed and passed",
            status="pass" if executed_and_passed else "block",
            evidence=(
                f"matlab_available={matlab_available}; matlab_executed={matlab_executed}; "
                f"comparison={comparison}"
            ),
            source="outputs/fit_alpha_power_matlab_crosscheck/crosscheck_summary.json",
            blocks_pressure=not executed_and_passed,
            blocks_default=not executed_and_passed,
            blocks_paper_grade=not executed_and_passed,
        )
    ]


def check_entry_path(data: dict[str, dict[str, Any] | None]) -> list[Check]:
    fit_stats = nested(
        data["entry_path_summary"],
        ["model_summaries", "prestus_fit_alpha_power_2"],
        {},
    )
    sound_speed = nested(fit_stats, ["sound_speed_skull"], {})
    density = nested(fit_stats, ["density_skull"], {})
    skull_count = nested(fit_stats, ["skull_samples"], 0)
    sound_speed_median = nested(sound_speed, ["median"])
    density_median = nested(density, ["median"])
    near_soft_tissue = (
        isinstance(sound_speed_median, (int, float))
        and isinstance(density_median, (int, float))
        and sound_speed_median <= 1600
        and density_median <= 1100
    )
    has_skull_samples = isinstance(skull_count, int) and skull_count > 0
    status = "block" if near_soft_tissue or not has_skull_samples else "pass"
    return [
        Check(
            check_id="entry_path.skull_property_plausibility",
            title="Entry-path skull c/rho does not collapse near water or soft tissue",
            status=status,
            evidence=(
                f"skull_samples={skull_count}; sound_speed_skull={sound_speed}; "
                f"density_skull={density}; near_soft_tissue_signal={near_soft_tissue}"
            ),
            source="outputs/entry_path_property_profiles/079_candidate_006_fit_alpha_power_2/entry_path_property_summary.json",
            blocks_pressure=near_soft_tissue or not has_skull_samples,
            blocks_default=True,
            blocks_paper_grade=True,
        )
    ]


def check_dry_run_only(data: dict[str, dict[str, Any] | None]) -> list[Check]:
    dry_only = as_bool_or_none(nested(data["dry_run_summary"], ["dry_run_quality_only"]))
    note = nested(data["dry_run_summary"], ["note"])
    output_completeness = nested(data["dry_run_summary"], ["simulation_quality", "output_completeness"], {})
    pressure_output_present = False
    if isinstance(output_completeness, dict):
        pressure_output_present = bool(output_completeness.get("pressure_max_mpa"))
    ok = dry_only is True and not pressure_output_present
    return [
        Check(
            check_id="dry_run.no_pressure_output",
            title="Dry-run did not generate pressure output",
            status="pass" if ok else "block",
            evidence=f"dry_run_quality_only={dry_only}; note={note}; output_completeness={output_completeness}",
            source="outputs/fit_alpha_power_migration/079_fit_alpha_power_2_dry_run/quality_dry_run_summary.json",
            blocks_pressure=not ok,
            blocks_default=not ok,
            blocks_paper_grade=not ok,
        )
    ]


def build_summary(data: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    checks: list[Check] = []
    checks.extend(check_inputs(data))
    checks.extend(check_alpha_semantics(data))
    checks.extend(check_formula_audit(data))
    checks.extend(check_matlab_crosscheck(data))
    checks.extend(check_entry_path(data))
    checks.extend(check_dry_run_only(data))

    pressure_blockers = [check for check in checks if check.blocks_pressure and check.status != "pass"]
    default_blockers = [check for check in checks if check.blocks_default and check.status != "pass"]
    paper_blockers = [check for check in checks if check.blocks_paper_grade and check.status != "pass"]

    profile_id = (
        nested(data["fit_alpha_gap"], ["key_results", "profile_id"])
        or nested(data["formula_audit"], ["model_build_result", "profile_id"])
        or "prestus_fit_alpha_power_2"
    )
    decision = {
        "profile_id": profile_id,
        "pressure_eligible": len(pressure_blockers) == 0,
        "default_profile_eligible": len(default_blockers) == 0,
        "paper_grade_eligible": len(paper_blockers) == 0,
        "promotion_allowed": False,
        "recommended_state": "remain_exploratory_pressure_blocked",
        "reason": "Conservative gate blocks promotion until alpha semantics conflict, MATLAB cross-check, and entry-path plausibility are resolved.",
    }
    decision["promotion_allowed"] = (
        decision["pressure_eligible"] and decision["default_profile_eligible"] and decision["paper_grade_eligible"]
    )
    if decision["promotion_allowed"]:
        decision["recommended_state"] = "promotion_candidate_requires_user_review"
        decision["reason"] = "All automated gate checks passed; user review is still required before changing defaults."

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "profile promotion gate only; read-only; no k-Wave; no CT rebuild",
        "inputs": {
            "paths": input_paths(),
            "exists": {name: payload is not None for name, payload in data.items()},
        },
        "decision": decision,
        "blockers": {
            "pressure": [check.to_dict() for check in pressure_blockers],
            "default_profile": [check.to_dict() for check in default_blockers],
            "paper_grade": [check.to_dict() for check in paper_blockers],
        },
        "checks": [check.to_dict() for check in checks],
        "not_executed": [
            "k-Wave pressure simulation",
            "CT acoustic model rebuild",
            "thermal simulation",
            "profile default promotion",
        ],
    }


def status_label(status: str) -> str:
    return {"pass": "PASS", "warn": "WARN", "block": "BLOCK"}.get(status, status.upper())


def build_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    checks = summary["checks"]
    lines = [
        "# Profile Promotion Gate Report",
        "",
        "> Scope: read-only evidence gate. This report did not run k-Wave, rebuild CT, or promote any profile.",
        "",
        "## Decision",
        "",
        f"- profile: `{decision['profile_id']}`",
        f"- pressure eligible: `{decision['pressure_eligible']}`",
        f"- default profile eligible: `{decision['default_profile_eligible']}`",
        f"- paper-grade eligible: `{decision['paper_grade_eligible']}`",
        f"- promotion allowed: `{decision['promotion_allowed']}`",
        f"- recommended state: `{decision['recommended_state']}`",
        f"- reason: {decision['reason']}",
        "",
        "## Checklist",
        "",
        "| Status | Check | Blocks | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for check in checks:
        blocks = []
        if check["blocks_pressure"]:
            blocks.append("pressure")
        if check["blocks_default"]:
            blocks.append("default")
        if check["blocks_paper_grade"]:
            blocks.append("paper-grade")
        block_text = ", ".join(blocks) if blocks else "none"
        evidence = str(check["evidence"]).replace("\n", " ")
        if len(evidence) > 260:
            evidence = evidence[:257] + "..."
        lines.append(f"| {status_label(check['status'])} | `{check['check_id']}` | {block_text} | {evidence} |")
    lines.extend(
        [
            "",
            "## Conservative Interpretation",
            "",
            "- `prestus_fit_alpha_power_2` remains exploratory/review-pending.",
            "- The current reproducible baseline remains `simple_hu300`.",
            "- No new source-backed alpha pressure run should be started until the blockers are resolved and explicitly authorized.",
            "",
            "## Not Executed",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["not_executed"])
    lines.append("")
    return "\n".join(lines)


def write_gap_feedback(output_dir: Path, summary: dict[str, Any]) -> None:
    brief_dir = PROJECT_ROOT / "outputs/evidence_briefs/profile_promotion_gate"
    brief_dir.mkdir(parents=True, exist_ok=True)
    feedback = {
        "module": "profile_promotion_gate",
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read existing source-backed alpha evidence summaries",
            "evaluated profile promotion checklist",
            "generated profile promotion gate report and JSON summary",
        ],
        "modified_files": [
            "evaluate_profile_promotion_gate.py",
            "outputs/evidence_briefs/profile_promotion_gate/evidence_brief.md",
            "outputs/evidence_briefs/profile_promotion_gate/evidence_brief.json",
        ],
        "outputs": {
            "gate_report": rel(output_dir / "profile_promotion_gate_report.md"),
            "gate_summary": rel(output_dir / "profile_promotion_gate_summary.json"),
        },
        "decision": summary["decision"],
        "not_executed": summary["not_executed"],
        "deviations": [
            {
                "deviation": "rg search failed with access denied in the current PowerShell environment.",
                "evidence": "PowerShell reported Program 'rg.exe' failed to run: Access is denied.",
                "adjustment": "Used Get-ChildItem/Where-Object for file discovery and continued with read-only checks.",
            }
        ],
        "remaining_gaps": [
            "MATLAB-side cross-check has not been executed or imported.",
            "alpha pressure_allowed metadata conflict remains unresolved.",
            "entry-path low-HU skull-edge c/rho plausibility remains unresolved.",
        ],
        "recommended_next_step": "Resolve alpha pressure gate conflict and import MATLAB cross-check before considering any source-backed alpha pressure run.",
    }
    (brief_dir / "gap_feedback.json").write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = "\n".join(
        [
            "# Gap Feedback：profile promotion gate",
            "",
            "## 实际执行",
            "",
            "- 读取现有 source-backed alpha evidence summary、dry-run summary、entry-path summary、formula audit 和 MATLAB cross-check summary。",
            "- 生成 profile promotion checklist/report。",
            "",
            "## 输出",
            "",
            f"- `{rel(output_dir / 'profile_promotion_gate_report.md')}`",
            f"- `{rel(output_dir / 'profile_promotion_gate_summary.json')}`",
            "",
            "## 当前判断",
            "",
            f"- promotion allowed: `{summary['decision']['promotion_allowed']}`",
            f"- recommended state: `{summary['decision']['recommended_state']}`",
            f"- reason: {summary['decision']['reason']}",
            "",
            "## 未执行",
            "",
            "- 未运行 k-Wave。",
            "- 未重建 CT 声学模型。",
            "- 未提升任何 profile 为默认。",
            "",
            "## 偏差与调节",
            "",
            "- `rg` 在当前 PowerShell 环境中 access denied，已改用 `Get-ChildItem` 搜索文件。",
            "",
            "## 下一步",
            "",
            "先解决 alpha pressure gate 冲突并导入/执行 MATLAB cross-check，再讨论是否进入受控 pressure sanity run。",
            "",
        ]
    )
    (brief_dir / "gap_feedback.md").write_text(md, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate source-backed profile promotion gates.")
    parser.add_argument(
        "--output-dir",
        default="outputs/profile_promotion_gate/prestus_fit_alpha_power_2",
        help="Directory for the gate report and JSON summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_inputs()
    summary = build_summary(data)
    (output_dir / "profile_promotion_gate_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "profile_promotion_gate_report.md").write_text(build_markdown(summary), encoding="utf-8-sig")
    write_gap_feedback(output_dir, summary)
    print(f"Wrote {output_dir / 'profile_promotion_gate_report.md'}")
    print(f"Wrote {output_dir / 'profile_promotion_gate_summary.json'}")


if __name__ == "__main__":
    main()
