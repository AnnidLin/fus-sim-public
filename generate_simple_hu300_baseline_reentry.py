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
    blocks_standard_review: bool = False
    blocks_paper_grade: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "title": self.title,
            "status": self.status,
            "evidence": self.evidence,
            "source": self.source,
            "blocks_standard_review": self.blocks_standard_review,
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
        "promotion_gate": PROJECT_ROOT
        / "outputs/profile_promotion_gate/prestus_fit_alpha_power_2/profile_promotion_gate_summary.json",
        "hu300_model_summary": PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300/summary.json",
        "standard_review_plan": PROJECT_ROOT / "outputs/ct_standard_review_plan/079_candidate_006/ct_standard_review_plan.json",
        "standard_review_dry_run": PROJECT_ROOT
        / "outputs/ct_standard_review_plan/079_candidate_006/quality_dry_run/quality_dry_run_summary.json",
        "reference_summary": PROJECT_ROOT / "outputs/case_refinement_runs/079_candidate_006_offset_10_0/summary.json",
        "reference_focus_metrics": PROJECT_ROOT
        / "outputs/case_refinement_runs/079_candidate_006_offset_10_0/focus_metrics.json",
        "freefield_quality": PROJECT_ROOT / "outputs/freefield_quality_report/freefield_quality_summary.json",
    }


def load_inputs() -> dict[str, dict[str, Any] | None]:
    return {name: read_json(path) for name, path in input_paths().items()}


def source_counts_background_only(counts: Any) -> bool:
    if not isinstance(counts, dict) or not counts:
        return False
    normalized = {str(key): value for key, value in counts.items()}
    return set(normalized) == {"0"} and int(normalized["0"]) > 0


def build_checks(data: dict[str, dict[str, Any] | None]) -> list[Check]:
    paths = {name: rel(path) for name, path in input_paths().items()}
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
                blocks_standard_review=not ok,
                blocks_paper_grade=not ok,
            )
        )

    promotion_allowed = nested(data["promotion_gate"], ["decision", "promotion_allowed"])
    recommended_state = nested(data["promotion_gate"], ["decision", "recommended_state"])
    source_alpha_frozen = promotion_allowed is False and recommended_state == "remain_exploratory_pressure_blocked"
    checks.append(
        Check(
            check_id="source_backed_alpha.frozen",
            title="Source-backed alpha route remains frozen",
            status="pass" if source_alpha_frozen else "block",
            evidence=f"promotion_allowed={promotion_allowed}; recommended_state={recommended_state}",
            source=paths["promotion_gate"],
            blocks_standard_review=not source_alpha_frozen,
            blocks_paper_grade=True,
        )
    )

    profile_id = nested(data["hu300_model_summary"], ["mapping_profile", "profile_id"])
    review_status = nested(data["hu300_model_summary"], ["mapping_profile", "review_status"])
    hu300_ok = profile_id == "simple_hu300" and review_status == "baseline_compatible"
    checks.append(
        Check(
            check_id="baseline.profile",
            title="simple_hu300 model summary is baseline-compatible",
            status="pass" if hu300_ok else "block",
            evidence=f"profile_id={profile_id}; review_status={review_status}",
            source=paths["hu300_model_summary"],
            blocks_standard_review=not hu300_ok,
            blocks_paper_grade=not hu300_ok,
        )
    )

    dry_run_only = nested(data["standard_review_dry_run"], ["dry_run_quality_only"])
    dry_run_pressure_output = nested(
        data["standard_review_dry_run"], ["simulation_quality", "output_completeness", "pressure_max_mpa"], False
    )
    dry_run_ok = dry_run_only is True and not bool(dry_run_pressure_output)
    checks.append(
        Check(
            check_id="standard_review.dry_run_only",
            title="standard-review dry-run exists and did not create pressure output",
            status="pass" if dry_run_ok else "block",
            evidence=f"dry_run_quality_only={dry_run_only}; pressure_output={dry_run_pressure_output}",
            source=paths["standard_review_dry_run"],
            blocks_standard_review=not dry_run_ok,
            blocks_paper_grade=not dry_run_ok,
        )
    )

    preset = nested(data["standard_review_dry_run"], ["simulation_quality", "preset"])
    ppw = nested(data["standard_review_dry_run"], ["simulation_quality", "ppw_min_sound_speed"])
    pml = nested(data["standard_review_dry_run"], ["simulation_quality", "pml_size"])
    cfl = nested(data["standard_review_dry_run"], ["simulation_quality", "cfl"])
    quality_ok = preset == "standard" and isinstance(ppw, (int, float)) and ppw >= 2.9 and pml is not None and cfl is not None
    checks.append(
        Check(
            check_id="standard_review.quality_metadata",
            title="standard-review dry-run has required quality metadata",
            status="pass" if quality_ok else "block",
            evidence=f"preset={preset}; ppw_min={ppw}; pml={pml}; cfl={cfl}",
            source=paths["standard_review_dry_run"],
            blocks_standard_review=not quality_ok,
            blocks_paper_grade=True,
        )
    )

    source_counts = nested(data["standard_review_dry_run"], ["source", "source_label_counts"])
    source_ok = source_counts_background_only(source_counts)
    checks.append(
        Check(
            check_id="standard_review.source_mask",
            title="dry-run source mask is background-only",
            status="pass" if source_ok else "block",
            evidence=f"source_label_counts={source_counts}",
            source=paths["standard_review_dry_run"],
            blocks_standard_review=not source_ok,
            blocks_paper_grade=not source_ok,
        )
    )

    runner_command = nested(data["standard_review_plan"], ["recommended_runner_command"], [])
    has_execute = isinstance(runner_command, list) and "--execute" in runner_command
    has_runner = isinstance(runner_command, list) and "run_kwave_command.py" in runner_command
    checks.append(
        Check(
            check_id="standard_review.runner_command",
            title="future run is expressed through run_kwave_command.py",
            status="pass" if has_runner and has_execute else "block",
            evidence=f"has_runner={has_runner}; has_execute_flag={has_execute}",
            source=paths["standard_review_plan"],
            blocks_standard_review=not (has_runner and has_execute),
            blocks_paper_grade=False,
        )
    )

    is_paper_grade = nested(data["standard_review_dry_run"], ["simulation_quality", "is_paper_grade"])
    paper_blockers = nested(data["standard_review_dry_run"], ["simulation_quality", "paper_grade_blockers"], [])
    checks.append(
        Check(
            check_id="paper_grade.explicit_blockers",
            title="paper-grade status remains blocked",
            status="warn" if is_paper_grade is False else "block",
            evidence=f"is_paper_grade={is_paper_grade}; paper_grade_blockers={paper_blockers}",
            source=paths["standard_review_dry_run"],
            blocks_standard_review=False,
            blocks_paper_grade=True,
        )
    )

    return checks


def build_summary(data: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    checks = build_checks(data)
    standard_blockers = [check for check in checks if check.blocks_standard_review and check.status != "pass"]
    paper_blockers = [check for check in checks if check.blocks_paper_grade and check.status != "pass"]
    reference_focus = data["reference_focus_metrics"] or {}
    plan = data["standard_review_plan"] or {}
    dry = data["standard_review_dry_run"] or {}

    standard_review_prepared = len(standard_blockers) == 0
    decision = {
        "case_id": "079",
        "baseline_profile": "simple_hu300",
        "source_backed_alpha_state": nested(data["promotion_gate"], ["decision", "recommended_state"]),
        "standard_review_prepared": standard_review_prepared,
        "execution_authorized": False,
        "runner_ready_but_not_executed": standard_review_prepared,
        "paper_grade_ready": False,
        "recommended_next_state": "await_user_authorization_for_single_standard_runner"
        if standard_review_prepared
        else "resolve_readiness_blockers_before_runner",
        "reason": "Prepared standard-review package exists, but execution still requires explicit authorization and paper-grade blockers remain.",
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "simple_hu300 baseline re-entry readiness only; no k-Wave; no CT rebuild",
        "inputs": {
            "paths": {name: rel(path) for name, path in input_paths().items()},
            "exists": {name: payload is not None for name, payload in data.items()},
        },
        "decision": decision,
        "checks": [check.to_dict() for check in checks],
        "blockers": {
            "standard_review": [check.to_dict() for check in standard_blockers],
            "paper_grade": [check.to_dict() for check in paper_blockers],
        },
        "reference_run": {
            "summary_path": rel(input_paths()["reference_summary"]),
            "focus_metrics_path": rel(input_paths()["reference_focus_metrics"]),
            "target_window_peak_mpa": reference_focus.get("target_window_peak_mpa"),
            "effective_peak_mpa": reference_focus.get("effective_peak_mpa"),
            "effective_peak_to_target_distance_mm": reference_focus.get("effective_peak_to_target_distance_mm"),
            "interpretation": "historical reference only; lacks full current simulation-quality metadata",
        },
        "prepared_standard_review": {
            "future_run_dir": plan.get("future_run_dir"),
            "quality_preset": nested(dry, ["simulation_quality", "preset"]),
            "grid_size": nested(dry, ["simulation_quality", "grid_size"]),
            "ppw_min_sound_speed": nested(dry, ["simulation_quality", "ppw_min_sound_speed"]),
            "pml_size": nested(dry, ["simulation_quality", "pml_size"]),
            "cfl": nested(dry, ["simulation_quality", "cfl"]),
            "memory_estimate_mb": nested(dry, ["simulation_quality", "memory_estimate", "estimated_mb"]),
            "runner_command": plan.get("recommended_runner_command"),
            "requires_explicit_user_authorization": True,
            "checkpoint_sec": 120,
            "hard_stop_min": 30,
        },
        "not_executed": [
            "k-Wave pressure simulation",
            "CT acoustic model rebuild",
            "thermal simulation",
            "source-backed alpha profile promotion",
        ],
    }


def status_label(status: str) -> str:
    return {"pass": "PASS", "warn": "WARN", "block": "BLOCK"}.get(status, status.upper())


def build_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    prep = summary["prepared_standard_review"]
    lines = [
        "# simple_hu300 Baseline Re-entry Report",
        "",
        "> Scope: read-only baseline re-entry planning. No k-Wave, CT rebuild, thermal run, or profile promotion was executed.",
        "",
        "## Decision",
        "",
        f"- case: `{decision['case_id']}`",
        f"- baseline profile: `{decision['baseline_profile']}`",
        f"- source-backed alpha state: `{decision['source_backed_alpha_state']}`",
        f"- standard-review prepared: `{decision['standard_review_prepared']}`",
        f"- execution authorized: `{decision['execution_authorized']}`",
        f"- paper-grade ready: `{decision['paper_grade_ready']}`",
        f"- next state: `{decision['recommended_next_state']}`",
        f"- reason: {decision['reason']}",
        "",
        "## Checklist",
        "",
        "| Status | Check | Blocks | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for check in summary["checks"]:
        blocks = []
        if check["blocks_standard_review"]:
            blocks.append("standard-review")
        if check["blocks_paper_grade"]:
            blocks.append("paper-grade")
        block_text = ", ".join(blocks) if blocks else "none"
        evidence = str(check["evidence"]).replace("\n", " ")
        if len(evidence) > 220:
            evidence = evidence[:217] + "..."
        lines.append(f"| {status_label(check['status'])} | `{check['check_id']}` | {block_text} | {evidence} |")

    runner = prep.get("runner_command") or []
    lines.extend(
        [
            "",
            "## Prepared Standard-review Package",
            "",
            f"- future run dir: `{prep.get('future_run_dir')}`",
            f"- preset: `{prep.get('quality_preset')}`",
            f"- grid size: `{prep.get('grid_size')}`",
            f"- PPW min: `{prep.get('ppw_min_sound_speed')}`",
            f"- PML: `{prep.get('pml_size')}`",
            f"- CFL: `{prep.get('cfl')}`",
            f"- memory estimate MB: `{prep.get('memory_estimate_mb')}`",
            f"- checkpoint: `{prep.get('checkpoint_sec')} s`; hard stop: `{prep.get('hard_stop_min')} min`",
            "",
            "Runner command prepared but not executed:",
            "",
            "```powershell",
            " ".join(str(part) for part in runner),
            "```",
            "",
            "## Reference Run Context",
            "",
            f"- target-window peak MPa: `{summary['reference_run']['target_window_peak_mpa']}`",
            f"- effective peak MPa: `{summary['reference_run']['effective_peak_mpa']}`",
            f"- effective peak to target distance mm: `{summary['reference_run']['effective_peak_to_target_distance_mm']}`",
            f"- interpretation: {summary['reference_run']['interpretation']}",
            "",
            "## Paper-grade Blockers",
            "",
        ]
    )
    paper_blockers = summary["blockers"]["paper_grade"]
    if paper_blockers:
        for blocker in paper_blockers:
            lines.append(f"- `{blocker['check_id']}`: {blocker['evidence']}")
    else:
        lines.append("- None from this read-only gate; user review still required.")

    lines.extend(
        [
            "",
            "## Not Executed",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["not_executed"])
    lines.append("")
    return "\n".join(lines)


def write_gap_feedback(output_dir: Path, summary: dict[str, Any]) -> None:
    brief_dir = PROJECT_ROOT / "outputs/evidence_briefs/simple_hu300_baseline_reentry"
    brief_dir.mkdir(parents=True, exist_ok=True)
    feedback = {
        "module": "simple_hu300_baseline_reentry",
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read source-backed alpha promotion gate",
            "read simple_hu300 model summary",
            "read existing 079 ct_standard_review plan and dry-run quality",
            "generated baseline re-entry readiness report",
        ],
        "outputs": {
            "report": rel(output_dir / "baseline_reentry_report.md"),
            "summary": rel(output_dir / "baseline_reentry_summary.json"),
        },
        "decision": summary["decision"],
        "not_executed": summary["not_executed"],
        "deviations": [
            {
                "deviation": "Initial reference run probe used a non-existent simulation_summary.json name.",
                "evidence": "The existing ct_standard_review plan references summary.json and focus_metrics.json.",
                "adjustment": "Read the actual summary.json and focus_metrics.json paths and treated the missing probe as a filename mismatch, not a data gap.",
            }
        ],
        "recommended_next_step": "Ask for explicit authorization before running the prepared single standard-review runner command.",
    }
    (brief_dir / "gap_feedback.json").write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = "\n".join(
        [
            "# Gap Feedback：simple_hu300 baseline re-entry",
            "",
            "## Actual Execution",
            "",
            "- Read existing source-backed alpha promotion gate outputs.",
            "- Read `simple_hu300` model summary and 079 standard-review planning artifacts.",
            "- Generated a read-only baseline re-entry report.",
            "",
            "## Outputs",
            "",
            f"- `{rel(output_dir / 'baseline_reentry_report.md')}`",
            f"- `{rel(output_dir / 'baseline_reentry_summary.json')}`",
            "",
            "## Decision",
            "",
            f"- standard-review prepared: `{summary['decision']['standard_review_prepared']}`",
            f"- execution authorized: `{summary['decision']['execution_authorized']}`",
            f"- paper-grade ready: `{summary['decision']['paper_grade_ready']}`",
            f"- next state: `{summary['decision']['recommended_next_state']}`",
            "",
            "## Not Executed",
            "",
            "- No k-Wave pressure simulation.",
            "- No CT model rebuild.",
            "- No thermal simulation.",
            "- No profile promotion.",
            "",
            "## Deviation",
            "",
            "- A first probe used `simulation_summary.json`, but the real historical files are `summary.json` and `focus_metrics.json`; the workflow was corrected.",
            "",
        ]
    )
    (brief_dir / "gap_feedback.md").write_text(md, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a simple_hu300 baseline re-entry readiness report.")
    parser.add_argument("--output-dir", default="outputs/simple_hu300_baseline_reentry/079_candidate_006")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_inputs()
    summary = build_summary(data)
    (output_dir / "baseline_reentry_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "baseline_reentry_report.md").write_text(build_markdown(summary), encoding="utf-8-sig")
    write_gap_feedback(output_dir, summary)
    print(f"Wrote {output_dir / 'baseline_reentry_report.md'}")
    print(f"Wrote {output_dir / 'baseline_reentry_summary.json'}")


if __name__ == "__main__":
    main()
