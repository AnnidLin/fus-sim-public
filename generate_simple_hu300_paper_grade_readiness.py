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
    category: str
    recommended_artifact: str
    blocks_paper_grade: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "title": self.title,
            "status": self.status,
            "evidence": self.evidence,
            "source": self.source,
            "category": self.category,
            "recommended_artifact": self.recommended_artifact,
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
    return {
        "baseline_reentry": PROJECT_ROOT
        / "outputs/simple_hu300_baseline_reentry/079_candidate_006/baseline_reentry_summary.json",
        "standard_review_dry_run": PROJECT_ROOT
        / "outputs/ct_standard_review_plan/079_candidate_006/quality_dry_run/quality_dry_run_summary.json",
        "freefield_quality": PROJECT_ROOT / "outputs/freefield_quality_report/freefield_quality_summary.json",
        "hu300_model_summary": PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300/summary.json",
        "reference_summary": PROJECT_ROOT / "outputs/case_refinement_runs/079_candidate_006_offset_10_0/summary.json",
        "reference_focus_metrics": PROJECT_ROOT
        / "outputs/case_refinement_runs/079_candidate_006_offset_10_0/focus_metrics.json",
        "simulation_presets": PROJECT_ROOT / "simulation_presets.json",
    }


def load_inputs() -> dict[str, dict[str, Any] | None]:
    return {name: read_json(path) for name, path in input_paths().items()}


def source_paths() -> dict[str, str]:
    return {name: rel(path) for name, path in input_paths().items()}


def build_checks(data: dict[str, dict[str, Any] | None]) -> list[Check]:
    paths = source_paths()
    checks: list[Check] = []

    for name, payload in data.items():
        ok = payload is not None
        checks.append(
            Check(
                check_id=f"input.{name}",
                title=f"Required input exists: {name}",
                status="pass" if ok else "block",
                evidence="JSON parsed" if ok else "Missing or unreadable JSON",
                source=paths[name],
                category="inputs",
                recommended_artifact="Restore or regenerate the missing input before paper-grade evaluation.",
                blocks_paper_grade=not ok,
            )
        )

    baseline_profile = nested(data["baseline_reentry"], ["decision", "baseline_profile"])
    standard_prepared = nested(data["baseline_reentry"], ["decision", "standard_review_prepared"])
    execution_authorized = nested(data["baseline_reentry"], ["decision", "execution_authorized"])
    checks.append(
        Check(
            check_id="baseline.standard_review_prepared",
            title="standard-review package is prepared but not executed",
            status="warn" if standard_prepared is True and execution_authorized is False else "block",
            evidence=(
                f"baseline_profile={baseline_profile}; standard_review_prepared={standard_prepared}; "
                f"execution_authorized={execution_authorized}"
            ),
            source=paths["baseline_reentry"],
            category="standard_review",
            recommended_artifact="If authorized, execute one standard-review runner and write a standard-run summary with simulation_quality metadata.",
            blocks_paper_grade=True,
        )
    )

    preset = nested(data["standard_review_dry_run"], ["simulation_quality", "preset"])
    is_paper_grade = nested(data["standard_review_dry_run"], ["simulation_quality", "is_paper_grade"])
    paper_blockers = nested(data["standard_review_dry_run"], ["simulation_quality", "paper_grade_blockers"], [])
    checks.append(
        Check(
            check_id="preset.paper_grade",
            title="paper-grade preset is not active",
            status="block" if is_paper_grade is False else "pass",
            evidence=f"preset={preset}; is_paper_grade={is_paper_grade}; paper_grade_blockers={paper_blockers}",
            source=paths["standard_review_dry_run"],
            category="preset",
            recommended_artifact="Create a separate paper-grade plan/dry-run package only after standard-review execution is reviewed.",
            blocks_paper_grade=is_paper_grade is not True,
        )
    )

    pressure_output = nested(
        data["standard_review_dry_run"], ["simulation_quality", "output_completeness", "pressure_max_mpa"], False
    )
    dry_run_only = nested(data["standard_review_dry_run"], ["dry_run_quality_only"])
    checks.append(
        Check(
            check_id="ct.pressure_run_current_quality",
            title="current-quality CT pressure run is missing",
            status="block" if dry_run_only is True and not pressure_output else "pass",
            evidence=f"dry_run_quality_only={dry_run_only}; pressure_output={pressure_output}",
            source=paths["standard_review_dry_run"],
            category="ct_pressure",
            recommended_artifact="Execute and review the prepared standard-run before planning any paper-grade run.",
            blocks_paper_grade=True,
        )
    )

    reference_runtime = nested(data["reference_summary"], ["runtime", "runtime_s"])
    reference_has_quality = nested(data["baseline_reentry"], ["reference_run", "interpretation"], "")
    checks.append(
        Check(
            check_id="ct.reference_run_metadata",
            title="historical CT reference lacks current simulation-quality metadata",
            status="warn",
            evidence=f"historical_runtime_s={reference_runtime}; interpretation={reference_has_quality}",
            source=paths["reference_summary"],
            category="ct_pressure",
            recommended_artifact="Use historical run only as context; do not use it as paper-grade evidence.",
            blocks_paper_grade=True,
        )
    )

    freefield_paper_grade = nested(data["freefield_quality"], ["stage_conclusion", "paper_grade"])
    freefield_gaps = nested(data["freefield_quality"], ["remaining_gaps"], [])
    checks.append(
        Check(
            check_id="freefield.paper_grade",
            title="free-field calibration is not paper-grade",
            status="block" if freefield_paper_grade is False else "pass",
            evidence=f"paper_grade={freefield_paper_grade}; remaining_gaps={freefield_gaps}",
            source=paths["freefield_quality"],
            category="freefield",
            recommended_artifact="Complete free-field grid convergence and boundary-reflection evidence before stronger claims.",
            blocks_paper_grade=freefield_paper_grade is not True,
        )
    )

    grid_comparison = nested(data["freefield_quality"], ["grid_convergence_comparison", "changes"], {})
    checks.append(
        Check(
            check_id="ct.grid_convergence",
            title="CT-specific grid convergence is missing",
            status="block",
            evidence=f"freefield_grid_context={grid_comparison}; ct_grid_convergence=None",
            source=paths["freefield_quality"],
            category="ct_numerical_quality",
            recommended_artifact="Prepare a CT grid convergence plan before any paper-grade candidate run; free-field convergence does not substitute for CT convergence.",
            blocks_paper_grade=True,
        )
    )

    pml_comparison = nested(data["freefield_quality"], ["pml_boundary_comparison", "changes"], {})
    checks.append(
        Check(
            check_id="ct.pml_boundary_review",
            title="CT-specific PML/boundary review is missing",
            status="block",
            evidence=f"freefield_pml_context={pml_comparison}; ct_pml_review=None",
            source=paths["freefield_quality"],
            category="ct_numerical_quality",
            recommended_artifact="Prepare CT PML/boundary review after standard-run output exists.",
            blocks_paper_grade=True,
        )
    )

    paper_requirements = nested(
        data["simulation_presets"], ["presets", "paper_grade", "quality_requirements"], {}
    )
    required_fields = nested(data["simulation_presets"], ["presets", "paper_grade", "required_summary_fields"], [])
    checks.append(
        Check(
            check_id="paper_grade.required_fields",
            title="paper-grade required summary fields are not yet satisfied by CT outputs",
            status="block",
            evidence=f"required_fields={required_fields}; quality_requirements={paper_requirements}",
            source=paths["simulation_presets"],
            category="reporting",
            recommended_artifact="Create a paper-grade report schema after standard-run, grid convergence, PML review, and environment records exist.",
            blocks_paper_grade=True,
        )
    )

    target_window_peak = nested(data["reference_focus_metrics"], ["target_window_peak_mpa"])
    effective_peak_distance = nested(data["reference_focus_metrics"], ["effective_peak_to_target_distance_mm"])
    checks.append(
        Check(
            check_id="interpretation.target_quality",
            title="target/focus interpretation is still engineering-level",
            status="warn",
            evidence=f"historical_target_window_peak_mpa={target_window_peak}; effective_peak_to_target_distance_mm={effective_peak_distance}",
            source=paths["reference_focus_metrics"],
            category="interpretation",
            recommended_artifact="After standard-run, decide whether target/focus metrics justify continued tuning or paper-grade planning.",
            blocks_paper_grade=True,
        )
    )

    return checks


def build_summary(data: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    checks = build_checks(data)
    blockers = [check for check in checks if check.blocks_paper_grade and check.status != "pass"]
    by_category: dict[str, list[dict[str, Any]]] = {}
    for check in blockers:
        by_category.setdefault(check.category, []).append(check.to_dict())

    standard_prepared = nested(data["baseline_reentry"], ["decision", "standard_review_prepared"], False)
    execution_authorized = nested(data["baseline_reentry"], ["decision", "execution_authorized"], False)
    decision = {
        "case_id": "079",
        "baseline_profile": "simple_hu300",
        "standard_review_prepared": bool(standard_prepared),
        "execution_authorized": bool(execution_authorized),
        "paper_grade_ready": False,
        "paper_grade_blocker_count": len(blockers),
        "recommended_next_state": "run_single_standard_review_only_if_user_authorizes"
        if standard_prepared and not execution_authorized
        else "resolve_standard_readiness_first",
        "conservative_judgement": "not_paper_grade",
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "simple_hu300 paper-grade readiness only; read-only; no k-Wave; no CT rebuild",
        "inputs": {
            "paths": source_paths(),
            "exists": {name: payload is not None for name, payload in data.items()},
        },
        "decision": decision,
        "checks": [check.to_dict() for check in checks],
        "paper_grade_blockers": [check.to_dict() for check in blockers],
        "blockers_by_category": by_category,
        "recommended_artifact_sequence": [
            "Execute exactly one authorized simple_hu300 standard-review runner, if the user explicitly authorizes it.",
            "Write standard-run gap_feedback and compare against the historical reference run.",
            "Prepare CT grid-convergence plan and dry-run estimates; do not batch-run convergence cases.",
            "Prepare CT PML/boundary review plan after standard-run metrics exist.",
            "Only then draft a paper-grade preset plan with environment records and reporting schema.",
        ],
        "not_executed": [
            "k-Wave pressure simulation",
            "CT acoustic model rebuild",
            "thermal simulation",
            "paper-grade preset run",
            "source-backed alpha profile promotion",
        ],
    }


def status_label(status: str) -> str:
    return {"pass": "PASS", "warn": "WARN", "block": "BLOCK"}.get(status, status.upper())


def build_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    lines = [
        "# simple_hu300 Paper-grade Readiness Checklist",
        "",
        "> Scope: read-only gap checklist. No k-Wave, CT rebuild, thermal run, paper-grade run, or profile promotion was executed.",
        "",
        "## Decision",
        "",
        f"- case: `{decision['case_id']}`",
        f"- baseline profile: `{decision['baseline_profile']}`",
        f"- standard-review prepared: `{decision['standard_review_prepared']}`",
        f"- execution authorized: `{decision['execution_authorized']}`",
        f"- paper-grade ready: `{decision['paper_grade_ready']}`",
        f"- blocker count: `{decision['paper_grade_blocker_count']}`",
        f"- next state: `{decision['recommended_next_state']}`",
        f"- conservative judgement: `{decision['conservative_judgement']}`",
        "",
        "## Checklist",
        "",
        "| Status | Check | Category | Evidence | Recommended Artifact |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in summary["checks"]:
        evidence = str(check["evidence"]).replace("\n", " ")
        artifact = str(check["recommended_artifact"]).replace("\n", " ")
        if len(evidence) > 190:
            evidence = evidence[:187] + "..."
        if len(artifact) > 150:
            artifact = artifact[:147] + "..."
        lines.append(
            f"| {status_label(check['status'])} | `{check['check_id']}` | {check['category']} | {evidence} | {artifact} |"
        )

    lines.extend(["", "## Recommended Artifact Sequence", ""])
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(summary["recommended_artifact_sequence"], start=1))
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in summary["not_executed"])
    lines.append("")
    return "\n".join(lines)


def write_gap_feedback(output_dir: Path, summary: dict[str, Any]) -> None:
    brief_dir = PROJECT_ROOT / "outputs/evidence_briefs/simple_hu300_paper_grade_readiness"
    brief_dir.mkdir(parents=True, exist_ok=True)
    feedback = {
        "module": "simple_hu300_paper_grade_readiness",
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read simple_hu300 baseline re-entry summary",
            "read CT standard-review dry-run summary",
            "read free-field quality summary",
            "generated paper-grade readiness checklist",
        ],
        "outputs": {
            "report": rel(output_dir / "paper_grade_readiness_report.md"),
            "summary": rel(output_dir / "paper_grade_readiness_summary.json"),
        },
        "decision": summary["decision"],
        "not_executed": summary["not_executed"],
        "remaining_gaps": [
            check["check_id"] for check in summary["paper_grade_blockers"]
        ],
        "recommended_next_step": "Only run the prepared simple_hu300 standard-review runner if the user explicitly authorizes it; otherwise continue with read-only CT convergence/PML planning.",
    }
    (brief_dir / "gap_feedback.json").write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = "\n".join(
        [
            "# Gap Feedback：simple_hu300 paper-grade readiness",
            "",
            "## Actual Execution",
            "",
            "- Read existing baseline re-entry, standard-review dry-run, free-field quality, and reference-run summaries.",
            "- Generated paper-grade readiness checklist.",
            "",
            "## Outputs",
            "",
            f"- `{rel(output_dir / 'paper_grade_readiness_report.md')}`",
            f"- `{rel(output_dir / 'paper_grade_readiness_summary.json')}`",
            "",
            "## Decision",
            "",
            f"- paper-grade ready: `{summary['decision']['paper_grade_ready']}`",
            f"- blocker count: `{summary['decision']['paper_grade_blocker_count']}`",
            f"- next state: `{summary['decision']['recommended_next_state']}`",
            "",
            "## Not Executed",
            "",
            "- No k-Wave pressure simulation.",
            "- No CT model rebuild.",
            "- No thermal simulation.",
            "- No paper-grade preset run.",
            "",
        ]
    )
    (brief_dir / "gap_feedback.md").write_text(md, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate simple_hu300 paper-grade readiness checklist.")
    parser.add_argument("--output-dir", default="outputs/simple_hu300_paper_grade_readiness/079_candidate_006")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_inputs()
    summary = build_summary(data)
    (output_dir / "paper_grade_readiness_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "paper_grade_readiness_report.md").write_text(build_markdown(summary), encoding="utf-8-sig")
    write_gap_feedback(output_dir, summary)
    print(f"Wrote {output_dir / 'paper_grade_readiness_report.md'}")
    print(f"Wrote {output_dir / 'paper_grade_readiness_summary.json'}")


if __name__ == "__main__":
    main()
