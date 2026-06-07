from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE = "simple_hu300_post_pressure_readiness"
OUT_DIR = PROJECT_ROOT / "outputs" / MODULE / "079_candidate_006"
BRIEF_DIR = PROJECT_ROOT / "outputs" / "evidence_briefs" / MODULE


@dataclass(frozen=True)
class ReadinessCheck:
    check_id: str
    title: str
    status: str
    category: str
    evidence: str
    source: str
    recommended_next: str
    blocks_paper_grade: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "title": self.title,
            "status": self.status,
            "category": self.category,
            "evidence": self.evidence,
            "source": self.source,
            "recommended_next": self.recommended_next,
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


def input_paths() -> dict[str, Path]:
    run_dir = PROJECT_ROOT / "outputs/ct_standard_pressure_authorization/079_candidate_006_dx0p75_pml12_standard"
    return {
        "previous_readiness": PROJECT_ROOT
        / "outputs/simple_hu300_paper_grade_readiness/079_candidate_006/paper_grade_readiness_summary.json",
        "standard_pressure_execution": run_dir / "standard_pressure_execution_summary.json",
        "kwave_summary": run_dir / "summary.json",
        "focus_metrics": run_dir / "focus_metrics.json",
        "runner_status": run_dir / "runner_status.json",
        "dx075_model_dry_run": PROJECT_ROOT
        / "outputs/ct_grid_convergence_plan/079_candidate_006/dx0p75_model_build_dry_run_summary.json",
        "pml12_dry_run": PROJECT_ROOT
        / "outputs/ct_pml_boundary_review/079_candidate_006_dx0p75/pml12_dry_run_summary.json",
        "progress_gate": PROJECT_ROOT
        / "outputs/simple_hu300_progress_goal_gate/079_candidate_006/current_progress_goal_gate_summary.json",
        "freefield_quality": PROJECT_ROOT / "outputs/freefield_quality_report/freefield_quality_summary.json",
        "simulation_presets": PROJECT_ROOT / "simulation_presets.json",
    }


def load_inputs() -> dict[str, dict[str, Any] | None]:
    return {name: read_json(path) for name, path in input_paths().items()}


def source_paths() -> dict[str, str]:
    return {name: rel(path) for name, path in input_paths().items()}


def build_checks(data: dict[str, dict[str, Any] | None]) -> list[ReadinessCheck]:
    paths = source_paths()
    checks: list[ReadinessCheck] = []

    for name, payload in data.items():
        checks.append(
            ReadinessCheck(
                check_id=f"input.{name}",
                title=f"Input available: {name}",
                status="pass" if payload is not None else "block",
                category="inputs",
                evidence="JSON parsed" if payload is not None else "missing or unreadable JSON",
                source=paths[name],
                recommended_next="Restore or regenerate missing input." if payload is None else "No action.",
                blocks_paper_grade=payload is None,
            )
        )

    runner_status = nested(data["runner_status"], ["status"])
    pressure_completed = nested(data["standard_pressure_execution"], ["decision", "standard_pressure_run_completed"])
    core_outputs = nested(data["standard_pressure_execution"], ["runner", "core_output_exists"], {})
    checks.append(
        ReadinessCheck(
            check_id="ct.standard_pressure_completed",
            title="standard pressure run is now complete",
            status="pass" if runner_status == "kwave_ok" and pressure_completed is True else "block",
            category="standard_pressure",
            evidence=f"runner_status={runner_status}; completed={pressure_completed}; core_outputs={core_outputs}",
            source=paths["standard_pressure_execution"],
            recommended_next="Use this as standard engineering pressure evidence only.",
            blocks_paper_grade=False,
        )
    )

    preset = nested(data["standard_pressure_execution"], ["simulation_quality", "preset"])
    is_paper_grade = nested(data["standard_pressure_execution"], ["simulation_quality", "is_paper_grade"])
    checks.append(
        ReadinessCheck(
            check_id="preset.paper_grade",
            title="run preset is standard, not paper-grade",
            status="block" if is_paper_grade is False else "pass",
            category="preset",
            evidence=f"preset={preset}; is_paper_grade={is_paper_grade}",
            source=paths["standard_pressure_execution"],
            recommended_next="Plan a separate paper-grade candidate only after convergence, boundary, CFL, and environment gaps close.",
            blocks_paper_grade=is_paper_grade is not True,
        )
    )

    alpha_status = nested(data["standard_pressure_execution"], ["alpha_semantics", "alpha_semantics_status"])
    alpha_allowed = nested(data["standard_pressure_execution"], ["alpha_semantics", "pressure_allowed_by_alpha_semantics"])
    checks.append(
        ReadinessCheck(
            check_id="alpha.semantics",
            title="alpha semantics remain incomplete",
            status="block",
            category="alpha",
            evidence=f"alpha_semantics_status={alpha_status}; pressure_allowed_by_alpha_semantics={alpha_allowed}",
            source=paths["standard_pressure_execution"],
            recommended_next="Do not promote to validated pressure baseline until alpha semantics are explicitly resolved.",
            blocks_paper_grade=True,
        )
    )

    grid = nested(data["standard_pressure_execution"], ["simulation_quality", "grid_size"])
    ppw = nested(data["standard_pressure_execution"], ["simulation_quality", "ppw_min_sound_speed"])
    checks.append(
        ReadinessCheck(
            check_id="ct.grid_convergence",
            title="CT pressure-level grid convergence is incomplete",
            status="block",
            category="ct_numerical_quality",
            evidence=f"standard_run_grid={grid}; ppw={ppw}; only one dx pressure point exists",
            source=paths["standard_pressure_execution"],
            recommended_next="Prepare a cautious convergence plan before any additional pressure run; do not batch-run cases.",
            blocks_paper_grade=True,
        )
    )

    pml = nested(data["standard_pressure_execution"], ["simulation_quality", "pml_size"])
    pml_dry = nested(data["pml12_dry_run"], ["actual_metrics"], {})
    checks.append(
        ReadinessCheck(
            check_id="ct.pml_boundary_review",
            title="CT PML/boundary evidence is partial",
            status="block",
            category="ct_numerical_quality",
            evidence=f"pressure_run_pml={pml}; pml12_dry_run_grid={pml_dry.get('grid_size')}; no PML pressure comparison or reflection analysis",
            source=paths["pml12_dry_run"],
            recommended_next="Review whether a single PML8/PML12 pressure comparison is justified; otherwise keep as partial metadata.",
            blocks_paper_grade=True,
        )
    )

    cfl = nested(data["standard_pressure_execution"], ["simulation_quality", "cfl"])
    checks.append(
        ReadinessCheck(
            check_id="ct.cfl_review",
            title="CFL sensitivity review is missing",
            status="block",
            category="ct_numerical_quality",
            evidence=f"standard_run_cfl={cfl}; no CFL sensitivity or justification package",
            source=paths["standard_pressure_execution"],
            recommended_next="Create a read-only CFL/environment review plan before considering further pressure.",
            blocks_paper_grade=True,
        )
    )

    backend = nested(data["standard_pressure_execution"], ["simulation_quality", "backend"])
    device = nested(data["standard_pressure_execution"], ["simulation_quality", "device"])
    runtime = nested(data["standard_pressure_execution"], ["simulation_quality", "runtime_s"])
    checks.append(
        ReadinessCheck(
            check_id="environment.record",
            title="environment record is incomplete for paper-grade",
            status="block",
            category="reporting",
            evidence=f"backend={backend}; device={device}; runtime_s={runtime}; full package/environment versions not recorded",
            source=paths["standard_pressure_execution"],
            recommended_next="Record Python/k-Wave/package/environment versions and hardware context.",
            blocks_paper_grade=True,
        )
    )

    freefield_pg = nested(data["freefield_quality"], ["stage_conclusion", "paper_grade"])
    freefield_gaps = nested(data["freefield_quality"], ["remaining_gaps"], [])
    checks.append(
        ReadinessCheck(
            check_id="freefield.paper_grade_context",
            title="free-field calibration remains non-paper-grade context",
            status="block" if freefield_pg is False else "pass",
            category="freefield",
            evidence=f"paper_grade={freefield_pg}; remaining_gaps={freefield_gaps}",
            source=paths["freefield_quality"],
            recommended_next="Do not use free-field context as paper-grade transcranial evidence.",
            blocks_paper_grade=freefield_pg is not True,
        )
    )

    required_fields = nested(data["simulation_presets"], ["presets", "paper_grade", "required_summary_fields"], [])
    checks.append(
        ReadinessCheck(
            check_id="paper_grade.required_fields",
            title="paper-grade required fields are not satisfied",
            status="block",
            category="reporting",
            evidence=f"required_fields={required_fields}; missing=grid_convergence,pml_review,cfl_review,environment_record",
            source=paths["simulation_presets"],
            recommended_next="Build the paper-grade report schema only after the missing evidence exists.",
            blocks_paper_grade=True,
        )
    )

    pressure = nested(data["standard_pressure_execution"], ["pressure"], {})
    checks.append(
        ReadinessCheck(
            check_id="interpretation.engineering_only",
            title="pressure/focus interpretation remains engineering-level",
            status="warn",
            category="interpretation",
            evidence=(
                f"target_pressure_mpa={pressure.get('target_pressure_mpa')}; "
                f"effective_peak_mpa={pressure.get('effective_peak_mpa')}; "
                f"effective_peak_to_target_distance_mm={pressure.get('effective_peak_to_target_distance_mm')}"
            ),
            source=paths["standard_pressure_execution"],
            recommended_next="Use metrics to guide next evidence tasks, not as medical or paper-grade claims.",
            blocks_paper_grade=True,
        )
    )

    return checks


def build_summary(data: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    checks = build_checks(data)
    blockers = [check for check in checks if check.blocks_paper_grade and check.status != "pass"]
    previous_blockers = nested(data["previous_readiness"], ["paper_grade_blockers"], [])
    previous_ids = [item.get("check_id") for item in previous_blockers if isinstance(item, dict)]
    current_ids = [check.check_id for check in blockers]
    closed = [
        "baseline.standard_review_prepared",
        "ct.pressure_run_current_quality",
    ]
    closed = [item for item in closed if item in previous_ids and item not in current_ids]
    by_category: dict[str, list[dict[str, Any]]] = {}
    for check in blockers:
        by_category.setdefault(check.category, []).append(check.to_dict())

    pressure = nested(data["standard_pressure_execution"], ["pressure"], {})
    decision = {
        "case_id": "079",
        "baseline_profile": "simple_hu300",
        "standard_pressure_completed": nested(
            data["standard_pressure_execution"], ["decision", "standard_pressure_run_completed"], False
        ),
        "paper_grade_ready": False,
        "paper_grade_blocker_count": len(blockers),
        "closed_previous_blockers": closed,
        "new_or_remaining_blockers": current_ids,
        "recommended_next_state": "read_only_cfl_environment_gate_before_any_additional_pressure",
        "conservative_judgement": "standard_engineering_output_not_paper_grade",
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "scope": "post-pressure paper-grade readiness refresh; read-only; no k-Wave",
        "inputs": {
            "paths": source_paths(),
            "exists": {name: payload is not None for name, payload in data.items()},
        },
        "decision": decision,
        "standard_pressure_metrics": {
            "global_peak_mpa": pressure.get("global_peak_mpa"),
            "effective_peak_mpa": pressure.get("effective_peak_mpa"),
            "target_pressure_mpa": pressure.get("target_pressure_mpa"),
            "target_window_peak_mpa": pressure.get("target_window_peak_mpa"),
            "effective_peak_to_target_distance_mm": pressure.get("effective_peak_to_target_distance_mm"),
            "target_to_effective_peak_ratio": pressure.get("target_to_effective_peak_ratio"),
        },
        "checks": [check.to_dict() for check in checks],
        "paper_grade_blockers": [check.to_dict() for check in blockers],
        "blockers_by_category": by_category,
        "recommended_artifact_sequence": [
            "Create a read-only CFL/environment gate using the completed standard run metadata.",
            "Decide whether a single additional pressure comparison is justified only after that gate.",
            "Keep source-backed alpha pressure and profile promotion blocked until alpha semantics are resolved.",
            "Do not draft paper-grade claims until convergence, PML/boundary, CFL, environment, and alpha semantics are resolved.",
        ],
        "not_executed": [
            "k-Wave pressure simulation",
            "thermal simulation",
            "paper-grade preset run",
            "source-backed alpha pressure run",
            "profile promotion",
            "default mapping change",
        ],
    }


def status_label(status: str) -> str:
    return {"pass": "PASS", "warn": "WARN", "block": "BLOCK"}.get(status, status.upper())


def build_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    lines = [
        "# simple_hu300 Post-Pressure Paper-grade Readiness",
        "",
        "> Scope: read-only readiness refresh after one authorized standard pressure run. No k-Wave, thermal, paper-grade, or profile promotion was executed.",
        "",
        "## Decision",
        "",
    ]
    for key, value in decision.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Standard Pressure Metrics", ""])
    for key, value in summary["standard_pressure_metrics"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Closed Previous Blockers", ""])
    if decision["closed_previous_blockers"]:
        lines.extend(f"- `{item}`" for item in decision["closed_previous_blockers"])
    else:
        lines.append("- None")
    lines.extend(["", "## Current Checklist", ""])
    lines.append("| Status | Check | Category | Evidence | Recommended Next |")
    lines.append("|---|---|---|---|---|")
    for check in summary["checks"]:
        evidence = str(check["evidence"]).replace("\n", " ")
        recommended = str(check["recommended_next"]).replace("\n", " ")
        if len(evidence) > 180:
            evidence = evidence[:177] + "..."
        if len(recommended) > 140:
            recommended = recommended[:137] + "..."
        lines.append(
            f"| {status_label(check['status'])} | `{check['check_id']}` | {check['category']} | {evidence} | {recommended} |"
        )
    lines.extend(["", "## Recommended Artifact Sequence", ""])
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(summary["recommended_artifact_sequence"], start=1))
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in summary["not_executed"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(summary: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUT_DIR / "post_pressure_readiness_report.md"
    summary_path = OUT_DIR / "post_pressure_readiness_summary.json"
    report_path.write_text(build_markdown(summary), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    feedback = {
        "module": MODULE,
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read completed standard pressure summary",
            "read previous paper-grade readiness checklist",
            "generated post-pressure readiness report",
        ],
        "outputs": {
            "report": rel(report_path),
            "summary": rel(summary_path),
        },
        "decision": summary["decision"],
        "closed_previous_blockers": summary["decision"]["closed_previous_blockers"],
        "remaining_blockers": [item["check_id"] for item in summary["paper_grade_blockers"]],
        "not_executed": summary["not_executed"],
        "recommended_next_step": "Create a read-only CFL/environment gate before any additional pressure run.",
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    md = "\n".join(
        [
            "# Gap Feedback: simple_hu300 Post-Pressure Readiness",
            "",
            "## Actual Execution",
            "",
            "- Read completed standard pressure summary and previous readiness checklist.",
            "- Generated post-pressure paper-grade readiness report.",
            "",
            "## Decision",
            "",
            f"- standard pressure completed: `{summary['decision']['standard_pressure_completed']}`",
            f"- paper-grade ready: `{summary['decision']['paper_grade_ready']}`",
            f"- blocker count: `{summary['decision']['paper_grade_blocker_count']}`",
            f"- closed previous blockers: `{summary['decision']['closed_previous_blockers']}`",
            "",
            "## Outputs",
            "",
            f"- `{rel(report_path)}`",
            f"- `{rel(summary_path)}`",
            "",
            "## Not Executed",
            "",
            "- No k-Wave pressure simulation.",
            "- No thermal simulation.",
            "- No paper-grade preset run.",
            "- No profile/default promotion.",
            "",
        ]
    )
    (BRIEF_DIR / "gap_feedback.md").write_text(md, encoding="utf-8")


def main() -> None:
    data = load_inputs()
    summary = build_summary(data)
    write_outputs(summary)
    print(f"Wrote {rel(OUT_DIR / 'post_pressure_readiness_report.md')}")
    print(f"Wrote {rel(OUT_DIR / 'post_pressure_readiness_summary.json')}")


if __name__ == "__main__":
    main()
