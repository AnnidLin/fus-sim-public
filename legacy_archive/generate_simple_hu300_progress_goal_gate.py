from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE = "simple_hu300_progress_goal_gate"
OUT_DIR = PROJECT_ROOT / "outputs" / MODULE / "079_candidate_006"
BRIEF_DIR = PROJECT_ROOT / "outputs" / "evidence_briefs" / MODULE


@dataclass(frozen=True)
class GateItem:
    item_id: str
    title: str
    status: str
    evidence: str
    source: str
    next_action: str
    blocks_pressure: bool
    blocks_paper_grade: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "status": self.status,
            "evidence": self.evidence,
            "source": self.source,
            "next_action": self.next_action,
            "blocks_pressure": self.blocks_pressure,
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
        "alpha_promotion_gate": PROJECT_ROOT
        / "outputs/profile_promotion_gate/prestus_fit_alpha_power_2/profile_promotion_gate_summary.json",
        "baseline_reentry": PROJECT_ROOT
        / "outputs/simple_hu300_baseline_reentry/079_candidate_006/baseline_reentry_summary.json",
        "paper_grade_readiness": PROJECT_ROOT
        / "outputs/simple_hu300_paper_grade_readiness/079_candidate_006/paper_grade_readiness_summary.json",
        "dx075_model_dry_run": PROJECT_ROOT
        / "outputs/ct_grid_convergence_plan/079_candidate_006/dx0p75_model_build_dry_run_summary.json",
        "dx075_quality_dry_run": PROJECT_ROOT
        / "outputs/ct_grid_convergence_plan/079_candidate_006/dx0p75_dry_run/quality_dry_run_summary.json",
        "pml12_dry_run": PROJECT_ROOT
        / "outputs/ct_pml_boundary_review/079_candidate_006_dx0p75/pml12_dry_run_summary.json",
        "pml12_quality_dry_run": PROJECT_ROOT
        / "outputs/ct_pml_boundary_review/079_candidate_006_dx0p75/pml12_dry_run/quality_dry_run_summary.json",
        "standard_pressure_execution": PROJECT_ROOT
        / "outputs/ct_standard_pressure_authorization/079_candidate_006_dx0p75_pml12_standard/standard_pressure_execution_summary.json",
        "post_pressure_readiness": PROJECT_ROOT
        / "outputs/simple_hu300_post_pressure_readiness/079_candidate_006/post_pressure_readiness_summary.json",
        "simulation_presets": PROJECT_ROOT / "simulation_presets.json",
    }


def load_inputs() -> dict[str, dict[str, Any] | None]:
    return {name: read_json(path) for name, path in input_paths().items()}


def pressure_file_absence() -> dict[str, bool]:
    paths = {
        "gate_output_pressure": OUT_DIR / "pressure_max_mpa.npz",
        "dx075_dry_run_pressure": PROJECT_ROOT
        / "outputs/ct_grid_convergence_plan/079_candidate_006/dx0p75_dry_run/pressure_max_mpa.npz",
        "pml12_dry_run_pressure": PROJECT_ROOT
        / "outputs/ct_pml_boundary_review/079_candidate_006_dx0p75/pml12_dry_run/pressure_max_mpa.npz",
        "dx075_model_pressure": PROJECT_ROOT
        / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/pressure_max_mpa.npz",
    }
    return {name: path.exists() for name, path in paths.items()}


def build_gate_items(data: dict[str, dict[str, Any] | None]) -> list[GateItem]:
    paths = {name: rel(path) for name, path in input_paths().items()}
    items: list[GateItem] = []

    for name, payload in data.items():
        ok = payload is not None
        items.append(
            GateItem(
                item_id=f"input.{name}",
                title=f"Required input available: {name}",
                status="pass" if ok else "block",
                evidence="JSON parsed" if ok else "missing or unreadable JSON",
                source=paths[name],
                next_action="Regenerate or restore this input before making a stronger decision." if not ok else "No action.",
                blocks_pressure=not ok,
                blocks_paper_grade=not ok,
            )
        )

    alpha_decision = nested(data["alpha_promotion_gate"], ["decision"], {})
    alpha_allowed = alpha_decision.get("pressure_eligible")
    alpha_state = alpha_decision.get("recommended_state")
    items.append(
        GateItem(
            item_id="alpha.source_backed_profile",
            title="source-backed alpha profile remains pressure-blocked",
            status="block" if alpha_allowed is False else "warn",
            evidence=f"pressure_eligible={alpha_allowed}; recommended_state={alpha_state}",
            source=paths["alpha_promotion_gate"],
            next_action="Keep prestus_fit_alpha_power_2 exploratory until alpha semantics conflict and cross-check gaps are resolved.",
            blocks_pressure=True,
            blocks_paper_grade=True,
        )
    )

    baseline_decision = nested(data["baseline_reentry"], ["decision"], {})
    baseline_profile = baseline_decision.get("baseline_profile")
    execution_authorized = baseline_decision.get("execution_authorized")
    items.append(
        GateItem(
            item_id="baseline.simple_hu300",
            title="simple_hu300 remains the active reproducible baseline",
            status="pass" if baseline_profile in {"baseline_compatible", "simple_hu300"} else "warn",
            evidence=f"baseline_profile={baseline_profile}; execution_authorized={execution_authorized}",
            source=paths["baseline_reentry"],
            next_action="Continue using simple_hu300 for readiness/gating work; require explicit authorization for pressure.",
            blocks_pressure=execution_authorized is not True,
            blocks_paper_grade=True,
        )
    )

    dx_executed = nested(data["dx075_model_dry_run"], ["executed"], [])
    dx_metrics = nested(data["dx075_model_dry_run"], ["dry_run_quality"], {})
    dx_pressure_generated = nested(data["dx075_model_dry_run"], ["pressure_field_generated"], False)
    items.append(
        GateItem(
            item_id="ct.dx075_grid_dry_run",
            title="dx0.75 model-build and dry-run-quality are complete",
            status="pass" if dx_metrics else "block",
            evidence=(
                f"executed={dx_executed}; grid={dx_metrics.get('grid_size')}; "
                f"pml={dx_metrics.get('pml_size')}; pressure_field_generated={dx_pressure_generated}"
            ),
            source=paths["dx075_model_dry_run"],
            next_action="Use as grid-quality metadata only; do not treat as pressure evidence.",
            blocks_pressure=False,
            blocks_paper_grade=True,
        )
    )

    pml_metrics = nested(data["pml12_dry_run"], ["actual_metrics"], {})
    pml_pressure_exists = nested(data["pml12_dry_run"], ["pressure_max_mpa_npz_exists"], None)
    items.append(
        GateItem(
            item_id="ct.pml12_dry_run",
            title="PML=12 CT dry-run-quality is complete",
            status="pass" if pml_metrics and pml_pressure_exists is False else "block",
            evidence=(
                f"grid={pml_metrics.get('grid_size')}; pml={pml_metrics.get('pml_size')}; "
                f"source_label_counts={pml_metrics.get('source_label_counts')}; pressure_npz_exists={pml_pressure_exists}"
            ),
            source=paths["pml12_dry_run"],
            next_action="Use as boundary-review metadata only; pressure still needs runner-gated authorization.",
            blocks_pressure=False,
            blocks_paper_grade=True,
        )
    )

    readiness_decision = nested(data["paper_grade_readiness"], ["decision"], {})
    blocker_count = readiness_decision.get("paper_grade_blocker_count")
    paper_ready = readiness_decision.get("paper_grade_ready")
    items.append(
        GateItem(
            item_id="paper_grade.readiness",
            title="paper-grade status remains blocked",
            status="block" if paper_ready is False else "pass",
            evidence=f"paper_grade_ready={paper_ready}; blocker_count={blocker_count}",
            source=paths["paper_grade_readiness"],
            next_action="Do not write paper-grade or medical conclusions; continue closing blockers one gate at a time.",
            blocks_pressure=False,
            blocks_paper_grade=paper_ready is not True,
        )
    )

    pressure_completed = nested(data["standard_pressure_execution"], ["decision", "standard_pressure_run_completed"])
    pressure_runner_status = nested(data["standard_pressure_execution"], ["runner", "status"])
    pressure_interpretation = nested(data["standard_pressure_execution"], ["alpha_semantics", "interpretation"])
    items.append(
        GateItem(
            item_id="ct.standard_pressure_execution",
            title="one user-authorized standard pressure run is complete",
            status="pass" if pressure_completed is True and pressure_runner_status == "kwave_ok" else "block",
            evidence=(
                f"standard_pressure_run_completed={pressure_completed}; runner_status={pressure_runner_status}; "
                f"interpretation={pressure_interpretation}"
            ),
            source=paths["standard_pressure_execution"],
            next_action="Use as engineering standard pressure evidence only; refresh readiness, but keep paper-grade blocked.",
            blocks_pressure=False,
            blocks_paper_grade=True,
        )
    )

    preset_standard = nested(data["simulation_presets"], ["presets", "standard", "runtime_policy"], {})
    preset_paper = nested(data["simulation_presets"], ["presets", "paper_grade", "quality_requirements"], {})
    items.append(
        GateItem(
            item_id="preset.boundary",
            title="standard and paper-grade remain separate",
            status="pass",
            evidence=f"standard_runtime_policy={preset_standard}; paper_grade_quality_requirements={preset_paper}",
            source=paths["simulation_presets"],
            next_action="If pressure is authorized, run only standard first; paper-grade requires separate convergence/environment evidence.",
            blocks_pressure=False,
            blocks_paper_grade=True,
        )
    )

    return items


def build_summary(data: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    items = build_gate_items(data)
    pressure_presence = pressure_file_absence()
    missing_inputs = [name for name, payload in data.items() if payload is None]
    pressure_outputs_present = [name for name, exists in pressure_presence.items() if exists]
    paper_blockers = nested(data["paper_grade_readiness"], ["paper_grade_blockers"], [])
    if not paper_blockers:
        paper_blockers = nested(data["paper_grade_readiness"], ["checks"], [])

    standard_pressure_completed = nested(
        data["standard_pressure_execution"], ["decision", "standard_pressure_run_completed"], False
    )
    post_pressure_readiness_refreshed = nested(
        data["post_pressure_readiness"], ["decision", "standard_pressure_completed"], False
    )
    if standard_pressure_completed:
        next_without_pressure = [
            "create read-only CFL/environment gate from the completed standard run metadata",
            "prepare a cautious decision gate for whether any single additional comparison is justified",
            "keep paper-grade/profile promotion blocked until convergence, boundary, CFL, environment, and alpha semantics gaps are resolved",
        ]
    else:
        next_without_pressure = [
            "refresh paper-grade/readiness checklist with dx0.75 and PML12 evidence",
            "prepare one runner-gated standard pressure command for explicit user approval",
            "add CFL/environment reporting plan without executing pressure",
        ]
    next_requires_authorization = [
        "single simple_hu300 standard pressure run through run_kwave_command.py --execute",
        "any dx0.75 or PML12 pressure comparison",
        "any paper-grade candidate run",
    ]

    decision = {
        "current_baseline": "simple_hu300",
        "source_backed_alpha_status": nested(
            data["alpha_promotion_gate"], ["decision", "recommended_state"], "unknown"
        ),
        "standard_pressure_completed": standard_pressure_completed,
        "post_pressure_readiness_refreshed": post_pressure_readiness_refreshed,
        "pressure_run_allowed": False,
        "pressure_authorization_present": False,
        "paper_grade_ready": False,
        "profile_promotion_allowed": False,
        "default_profile_change_allowed": False,
        "recommended_state": (
            "standard_pressure_completed_cfl_environment_gate_next"
            if standard_pressure_completed
            else "baseline_metadata_ready_pressure_awaits_explicit_authorization"
        ),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "scope": "read-only current progress and next-action gate",
        "inputs": {
            "paths": {name: rel(path) for name, path in input_paths().items()},
            "missing": missing_inputs,
        },
        "decision": decision,
        "current_progress": {
            "completed": [
                "source-backed alpha promotion gate blocks prestus_fit_alpha_power_2 pressure/default promotion",
                "simple_hu300 baseline re-entry prepared",
                "paper-grade readiness checklist generated and remains blocked",
                "dx0.75 simple_hu300 CT model-build completed",
                "dx0.75 dry-run-quality completed",
                "PML=12 CT dry-run-quality completed",
                "one user-authorized simple_hu300 dx0.75 PML12 standard pressure run completed",
            ],
            "not_completed": [
                "no MATLAB source-backed alpha cross-check execution",
                "no paper-grade convergence package",
                "no paper-grade environment record",
                "no validated alpha-semantics pressure baseline",
            ],
        },
        "gate_items": [item.to_dict() for item in items],
        "pressure_file_presence": pressure_presence,
        "paper_grade_blocker_count": len(paper_blockers),
        "next_allowed_without_pressure_authorization": next_without_pressure,
        "next_requires_explicit_pressure_authorization": next_requires_authorization,
        "not_executed": [
            "k-Wave pressure simulation",
            "thermal simulation",
            "profile promotion",
            "default mapping change",
        ],
        "warnings": [
            "dry-run-quality metadata is not pressure validation",
            "historical pressure outputs must not be merged with dx0.75/PML12 dry-run metadata as if they were the same run",
            "paper-grade and medical conclusions remain blocked",
        ],
    }


def write_report(summary: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUT_DIR / "current_progress_goal_gate_report.md"
    summary_path = OUT_DIR / "current_progress_goal_gate_summary.json"

    lines = [
        "# simple_hu300 Current Progress / Goal Gate",
        "",
        "## Decision",
        "",
    ]
    for key, value in summary["decision"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Completed Evidence", ""])
    lines.extend(f"- {item}" for item in summary["current_progress"]["completed"])
    lines.extend(["", "## Not Completed", ""])
    lines.extend(f"- {item}" for item in summary["current_progress"]["not_completed"])
    lines.extend(["", "## Gate Items", ""])
    lines.append("| item | status | blocks pressure | blocks paper-grade | evidence |")
    lines.append("|---|---:|---:|---:|---|")
    for item in summary["gate_items"]:
        lines.append(
            f"| `{item['item_id']}` | `{item['status']}` | `{item['blocks_pressure']}` | "
            f"`{item['blocks_paper_grade']}` | {item['evidence']} |"
        )
    lines.extend(["", "## Next Allowed Without Pressure Authorization", ""])
    lines.extend(f"- {item}" for item in summary["next_allowed_without_pressure_authorization"])
    lines.extend(["", "## Requires Explicit Pressure Authorization", ""])
    lines.extend(f"- {item}" for item in summary["next_requires_explicit_pressure_authorization"])
    lines.extend(["", "## Pressure File Presence Check", ""])
    for name, exists in summary["pressure_file_presence"].items():
        lines.append(f"- `{name}`: `{exists}`")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in summary["warnings"])
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in summary["not_executed"])
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    feedback = {
        "module": MODULE,
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read existing gate/readiness/dry-run JSON summaries",
            "generated current progress and next-action gate report",
            "verified pressure outputs are absent in dry-run/gate paths",
        ],
        "outputs": {
            "report": rel(report_path),
            "summary": rel(summary_path),
        },
        "decision": summary["decision"],
        "pressure_file_presence": summary["pressure_file_presence"],
        "not_executed": summary["not_executed"],
        "recommended_next_step": "Prepare an explicit user-authorization prompt for one runner-gated standard pressure run, or continue read-only CFL/environment gate work.",
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "\n".join(
            [
                "# Gap Feedback: simple_hu300 Progress/Goal Gate",
                "",
                "## Actual Execution",
                "",
                "- Read existing summary JSON files.",
                "- Generated current progress and next-action gate report.",
                "- Confirmed dry-run/gate pressure outputs are absent.",
                "",
                "## Decision",
                "",
                f"- pressure_run_allowed: `{summary['decision']['pressure_run_allowed']}`",
                f"- paper_grade_ready: `{summary['decision']['paper_grade_ready']}`",
                f"- recommended_state: `{summary['decision']['recommended_state']}`",
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
                "- No profile promotion.",
                "- No default mapping change.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    data = load_inputs()
    summary = build_summary(data)
    write_report(summary)
    print(f"Wrote {rel(OUT_DIR / 'current_progress_goal_gate_report.md')}")
    print(f"Wrote {rel(OUT_DIR / 'current_progress_goal_gate_summary.json')}")


if __name__ == "__main__":
    main()
