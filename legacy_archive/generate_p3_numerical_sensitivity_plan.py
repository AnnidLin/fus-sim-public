from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE = "p3_numerical_sensitivity_plan"
OUT_DIR = PROJECT_ROOT / "outputs" / MODULE / "079_candidate_006_dx0p75"
OUT_JSON = OUT_DIR / "p3_numerical_sensitivity_plan.json"
OUT_MD = OUT_DIR / "p3_numerical_sensitivity_plan.md"
BRIEF_DIR = PROJECT_ROOT / "outputs" / "evidence_briefs" / MODULE

BASELINE_DIR = PROJECT_ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard"
BASELINE_SUMMARY = BASELINE_DIR / "summary.json"
BASELINE_RUNNER = BASELINE_DIR / "runner_status.json"
BASELINE_FOCUS = BASELINE_DIR / "focus_metrics.json"
MODEL_PATH = PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/acoustic_model_3d.npz"
ENTRY_PLAN_PATH = PROJECT_ROOT / "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p75/selected_entry_plan.json"
P3A_REPORT = PROJECT_ROOT / "outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report.json"
P3A_REPORT_VALIDATION = PROJECT_ROOT / "outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report_validation.json"
P3B_REPORT = PROJECT_ROOT / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report.json"
P3B_REPORT_VALIDATION = PROJECT_ROOT / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report_validation.json"
P3C_VALIDATION = PROJECT_ROOT / "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p5/corrected_entry_plan_resolution_chain_validation.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return read_json(path)


def nested(data: dict[str, Any] | None, keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def runner_args(*, output_dir: str, pml_size: int, cfl: float) -> list[str]:
    return [
        "run_kwave_command.py",
        "--script",
        "simulate_kwave_3d_focus.py",
        "--output-dir",
        output_dir,
        "--preset",
        "standard",
        "--checkpoint-sec",
        "120",
        "--hard-stop-min",
        "60" if cfl >= 0.2 else "90",
        "--model",
        rel(MODEL_PATH),
        "--entry-plan",
        rel(ENTRY_PLAN_PATH),
        "--sim-time-us",
        "85",
        "--cycles",
        "8",
        "--quick-lateral-mm",
        "17",
        "--quick-post-target-mm",
        "8",
        "--aperture-mm",
        "30",
        "--radius-mm",
        "35",
        "--pml-size",
        str(pml_size),
        "--cfl",
        str(cfl),
    ]


def packet(
    packet_id: str,
    status: str,
    purpose: str,
    output_dir: str,
    pml_size: int,
    cfl: float,
    hard_stop_min: int,
    gates: list[str],
    next_action: str,
) -> dict[str, Any]:
    return {
        "packet_id": packet_id,
        "status": status,
        "agent_budget_class": "L",
        "authorization": "required_before_execute",
        "purpose": purpose,
        "output_dir": output_dir,
        "preset": "standard",
        "pml_size": pml_size,
        "cfl": cfl,
        "checkpoint_sec": 120,
        "hard_stop_min": hard_stop_min,
        "planned_runner_command_without_execute": runner_args(output_dir=output_dir, pml_size=pml_size, cfl=cfl),
        "execute_policy": "Add --execute only after explicit one-run authorization for this packet.",
        "required_gates": gates,
        "success_outputs": [
            "runner_status.json",
            "summary.json",
            "focus_metrics.json",
            "pressure_max_mpa.npz",
        ],
        "comparison_metrics": [
            "target_pressure_mpa",
            "target_window_peak_mpa",
            "global_peak_to_target_distance_mm",
            "target_to_global_peak_ratio",
            "effective_peak_to_target_distance_mm",
            "target_to_effective_peak_ratio",
        ],
        "pause_thresholds": {
            "target_window_peak_relative_delta_gt": 0.2,
            "target_to_global_peak_ratio_relative_delta_gt": 0.2,
            "global_peak_to_target_distance_delta_mm_gt": 5.0,
        },
        "next_action": next_action,
    }


def build_plan() -> dict[str, Any]:
    summary = read_json(BASELINE_SUMMARY)
    runner = read_json(BASELINE_RUNNER)
    focus = read_json(BASELINE_FOCUS)
    baseline_runtime_s = float(nested(runner, ["execution", "runtime_s"], 0.0))
    baseline_nt = int(nested(summary, ["runtime", "nt"], 0))
    p3a_report = read_json_if_exists(P3A_REPORT)
    p3a_validation = read_json_if_exists(P3A_REPORT_VALIDATION)
    p3a_completed = nested(p3a_validation, ["report_valid"], False) is True
    p3a_stable = nested(p3a_report, ["decision", "p3a_stable_within_thresholds"], False) is True
    p3b_ready = p3a_completed and p3a_stable
    p3b_report = read_json_if_exists(P3B_REPORT)
    p3b_validation = read_json_if_exists(P3B_REPORT_VALIDATION)
    p3c_validation = read_json_if_exists(P3C_VALIDATION)
    p3b_completed = nested(p3b_validation, ["report_valid"], False) is True
    p3b_stable = nested(p3b_report, ["decision", "p3b_stable_within_thresholds"], False) is True
    p3c_completed = nested(p3c_validation, ["chain_valid"], False) is True

    p3a_output = "outputs/corrected_pressure_sensitivity/079_candidate_006_dx0p75_pml16_cfl0p2_standard"
    p3b_output = "outputs/corrected_pressure_sensitivity/079_candidate_006_dx0p75_pml12_cfl0p1_standard"

    return {
        "plan_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "case_id": "079",
        "candidate_id": "candidate_006",
        "baseline": {
            "run_id": "079_candidate_006_simple_hu300_dx075_pml12_cfl02_corrected_standard_2026-06-18",
            "output_dir": rel(BASELINE_DIR),
            "summary_path": rel(BASELINE_SUMMARY),
            "runner_status_path": rel(BASELINE_RUNNER),
            "focus_metrics_path": rel(BASELINE_FOCUS),
            "runner_status": nested(runner, ["status"]),
            "runtime_s": baseline_runtime_s,
            "model_path": nested(summary, ["config", "model_path"]),
            "entry_plan_path": nested(summary, ["config", "entry_plan_path"]),
            "preset": nested(summary, ["config", "preset"]),
            "dx_m": nested(summary, ["dx_m"]),
            "grid_size": nested(summary, ["simulation_quality", "grid_size"]),
            "nt": baseline_nt,
            "pml_size": nested(summary, ["config", "pml_size"]),
            "cfl": nested(summary, ["config", "cfl"]),
            "target_pressure_mpa": nested(focus, ["target_pressure_mpa"]),
            "target_window_peak_mpa": nested(focus, ["target_window_peak_mpa"]),
            "global_peak_to_target_distance_mm": nested(focus, ["global_peak_to_target_distance_mm"]),
            "target_to_global_peak_ratio": nested(focus, ["target_to_global_peak_ratio"]),
            "tuning_note": nested(summary, ["tuning_note"]),
        },
        "claim_boundary": {
            "claim_level": "numerical_sensitivity_plan_only",
            "allowed_claims": [
                "P3 sensitivity legs are planned as separate one-run authorization packets",
                "P3a PML16 is complete and stable within thresholds"
                if p3a_completed and p3a_stable
                else "P3a PML16 is the first recommended sensitivity run",
                "P3b CFL0.1 is awaiting one-run authorization"
                if p3b_ready and not p3b_completed
                else "P3b CFL0.1 is complete and stable within thresholds"
                if p3b_completed and p3b_stable
                else "P3b CFL0.1 is blocked until P3a is reviewed",
            ],
            "blocked_claims": [
                "additional pressure simulation has been authorized",
                "additional pressure simulation has been run",
                "thermal simulation",
                "tuned focus baseline",
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical or safety conclusion",
                "numerical convergence claim",
            ],
        },
        "immediate_next_packet": (
            "P5_final_reproducibility_package"
            if p3c_completed
            else "P3c_corrected_dx0p5_grid_sensitivity_prerequisite"
            if p3b_completed and p3b_stable
            else "pause_for_p3b_timestep_analysis"
            if p3b_completed
            else
            "P3b_cfl0p1_timestep_sensitivity_authorization"
            if p3b_ready
            else "pause_for_p3a_boundary_analysis"
            if p3a_completed
            else "P3a_pml16_boundary_sensitivity_authorization"
        ),
        "packets": [
            packet(
                "P3a_pml16_boundary_sensitivity_authorization",
                "completed" if p3a_completed else "awaiting_user_authorization",
                "Check boundary/PML sensitivity against the corrected P2 baseline before spending longer CFL runtime.",
                p3a_output,
                16,
                0.2,
                60,
                [
                    "P2 baseline runner_status is kwave_ok",
                    "output directory has no pressure_max_mpa.npz conflict",
                    "run through run_kwave_command.py",
                    "runner performs dry-run-quality before execution",
                    "explicit user authorization names this packet",
                ],
                "If P3a is stable within thresholds, request authorization for P3b CFL0.1; otherwise pause for analysis.",
            ),
            packet(
                "P3b_cfl0p1_timestep_sensitivity_authorization",
                "completed" if p3b_completed else "awaiting_user_authorization" if p3b_ready else "blocked_until_P3a_review",
                "Check time-step sensitivity with smaller CFL after PML boundary behavior is acceptable.",
                p3b_output,
                12,
                0.1,
                90,
                [
                    "P3a runner_status is kwave_ok",
                    "P3a comparison report is reviewed",
                    "output directory has no pressure_max_mpa.npz conflict",
                    "run through run_kwave_command.py",
                    "runner performs dry-run-quality before execution",
                    "explicit user authorization names this packet",
                ],
                "If P3b is stable within thresholds, decide whether tuning or dx0.5 corrected-grid planning is more valuable.",
            ),
            {
                "packet_id": "P3c_corrected_dx0p5_grid_sensitivity_prerequisite",
                "status": "completed"
                if p3c_completed
                else "planned_coordinate_chain_prerequisite"
                if p3b_completed and p3b_stable
                else "blocked_until_dx0p75_sensitivity_review",
                "agent_budget_class": "M_before_L",
                "authorization": "not_authorized_for_pressure",
                "purpose": "Prepare a corrected dx0.5 entry/source/target chain before any dx0.5 pressure comparison.",
                "required_gates": [
                    "dx0.5 corrected entry plan exists",
                    "dx0.5 dry-run-quality passes without --allow-entry-plan-resolution-mismatch",
                    "source mask is background-only",
                    "crop contains skull material when skull crossing is expected",
                ],
                "next_action": "Coordinate-chain prerequisite complete; dx0.5 pressure still requires separate one-run authorization."
                if p3c_completed
                else "Do not run dx0.5 pressure until the corrected dx0.5 coordinate chain is generated and separately authorized.",
            },
        ],
        "comparison_policy": {
            "baseline_is_not_tuned_focus": True,
            "primary_decision": "Use PML16 first because it is the cheapest boundary check and preserves dt/nt.",
            "secondary_decision": "Use CFL0.1 only after PML16 is reviewed because it roughly doubles nt and runtime.",
            "pause_if": [
                "P3a changes target-window peak or target/global ratio by more than 20%.",
                "P3a moves global peak distance to target by more than 5 mm.",
                "Any run reports source mask labels outside background.",
                "Any run bypasses entry-plan resolution gate.",
            ],
        },
        "not_executed": [
            "additional pressure simulation beyond P3b"
            if p3b_completed
            else "additional pressure simulation beyond P3a"
            if p3a_completed
            else "additional pressure simulation",
            "thermal simulation",
            "paper-grade candidate run",
            "profile/default promotion",
        ],
    }


def build_markdown(plan: dict[str, Any]) -> str:
    baseline = plan["baseline"]
    lines = [
        "# P3 Numerical Sensitivity Plan",
        "",
        f"- generated at: `{plan['generated_at']}`",
        f"- immediate next packet: `{plan['immediate_next_packet']}`",
        f"- claim level: `{plan['claim_boundary']['claim_level']}`",
        "",
        "## Baseline",
        "",
        f"- output: `{baseline['output_dir']}`",
        f"- runner status: `{baseline['runner_status']}`",
        f"- runtime s: `{baseline['runtime_s']}`",
        f"- grid: `{baseline['grid_size']}`",
        f"- nt: `{baseline['nt']}`",
        f"- PML/CFL: `{baseline['pml_size']}` / `{baseline['cfl']}`",
        f"- target pressure MPa: `{baseline['target_pressure_mpa']}`",
        f"- target-window peak MPa: `{baseline['target_window_peak_mpa']}`",
        f"- global peak to target distance mm: `{baseline['global_peak_to_target_distance_mm']}`",
        f"- target/global peak ratio: `{baseline['target_to_global_peak_ratio']}`",
        f"- tuning note: `{baseline['tuning_note']}`",
        "",
        "## Packets",
        "",
        "| Packet | Status | PML | CFL | Hard Stop | Output | Next Action |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for item in plan["packets"]:
        lines.append(
            f"| `{item['packet_id']}` | `{item['status']}` | `{item.get('pml_size', '')}` | "
            f"`{item.get('cfl', '')}` | `{item.get('hard_stop_min', '')}` | "
            f"`{item.get('output_dir', '')}` | {item['next_action']} |"
        )
    lines.extend(["", "## Blocked Claims", ""])
    lines.extend(f"- {item}" for item in plan["claim_boundary"]["blocked_claims"])
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in plan["not_executed"])
    lines.append("")
    return "\n".join(lines)


def write_evidence_brief(plan: dict[str, Any]) -> None:
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    brief = {
        "module": MODULE,
        "brief_type": "pre_execution_planning_evidence_brief",
        "created_at": plan["generated_at"],
        "goal": "Plan the smallest P3 numerical sensitivity sequence for the corrected dx0.75 pressure candidate without running additional pressure.",
        "baseline_inputs": plan["baseline"],
        "recommended_engineering_decision": plan["comparison_policy"],
        "acceptance_criteria": [
            "P3 plan exists",
            "each real run is represented as a separate authorization packet",
            "no packet contains --execute before explicit authorization",
            "thermal remains blocked",
        ],
        "blocked_claims": plan["claim_boundary"]["blocked_claims"],
    }
    (BRIEF_DIR / "evidence_brief.json").write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "evidence_brief.md").write_text(
        "\n".join(
            [
                "# Evidence Brief: P3 Numerical Sensitivity Plan",
                "",
                "## Goal",
                "",
                brief["goal"],
                "",
                "## Baseline",
                "",
                f"- corrected run: `{plan['baseline']['output_dir']}`",
                f"- tuning note: `{plan['baseline']['tuning_note']}`",
                "",
                "## Engineering Decision",
                "",
                f"- {plan['comparison_policy']['primary_decision']}",
                f"- {plan['comparison_policy']['secondary_decision']}",
                "",
                "## Blocked Claims",
                "",
                *[f"- {item}" for item in plan["claim_boundary"]["blocked_claims"]],
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_gap_feedback(plan: dict[str, Any]) -> None:
    p3a_packet = next(
        (
            item
            for item in plan["packets"]
            if item.get("packet_id") == "P3a_pml16_boundary_sensitivity_authorization"
        ),
        {},
    )
    p3a_completed = p3a_packet.get("status") == "completed"
    p3b_packet = next(
        (
            item
            for item in plan["packets"]
            if item.get("packet_id") == "P3b_cfl0p1_timestep_sensitivity_authorization"
        ),
        {},
    )
    p3b_completed = p3b_packet.get("status") == "completed"
    feedback = {
        "module": MODULE,
        "feedback_type": "post_planning_gap_feedback",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actual_execution": [
            "read corrected P2 baseline summary, runner status, and focus metrics",
            "generated or refreshed P3 one-run authorization packet plan",
            "reflected completed P3a PML16 sensitivity run"
            if p3a_completed
            else "did not run additional pressure",
            "reflected completed P3b CFL0.1 sensitivity run"
            if p3b_completed
            else "did not run P3b",
            "did not run thermal",
        ],
        "outputs": {
            "plan_json": rel(OUT_JSON),
            "plan_md": rel(OUT_MD),
        },
        "deviations": [
            "P2 baseline has a far-target peak tuning note, so P3 is constrained to minimal numerical sensitivity before any stronger interpretation.",
        ],
        "recommended_next_step": plan["immediate_next_packet"],
        "blocked_claims": plan["claim_boundary"]["blocked_claims"],
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "\n".join(
            [
                "# Gap Feedback: P3 Numerical Sensitivity Plan",
                "",
                "## Actual Execution",
                "",
                "- Read corrected P2 baseline summary, runner status, and focus metrics.",
                "- Generated or refreshed P3 one-run authorization packet plan.",
                "- Reflected completed P3a PML16 sensitivity run." if p3a_completed else "- Did not run additional pressure.",
                "- Reflected completed P3b CFL0.1 sensitivity run." if p3b_completed else "- Did not run P3b.",
                "- Did not run thermal.",
                "",
                "## Outputs",
                "",
                f"- `{rel(OUT_JSON)}`",
                f"- `{rel(OUT_MD)}`",
                "",
                "## Next Step",
                "",
                f"- `{plan['immediate_next_packet']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plan = build_plan()
    OUT_JSON.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(build_markdown(plan), encoding="utf-8")
    write_evidence_brief(plan)
    write_gap_feedback(plan)
    print(f"Wrote {rel(OUT_JSON)}")
    print(f"Wrote {rel(OUT_MD)}")


if __name__ == "__main__":
    main()
