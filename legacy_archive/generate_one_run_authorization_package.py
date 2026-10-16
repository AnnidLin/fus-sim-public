from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/one_run_authorization_package/079_candidate_006"
BRIEF_DIR = PROJECT_ROOT / "outputs/evidence_briefs/one_run_authorization_package"
GRID_DX0P5_HARD_STOP_MIN = 75


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
        "readiness_checklist": PROJECT_ROOT / "outputs/paper_grade_readiness_checklist/paper_grade_readiness_checklist.md",
        "baseline_summary": PROJECT_ROOT / "outputs/ct_standard_pressure_authorization/079_candidate_006_dx0p75_pml12_standard/summary.json",
        "cfl0p3_summary": PROJECT_ROOT / "outputs/ct_cfl_sensitivity_runs/079_candidate_006_dx0p75_pml12_cfl0p3_standard/summary.json",
        "cfl0p1_summary": PROJECT_ROOT / "outputs/ct_cfl_sensitivity_runs/079_candidate_006_dx0p75_pml12_cfl0p1_standard/summary.json",
        "pml16_summary": PROJECT_ROOT / "outputs/ct_pml_sensitivity_runs/079_candidate_006_dx0p75_pml16_cfl0p2_standard/summary.json",
        "entry_plan": PROJECT_ROOT / "outputs/case_refinement_plan/079/candidate_006/entry_plan.json",
        "dx0p5_model_summary": PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p5/summary.json",
    }


def candidate_score(candidate: dict[str, Any]) -> float:
    value = float(candidate["evidence_value_score"])
    cost = float(candidate["relative_cost_score"])
    risk = float(candidate["risk_score"])
    return round(value - cost - risk, 3)


def completed_context(inputs: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    baseline = inputs.get("baseline_summary") or {}
    cfl03 = inputs.get("cfl0p3_summary") or {}
    cfl01 = inputs.get("cfl0p1_summary") or {}
    pml16 = inputs.get("pml16_summary") or {}
    resolution_gate = entry_plan_resolution_gate(inputs)
    return {
        "baseline_dx0p75_cfl0p2_pml12_present": bool(baseline),
        "cfl0p3_present": bool(cfl03),
        "cfl0p1_present": bool(cfl01),
        "pml16_present": bool(pml16),
        "baseline_runtime_s": (baseline.get("runtime") or {}).get("runtime_s"),
        "cfl0p1_runtime_s": (cfl01.get("runtime") or {}).get("runtime_s"),
        "pml16_runtime_s": (pml16.get("runtime") or {}).get("runtime_s"),
        "numerical_sensitivity_status": (
            "cfl_and_pml_context_present"
            if bool(cfl03) and bool(cfl01) and bool(pml16)
            else "incomplete_context"
        ),
        "entry_plan_resolution_gate": resolution_gate,
    }


def entry_plan_resolution_gate(inputs: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    entry_plan = inputs.get("entry_plan") or {}
    model = inputs.get("dx0p5_model_summary") or {}
    entry_dx = entry_plan.get("dx_m")
    model_dx = model.get("dx_m")
    entry_shape = entry_plan.get("model_shape")
    model_shape = model.get("grid_shape")
    dx_matches = entry_dx is not None and model_dx is not None and abs(float(entry_dx) - float(model_dx)) <= 1e-9
    shape_matches = entry_shape is not None and model_shape is not None and list(entry_shape) == list(model_shape)
    compatible = dx_matches and shape_matches
    return {
        "target": "dx0p5",
        "compatible": compatible,
        "status": "pass" if compatible else "block",
        "entry_plan_dx_m": entry_dx,
        "model_dx_m": model_dx,
        "entry_plan_model_shape": entry_shape,
        "model_shape": model_shape,
        "reason": (
            "entry plan resolution matches target model"
            if compatible
            else "entry plan dx_m/model_shape does not match the dx0p5 acoustic model"
        ),
        "next_action": "Regenerate or transform entry_plan for the dx0p5 acoustic model before any further pressure run.",
    }


def estimate_grid_runtime_s(candidate: dict[str, Any], context: dict[str, Any]) -> float | None:
    baseline_runtime = context.get("baseline_runtime_s")
    relative_work = candidate.get("relative_work")
    grid_plan_baseline_work = 3.273956647489115
    if baseline_runtime is None or relative_work is None:
        return None
    return round(float(baseline_runtime) * float(relative_work) / grid_plan_baseline_work, 1)


def with_hard_stop(command: list[str] | None, hard_stop_min: int) -> list[str] | None:
    if command is None:
        return None
    updated = list(command)
    if "--hard-stop-min" in updated:
        index = updated.index("--hard-stop-min")
        if index + 1 < len(updated):
            updated[index + 1] = str(hard_stop_min)
            return updated
    updated.extend(["--hard-stop-min", str(hard_stop_min)])
    return updated


def with_option(command: list[str] | None, option: str, value: str) -> list[str] | None:
    if command is None:
        return None
    updated = list(command)
    if option in updated:
        index = updated.index(option)
        if index + 1 < len(updated):
            updated[index + 1] = value
            return updated
    insert_at = updated.index("--execute") if "--execute" in updated else len(updated)
    updated[insert_at:insert_at] = [option, value]
    return updated


def build_candidates(inputs: dict[str, dict[str, Any] | None]) -> list[dict[str, Any]]:
    grid = inputs["grid_plan"] or {}
    context = completed_context(inputs)

    dx05 = next((item for item in grid.get("candidates", []) if abs(float(item.get("dx_mm", -1)) - 0.5) < 1e-9), None)

    candidates: list[dict[str, Any]] = []
    resolution_gate = context["entry_plan_resolution_gate"]
    if dx05 and context["numerical_sensitivity_status"] == "cfl_and_pml_context_present" and resolution_gate["compatible"]:
        expected_runtime_s = estimate_grid_runtime_s(dx05, context)
        candidates.append(
            {
                "candidate_id": "grid_dx0p5_pressure_comparison",
                "planning_leg": "grid_convergence",
                "question_answered": "Does a finer dx=0.5 mm CT grid materially change the current dx=0.75 mm standard pressure metrics?",
                "status_context": "CFL0.1/CFL0.3 and PML16 sensitivity context is present; grid convergence is now the main paper-grade blocker.",
                "expected_runtime_s": expected_runtime_s,
                "relative_work": dx05.get("relative_work"),
                "risk_level": dx05.get("risk_level"),
                "output_dir": dx05.get("future_run_dir"),
                "command": with_hard_stop(
                    with_option(
                        with_option(dx05.get("future_runner_command"), "--pml-size", "12"),
                        "--cfl",
                        "0.2",
                    ),
                    GRID_DX0P5_HARD_STOP_MIN,
                ),
                "evidence_value_score": 9.0,
                "relative_cost_score": 6.0,
                "risk_score": 3.0,
                "exit_conditions": [
                    "dx=0.5 model build or dry-run-quality has not been refreshed immediately before execution",
                    "dry-run-quality source mask, PPW, PML, CFL, grid size, nt, or memory estimate deviates from the authorization package",
                    "estimated runtime exceeds the approved hard stop",
                    "output directory already contains pressure output",
                    "runner status is nonzero or summary/pressure outputs are missing at checkpoint review",
                ],
            }
        )
    for item in candidates:
        item["priority_score"] = candidate_score(item)
    return sorted(candidates, key=lambda item: item["priority_score"], reverse=True)


def build_package() -> dict[str, Any]:
    paths = input_paths()
    inputs = {name: read_json(path) for name, path in paths.items() if path.suffix.lower() == ".json"}
    for name, path in paths.items():
        if path.suffix.lower() != ".json":
            inputs[name] = {"exists": path.exists()} if path.exists() else None
    candidates = build_candidates(inputs)
    recommended = candidates[0] if candidates else None
    context = completed_context(inputs)
    resolution_gate = context["entry_plan_resolution_gate"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "one_run_authorization_package",
        "scope": "read-only selection package for the next single CT grid-convergence pressure comparison",
        "inputs": {
            "paths": {name: rel(path) for name, path in paths.items()},
            "missing": [name for name, payload in inputs.items() if payload is None],
        },
        "completed_context": context,
        "decision": {
            "package_ready": bool(candidates),
            "recommended_candidate_id": None if recommended is None else recommended["candidate_id"],
            "pressure_execution_allowed_now": False,
            "requires_explicit_user_authorization": True,
            "recommended_authorization_wording": (
                "Authorize exactly one dx=0.5 mm standard CT grid-convergence pressure run for 079 candidate_006, after model-build and dry-run-quality checks pass."
                if recommended and recommended["candidate_id"] == "grid_dx0p5_pressure_comparison"
                else "No pressure run is recommended until entry_plan resolution matches the target acoustic model."
                if resolution_gate["status"] == "block"
                else "No pressure run is recommended without further review."
            ),
            "entry_plan_resolution_gate_status": resolution_gate["status"],
        },
        "recommended_candidate": recommended,
        "candidates": candidates,
        "run_budget": {
            "checkpoint_sec": 120,
            "hard_stop_min": GRID_DX0P5_HARD_STOP_MIN,
            "expected_exit_condition": "stop on timeout, missing summary.json, missing pressure output, nonzero runner status, or output directory conflict",
        },
        "guardrails": [
            "This package does not authorize execution.",
            "Run at most one grid-convergence pressure comparison after explicit user approval.",
            "Do not run pressure when entry_plan dx_m/model_shape differs from the target acoustic model.",
            "Refresh dx=0.5 model-build and dry-run-quality evidence immediately before execution.",
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
