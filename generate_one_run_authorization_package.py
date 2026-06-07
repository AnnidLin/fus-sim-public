from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/one_run_authorization_package/079_candidate_006"
BRIEF_DIR = PROJECT_ROOT / "outputs/evidence_briefs/one_run_authorization_package"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def input_paths() -> dict[str, Path]:
    return {
        "grid_plan": PROJECT_ROOT / "outputs/simple_hu300_ct_grid_convergence_plan/079_candidate_006/ct_grid_convergence_plan.json",
        "pml_plan": PROJECT_ROOT / "outputs/simple_hu300_ct_pml_boundary_review/079_candidate_006_dx0p75/ct_pml_boundary_review_plan.json",
        "cfl_plan": PROJECT_ROOT / "outputs/simple_hu300_ct_cfl_sensitivity_plan/079_candidate_006_dx0p75_pml12/ct_cfl_sensitivity_plan.json",
        "numerical_plan": PROJECT_ROOT / "outputs/numerical_sensitivity_planning/079_candidate_006/numerical_sensitivity_plan.json",
        "cfl_environment_gate": PROJECT_ROOT / "outputs/cfl_environment_gate/cfl_environment_gate.json",
    }


def candidate_score(candidate: dict[str, Any]) -> float:
    value = float(candidate["evidence_value_score"])
    cost = float(candidate["relative_cost_score"])
    risk = float(candidate["risk_score"])
    return round(value - cost - risk, 3)


def build_candidates(inputs: dict[str, dict[str, Any] | None]) -> list[dict[str, Any]]:
    grid = inputs["grid_plan"] or {}
    pml = inputs["pml_plan"] or {}
    cfl = inputs["cfl_plan"] or {}

    dx075 = next((item for item in grid.get("candidates", []) if abs(float(item.get("dx_mm", -1)) - 0.75) < 1e-9), None)
    pml12 = next((item for item in pml.get("candidates", []) if int(item.get("pml_size", -1)) == 12), None)
    cfl03 = next((item for item in cfl.get("candidates", []) if abs(float(item.get("cfl", -1)) - 0.3) < 1e-9), None)
    cfl01 = next((item for item in cfl.get("candidates", []) if abs(float(item.get("cfl", -1)) - 0.1) < 1e-9), None)

    candidates: list[dict[str, Any]] = []
    if dx075:
        candidates.append(
            {
                "candidate_id": "grid_dx0p75_pressure_comparison",
                "planning_leg": "grid_convergence",
                "question_answered": "How much does the existing dx0.75 pressure output differ from a coarser-grid baseline?",
                "status_context": "dx0.75 standard pressure exists in current baseline; additional grid run would be comparatively costly.",
                "expected_runtime_s": None,
                "relative_work": dx075.get("relative_work"),
                "risk_level": dx075.get("risk_level"),
                "output_dir": dx075.get("future_run_dir"),
                "command": dx075.get("future_runner_command"),
                "evidence_value_score": 7.0,
                "relative_cost_score": 4.0,
                "risk_score": 2.0,
                "exit_conditions": [
                    "dry-run-quality missing or source mask changes unexpectedly",
                    "estimated runtime exceeds 30 minute hard stop",
                    "output directory already contains pressure output",
                ],
            }
        )
    if pml12:
        candidates.append(
            {
                "candidate_id": "pml12_pressure_comparison",
                "planning_leg": "pml_boundary",
                "question_answered": "Does increasing PML thickness materially change CT pressure metrics?",
                "status_context": "Current standard pressure output already uses PML12; a new PML run may duplicate existing evidence unless paired with a clear baseline.",
                "expected_runtime_s": None,
                "relative_work": pml12.get("relative_voxel_count"),
                "risk_level": "medium",
                "output_dir": pml12.get("future_run_dir"),
                "command": pml12.get("future_runner_command"),
                "evidence_value_score": 6.0,
                "relative_cost_score": 2.5,
                "risk_score": 1.5,
                "exit_conditions": [
                    "PML baseline/output pairing is ambiguous",
                    "dry-run-quality does not match expected grid/PML",
                    "output directory already contains pressure output",
                ],
            }
        )
    if cfl03:
        candidates.append(
            {
                "candidate_id": "cfl0p3_pressure_comparison",
                "planning_leg": "cfl_sensitivity",
                "question_answered": "Does a larger CFL with fewer time steps preserve current standard pressure metrics?",
                "status_context": "CFL review is explicitly missing; CFL0.3 is lower cost than CFL0.1 and can screen time-step sensitivity first.",
                "expected_runtime_s": cfl03.get("estimated_runtime_s_if_pressure_run"),
                "relative_work": cfl03.get("relative_work_vs_cfl_0p2"),
                "risk_level": "medium",
                "output_dir": cfl03.get("future_run_dir"),
                "command": cfl03.get("blocked_future_pressure_command"),
                "evidence_value_score": 8.0,
                "relative_cost_score": 1.0,
                "risk_score": 2.0,
                "exit_conditions": [
                    "CFL dry-run-quality fails",
                    "estimated runtime exceeds 15 minutes for this lower-cost screen",
                    "focus metrics are unstable enough to require smaller CFL before interpretation",
                ],
            }
        )
    if cfl01:
        candidates.append(
            {
                "candidate_id": "cfl0p1_pressure_comparison",
                "planning_leg": "cfl_sensitivity",
                "question_answered": "Does a smaller CFL with more time steps change current standard pressure metrics?",
                "status_context": "High-value but roughly double baseline time; better as a follow-up if CFL0.3 shows sensitivity.",
                "expected_runtime_s": cfl01.get("estimated_runtime_s_if_pressure_run"),
                "relative_work": cfl01.get("relative_work_vs_cfl_0p2"),
                "risk_level": "medium_high_cost",
                "output_dir": cfl01.get("future_run_dir"),
                "command": cfl01.get("blocked_future_pressure_command"),
                "evidence_value_score": 8.0,
                "relative_cost_score": 4.0,
                "risk_score": 2.0,
                "exit_conditions": [
                    "CFL0.3 has not been reviewed first",
                    "estimated runtime exceeds hard stop budget",
                    "output directory already contains pressure output",
                ],
            }
        )
    for item in candidates:
        item["priority_score"] = candidate_score(item)
    return sorted(candidates, key=lambda item: item["priority_score"], reverse=True)


def build_package() -> dict[str, Any]:
    inputs = {name: read_json(path) for name, path in input_paths().items()}
    candidates = build_candidates(inputs)
    recommended = candidates[0] if candidates else None
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "one_run_authorization_package",
        "scope": "read-only selection package for the next single pressure comparison",
        "inputs": {
            "paths": {name: rel(path) for name, path in input_paths().items()},
            "missing": [name for name, payload in inputs.items() if payload is None],
        },
        "decision": {
            "package_ready": bool(candidates),
            "recommended_candidate_id": None if recommended is None else recommended["candidate_id"],
            "pressure_execution_allowed_now": False,
            "requires_explicit_user_authorization": True,
            "recommended_authorization_wording": (
                "Authorize exactly one CFL0.3 standard pressure comparison run for 079 candidate_006 dx0.75 PML12."
                if recommended and recommended["candidate_id"] == "cfl0p3_pressure_comparison"
                else "No pressure run is recommended without further review."
            ),
        },
        "recommended_candidate": recommended,
        "candidates": candidates,
        "run_budget": {
            "checkpoint_sec": 120,
            "hard_stop_min": 30,
            "expected_exit_condition": "stop on timeout, missing summary.json, missing pressure output, nonzero runner status, or output directory conflict",
        },
        "guardrails": [
            "This package does not authorize execution.",
            "Run at most one pressure comparison after explicit user approval.",
            "Use run_kwave_command.py, not Start-Process or PowerShell jobs.",
            "Do not overwrite locked or existing pressure outputs.",
            "After execution, update run ledger, evidence registry, and gap feedback.",
        ],
        "not_executed": [
            "k-Wave pressure simulation",
            "thermal simulation",
            "paper-grade run",
        ],
    }


def markdown(package: dict[str, Any]) -> str:
    decision = package["decision"]
    recommended = package["recommended_candidate"]
    lines = [
        "# One-Run Authorization Package",
        "",
        f"- package ready: `{decision['package_ready']}`",
        f"- pressure execution allowed now: `{decision['pressure_execution_allowed_now']}`",
        f"- recommended candidate: `{decision['recommended_candidate_id']}`",
        "",
        "## Recommendation",
        "",
    ]
    if recommended:
        lines.extend(
            [
                f"- planning leg: `{recommended['planning_leg']}`",
                f"- question answered: {recommended['question_answered']}",
                f"- expected runtime: `{recommended['expected_runtime_s']}` seconds",
                f"- output dir: `{recommended['output_dir']}`",
                f"- priority score: `{recommended['priority_score']}`",
                "",
                "Command remains blocked until explicit user authorization:",
                "",
                "```powershell",
                " ".join(recommended["command"]),
                "```",
                "",
            ]
        )
    lines.extend(["## Candidates", "", "| Candidate | Leg | Score | Runtime s | Risk |"])
    lines.append("|---|---|---:|---:|---|")
    for item in package["candidates"]:
        lines.append(
            f"| `{item['candidate_id']}` | `{item['planning_leg']}` | `{item['priority_score']}` | "
            f"`{item['expected_runtime_s']}` | `{item['risk_level']}` |"
        )
    lines.extend(["", "## Guardrails", ""])
    lines.extend(f"- {item}" for item in package["guardrails"])
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in package["not_executed"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    package = build_package()
    package_json = OUT_DIR / "one_run_authorization_package.json"
    package_md = OUT_DIR / "one_run_authorization_package.md"
    package_json.write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8")
    package_md.write_text(markdown(package), encoding="utf-8")
    feedback = {
        "module": "one_run_authorization_package",
        "feedback_type": "post_execution_gap_feedback",
        "outputs": {"package_json": rel(package_json), "package_md": rel(package_md)},
        "decision": package["decision"],
        "not_executed": package["not_executed"],
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "# Gap Feedback: One-Run Authorization Package\n\n"
        f"- recommended candidate: `{package['decision']['recommended_candidate_id']}`\n"
        f"- pressure execution allowed now: `{package['decision']['pressure_execution_allowed_now']}`\n"
        "- No pressure simulation was executed.\n",
        encoding="utf-8",
    )
    print(f"Wrote {rel(package_json)}")


if __name__ == "__main__":
    main()
