from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE = "simple_hu300_standard_pressure_authorization_package"
OUT_DIR = PROJECT_ROOT / "outputs" / MODULE / "079_candidate_006"
BRIEF_DIR = PROJECT_ROOT / "outputs" / "evidence_briefs" / MODULE
KWAVE_PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")

INTENDED_RUN_DIR = PROJECT_ROOT / "outputs" / "ct_standard_pressure_authorization" / "079_candidate_006_dx0p75_pml12_standard"
MODEL_PATH = PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d_profile_hu300_dx0p75" / "acoustic_model_3d.npz"
ENTRY_PLAN_PATH = PROJECT_ROOT / "outputs" / "case_refinement_plan" / "079" / "candidate_006" / "entry_plan.json"


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
        "progress_goal_gate": PROJECT_ROOT
        / "outputs/simple_hu300_progress_goal_gate/079_candidate_006/current_progress_goal_gate_summary.json",
        "dx075_execution": PROJECT_ROOT
        / "outputs/ct_grid_convergence_plan/079_candidate_006/dx0p75_model_build_dry_run_summary.json",
        "dx075_quality": PROJECT_ROOT
        / "outputs/ct_grid_convergence_plan/079_candidate_006/dx0p75_dry_run/quality_dry_run_summary.json",
        "pml12_summary": PROJECT_ROOT
        / "outputs/ct_pml_boundary_review/079_candidate_006_dx0p75/pml12_dry_run_summary.json",
        "pml12_quality": PROJECT_ROOT
        / "outputs/ct_pml_boundary_review/079_candidate_006_dx0p75/pml12_dry_run/quality_dry_run_summary.json",
        "model_npz": MODEL_PATH,
        "entry_plan": ENTRY_PLAN_PATH,
        "runner": PROJECT_ROOT / "run_kwave_command.py",
        "simulation_script": PROJECT_ROOT / "simulate_kwave_3d_focus.py",
    }


def load_inputs() -> dict[str, dict[str, Any] | None]:
    data: dict[str, dict[str, Any] | None] = {}
    for name, path in input_paths().items():
        if path.suffix.lower() == ".json":
            data[name] = read_json(path)
        else:
            data[name] = {"exists": path.exists()}
    return data


def runner_plan_command() -> list[str]:
    return [
        str(KWAVE_PYTHON),
        "run_kwave_command.py",
        "--script",
        "simulate_kwave_3d_focus.py",
        "--output-dir",
        rel(INTENDED_RUN_DIR),
        "--preset",
        "standard",
        "--checkpoint-sec",
        "120",
        "--hard-stop-min",
        "30",
        "--model",
        rel(MODEL_PATH),
        "--entry-plan",
        rel(ENTRY_PLAN_PATH),
        "--sim-time-us",
        "55",
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
        "12",
    ]


def runner_execute_command() -> list[str]:
    command = runner_plan_command()
    insert_at = command.index("--checkpoint-sec")
    return command[:insert_at] + ["--execute"] + command[insert_at:]


def command_text(command: list[str]) -> str:
    return " ".join(command)


def build_summary(data: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    missing_inputs = [name for name, payload in data.items() if payload is None or payload.get("exists") is False]
    dx_metrics = nested(data["dx075_execution"], ["dry_run_quality"], {})
    pml_metrics = nested(data["pml12_summary"], ["actual_metrics"], {})
    gate_decision = nested(data["progress_goal_gate"], ["decision"], {})
    intended_pressure = INTENDED_RUN_DIR / "pressure_max_mpa.npz"
    runner_status_path = INTENDED_RUN_DIR / "runner_status.json"
    runner_status = read_json(runner_status_path)
    quality_summary_path = INTENDED_RUN_DIR / "quality_dry_run_summary.json"
    quality_summary = read_json(quality_summary_path)

    planned_not_executed = nested(runner_status, ["status"]) == "planned_not_executed"
    runner_plan_verified = planned_not_executed and quality_summary_path.exists()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "scope": "authorization package for one runner-gated standard pressure run; no pressure execution",
        "inputs": {
            "paths": {name: rel(path) for name, path in input_paths().items()},
            "missing": missing_inputs,
        },
        "decision": {
            "authorization_package_ready": len(missing_inputs) == 0,
            "runner_plan_verified": runner_plan_verified,
            "pressure_run_allowed_now": False,
            "requires_user_authorization": True,
            "paper_grade_ready": False,
            "profile_promotion_allowed": False,
            "recommended_state": "await_explicit_user_authorization_for_single_standard_pressure_run",
        },
        "intended_run": {
            "case_id": "079",
            "candidate_id": "candidate_006",
            "mapping_profile": "simple_hu300",
            "preset": "standard",
            "model": rel(MODEL_PATH),
            "entry_plan": rel(ENTRY_PLAN_PATH),
            "output_dir": rel(INTENDED_RUN_DIR),
            "dx_mm": pml_metrics.get("dx_mm", dx_metrics.get("dx_mm", 0.75)),
            "pml_size": 12,
            "sim_time_us": 55,
            "cycles": 8,
            "aperture_mm": 30,
            "radius_mm": 35,
            "quick_lateral_mm": 17,
            "quick_post_target_mm": 8,
            "checkpoint_sec": 120,
            "hard_stop_min": 30,
        },
        "dry_run_evidence": {
            "dx075_grid_size": dx_metrics.get("grid_size"),
            "dx075_memory_estimate_mb": dx_metrics.get("memory_estimate_mb"),
            "dx075_source_label_counts": dx_metrics.get("source_label_counts"),
            "pml12_grid_size": pml_metrics.get("grid_size"),
            "pml12_memory_estimate_mb": pml_metrics.get("memory_estimate_mb"),
            "pml12_source_label_counts": pml_metrics.get("source_label_counts"),
            "pml12_pressure_npz_exists": nested(data["pml12_summary"], ["pressure_max_mpa_npz_exists"]),
            "progress_gate_decision": gate_decision,
        },
        "commands": {
            "runner_plan_command_no_execute": runner_plan_command(),
            "runner_plan_command_no_execute_text": command_text(runner_plan_command()),
            "runner_execute_command_requires_user_authorization": runner_execute_command(),
            "runner_execute_command_requires_user_authorization_text": command_text(runner_execute_command()),
        },
        "runner_plan_status": {
            "runner_status_path": rel(runner_status_path),
            "runner_status_exists": runner_status_path.exists(),
            "status": nested(runner_status, ["status"]),
            "execute": nested(runner_status, ["execute"]),
            "quality_summary_path": rel(quality_summary_path),
            "quality_summary_exists": quality_summary_path.exists(),
            "dry_run_quality_only": nested(quality_summary, ["dry_run_quality_only"]),
            "pressure_output_exists": intended_pressure.exists(),
        },
        "checkpoints": {
            "checkpoint_sec": 120,
            "hard_stop_min": 30,
            "expected_core_outputs": {
                "pressure": rel(INTENDED_RUN_DIR / "pressure_max_mpa.npz"),
                "summary": rel(INTENDED_RUN_DIR / "summary.json"),
            },
            "stop_on": [
                "timeout_no_core_output",
                "source mask includes non-background labels",
                "summary.json missing after process exit",
                "runner status not kwave_ok",
            ],
        },
        "risk_register": [
            "standard result is engineering validation only, not paper-grade",
            "runtime may exceed dry-run expectations",
            "focus may be poor or target-window pressure may be lower than expected",
            "do not merge historical dx1.0 pressure results with dx0.75/PML12 metadata as one run",
        ],
        "not_executed": [
            "k-Wave pressure simulation",
            "thermal simulation",
            "paper-grade preset run",
            "source-backed alpha pressure run",
            "profile promotion",
        ],
    }


def write_outputs(summary: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUT_DIR / "standard_pressure_authorization_report.md"
    summary_path = OUT_DIR / "standard_pressure_authorization_summary.json"

    lines = [
        "# simple_hu300 Standard Pressure Authorization Package",
        "",
        "## Decision",
        "",
    ]
    for key, value in summary["decision"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Intended Run", ""])
    for key, value in summary["intended_run"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Runner Plan Command (No Execute)", "", "```powershell", summary["commands"]["runner_plan_command_no_execute_text"], "```"])
    lines.extend(
        [
            "",
            "## Execute Command (Requires Explicit User Authorization)",
            "",
            "Do not run this command unless the user explicitly authorizes this exact single standard pressure run.",
            "",
            "```powershell",
            summary["commands"]["runner_execute_command_requires_user_authorization_text"],
            "```",
        ]
    )
    lines.extend(["", "## Runner Plan Status", ""])
    for key, value in summary["runner_plan_status"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Dry-Run Evidence", ""])
    for key, value in summary["dry_run_evidence"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Checkpoints And Stop Conditions", ""])
    lines.append(f"- checkpoint: `{summary['checkpoints']['checkpoint_sec']} sec`")
    lines.append(f"- hard stop: `{summary['checkpoints']['hard_stop_min']} min`")
    for item in summary["checkpoints"]["stop_on"]:
        lines.append(f"- stop on: {item}")
    lines.extend(["", "## Risk Register", ""])
    lines.extend(f"- {item}" for item in summary["risk_register"])
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in summary["not_executed"])
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    feedback = {
        "module": MODULE,
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read dx0.75 and PML12 dry-run evidence",
            "generated standard pressure authorization package",
            "verified runner plan mode without --execute",
        ],
        "outputs": {
            "report": rel(report_path),
            "summary": rel(summary_path),
            "runner_status": summary["runner_plan_status"]["runner_status_path"],
        },
        "decision": summary["decision"],
        "runner_plan_status": summary["runner_plan_status"],
        "not_executed": summary["not_executed"],
        "recommended_next_step": "Ask the user to explicitly authorize or reject the exact single standard pressure run command.",
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "\n".join(
            [
                "# Gap Feedback: simple_hu300 Standard Pressure Authorization Package",
                "",
                "## Actual Execution",
                "",
                "- Read existing dx0.75 and PML12 dry-run evidence.",
                "- Generated standard pressure authorization report and summary.",
                "- Verified runner plan mode without `--execute`.",
                "",
                "## Decision",
                "",
                f"- authorization_package_ready: `{summary['decision']['authorization_package_ready']}`",
                f"- runner_plan_verified: `{summary['decision']['runner_plan_verified']}`",
                f"- pressure_run_allowed_now: `{summary['decision']['pressure_run_allowed_now']}`",
                f"- requires_user_authorization: `{summary['decision']['requires_user_authorization']}`",
                "",
                "## Outputs",
                "",
                f"- `{rel(report_path)}`",
                f"- `{rel(summary_path)}`",
                f"- `{summary['runner_plan_status']['runner_status_path']}`",
                "",
                "## Not Executed",
                "",
                "- No k-Wave pressure simulation.",
                "- No thermal simulation.",
                "- No paper-grade preset run.",
                "- No source-backed alpha pressure run.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    data = load_inputs()
    summary = build_summary(data)
    write_outputs(summary)
    print(f"Wrote {rel(OUT_DIR / 'standard_pressure_authorization_report.md')}")
    print(f"Wrote {rel(OUT_DIR / 'standard_pressure_authorization_summary.json')}")


if __name__ == "__main__":
    main()
