from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
KWAVE_PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
OUT_DIR = PROJECT_ROOT / "outputs/simple_hu300_ct_cfl_sensitivity_plan/079_candidate_006_dx0p75_pml12"
BRIEF_DIR = PROJECT_ROOT / "outputs/evidence_briefs/ct_cfl_sensitivity_plan"


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
        "standard_pressure_execution": run_dir / "standard_pressure_execution_summary.json",
        "kwave_summary": run_dir / "summary.json",
        "runner_status": run_dir / "runner_status.json",
        "cfl_environment_gate": PROJECT_ROOT / "outputs/cfl_environment_gate/cfl_environment_gate.json",
        "simulation_presets": PROJECT_ROOT / "simulation_presets.json",
    }


def build_command(cfl: float, output_dir: str, *, execute: bool) -> list[str]:
    command = [
        str(KWAVE_PYTHON),
        "run_kwave_command.py",
        "--script",
        "simulate_kwave_3d_focus.py",
        "--output-dir",
        output_dir,
        "--preset",
        "standard",
        "--model",
        "outputs\\ct_acoustic_model_3d_profile_hu300_dx0p75\\acoustic_model_3d.npz",
        "--entry-plan",
        "outputs\\case_refinement_plan\\079\\candidate_006\\entry_plan.json",
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
        "--cfl",
        f"{cfl:g}",
        "--checkpoint-sec",
        "120",
        "--hard-stop-min",
        "30",
    ]
    if execute:
        command.append("--execute")
    return command


def build_plan(cfl_values: list[float]) -> dict[str, Any]:
    inputs = {name: read_json(path) for name, path in input_paths().items()}
    summary = inputs["kwave_summary"]
    quality = nested(summary, ["simulation_quality"], {})
    baseline_cfl = float(nested(quality, ["cfl"], 0.2))
    baseline_dt = float(nested(quality, ["dt_s"], 5.3571429037089864e-08))
    baseline_nt = int(nested(quality, ["nt"], 1027))
    baseline_runtime = float(nested(quality, ["runtime_s"], 778.9684731999878))
    candidates = []
    for cfl in cfl_values:
        relative_dt = cfl / baseline_cfl
        nt_estimate = int(math.ceil(baseline_nt / relative_dt))
        relative_work = nt_estimate / baseline_nt
        dry_dir = f"outputs\\simple_hu300_ct_cfl_sensitivity_plan\\079_candidate_006_dx0p75_pml12\\cfl{str(cfl).replace('.', 'p')}_dry_run"
        future_dir = f"outputs\\ct_cfl_sensitivity_runs\\079_candidate_006_dx0p75_pml12_cfl{str(cfl).replace('.', 'p')}_standard"
        role = "baseline_existing" if abs(cfl - baseline_cfl) < 1e-9 else "dry_run_quality_candidate"
        recommendation = (
            "Use existing standard run as baseline."
            if role == "baseline_existing"
            else "Run dry-run-quality only before considering any pressure execution."
        )
        candidates.append(
            {
                "cfl": cfl,
                "role": role,
                "estimated_dt_s": baseline_dt * relative_dt,
                "estimated_nt": nt_estimate,
                "relative_work_vs_cfl_0p2": relative_work,
                "estimated_runtime_s_if_pressure_run": baseline_runtime * relative_work,
                "dry_run_output_dir": dry_dir,
                "future_run_dir": future_dir,
                "dry_run_command": build_command(cfl, dry_dir, execute=False),
                "blocked_future_pressure_command": build_command(cfl, future_dir, execute=True),
                "recommendation": recommendation,
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "ct_cfl_sensitivity_plan",
        "scope": "read-only CFL sensitivity planning for simple_hu300 079 candidate_006 dx0.75 PML12",
        "inputs": {
            "paths": {name: rel(path) for name, path in input_paths().items()},
            "exists": {name: payload is not None for name, payload in inputs.items()},
        },
        "baseline": {
            "cfl": baseline_cfl,
            "dt_s": baseline_dt,
            "nt": baseline_nt,
            "runtime_s": baseline_runtime,
            "preset": nested(summary, ["simulation_quality", "preset"], "standard"),
        },
        "decision": {
            "plan_ready": bool(candidates),
            "dry_run_quality_allowed": True,
            "pressure_run_allowed": False,
            "paper_grade_ready": False,
            "recommended_next_action": "Review CFL dry-run-quality candidates; do not execute pressure without explicit authorization.",
        },
        "candidates": candidates,
        "guardrails": [
            "This plan does not authorize any pressure solve.",
            "CFL dry-run-quality checks metadata and cost only.",
            "Any pressure comparison must be exactly one authorized run after reviewing dry-run output.",
        ],
        "not_executed": [
            "k-Wave pressure simulation",
            "thermal simulation",
            "paper-grade run",
        ],
    }


def markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# CT CFL Sensitivity Plan",
        "",
        f"- baseline CFL: `{plan['baseline']['cfl']}`",
        f"- pressure run allowed: `{plan['decision']['pressure_run_allowed']}`",
        f"- recommended next action: {plan['decision']['recommended_next_action']}",
        "",
        "| CFL | Role | Estimated nt | Relative Work | Recommendation |",
        "|---:|---|---:|---:|---|",
    ]
    for item in plan["candidates"]:
        lines.append(
            f"| `{item['cfl']}` | `{item['role']}` | `{item['estimated_nt']}` | "
            f"`{item['relative_work_vs_cfl_0p2']:.2f}` | {item['recommendation']} |"
        )
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in plan["not_executed"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    plan = build_plan([0.1, 0.2, 0.3])
    plan_json = OUT_DIR / "ct_cfl_sensitivity_plan.json"
    plan_md = OUT_DIR / "ct_cfl_sensitivity_plan.md"
    plan_json.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    plan_md.write_text(markdown(plan), encoding="utf-8")
    feedback = {
        "module": "ct_cfl_sensitivity_plan",
        "feedback_type": "post_execution_gap_feedback",
        "outputs": {"plan_json": rel(plan_json), "plan_md": rel(plan_md)},
        "decision": plan["decision"],
        "not_executed": plan["not_executed"],
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "# Gap Feedback: CT CFL Sensitivity Plan\n\n"
        f"- plan ready: `{plan['decision']['plan_ready']}`\n"
        f"- pressure run allowed: `{plan['decision']['pressure_run_allowed']}`\n"
        "- No k-Wave pressure simulation was executed.\n",
        encoding="utf-8",
    )
    print(f"Wrote {rel(plan_json)}")


if __name__ == "__main__":
    main()
