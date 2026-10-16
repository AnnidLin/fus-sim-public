from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/numerical_sensitivity_planning/079_candidate_006"
BRIEF_DIR = PROJECT_ROOT / "outputs/evidence_briefs/numerical_sensitivity_planning"


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
        "cfl_environment_gate": PROJECT_ROOT / "outputs/cfl_environment_gate/cfl_environment_gate.json",
    }


def build_plan() -> dict[str, Any]:
    inputs = {name: read_json(path) for name, path in input_paths().items()}
    missing = [name for name, payload in inputs.items() if payload is None]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "numerical_sensitivity_planning",
        "scope": "read-only grid/PML/CFL planning index for simple_hu300 079 candidate_006",
        "inputs": {
            "paths": {name: rel(path) for name, path in input_paths().items()},
            "missing": missing,
        },
        "plan_status": {
            "grid_plan": "available" if inputs["grid_plan"] else "missing",
            "pml_plan": "available" if inputs["pml_plan"] else "missing",
            "cfl_plan": "available" if inputs["cfl_plan"] else "missing",
            "cfl_environment_gate": None if inputs["cfl_environment_gate"] is None else inputs["cfl_environment_gate"].get("decision", {}).get("gate_status"),
        },
        "decision": {
            "planning_complete": not missing,
            "pressure_execution_allowed": False,
            "paper_grade_ready": False,
            "recommended_next_action": "Review the three planning legs and choose at most one dry-run-quality or one explicitly authorized comparison run.",
        },
        "recommended_order": [
            "complete environment record fields for future runner outputs",
            "review grid convergence plan and existing dx0.75 dry-run",
            "review PML boundary plan and existing PML12 dry-run",
            "review CFL sensitivity dry-run candidates",
            "request explicit user authorization before exactly one pressure comparison, if justified",
        ],
        "not_executed": [
            "k-Wave pressure simulation",
            "thermal simulation",
            "paper-grade run",
        ],
    }


def markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Numerical Sensitivity Planning",
        "",
        f"- planning complete: `{plan['decision']['planning_complete']}`",
        f"- pressure execution allowed: `{plan['decision']['pressure_execution_allowed']}`",
        f"- paper-grade ready: `{plan['decision']['paper_grade_ready']}`",
        "",
        "## Plan Status",
        "",
    ]
    for key, value in plan["plan_status"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Recommended Order", ""])
    lines.extend(f"- {item}" for item in plan["recommended_order"])
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in plan["not_executed"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    plan = build_plan()
    plan_json = OUT_DIR / "numerical_sensitivity_plan.json"
    plan_md = OUT_DIR / "numerical_sensitivity_plan.md"
    plan_json.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    plan_md.write_text(markdown(plan), encoding="utf-8")
    feedback = {
        "module": "numerical_sensitivity_planning",
        "feedback_type": "post_execution_gap_feedback",
        "outputs": {"plan_json": rel(plan_json), "plan_md": rel(plan_md)},
        "decision": plan["decision"],
        "not_executed": plan["not_executed"],
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "# Gap Feedback: Numerical Sensitivity Planning\n\n"
        f"- planning complete: `{plan['decision']['planning_complete']}`\n"
        f"- pressure execution allowed: `{plan['decision']['pressure_execution_allowed']}`\n"
        "- No k-Wave pressure simulation was executed.\n",
        encoding="utf-8",
    )
    print(f"Wrote {rel(plan_json)}")


if __name__ == "__main__":
    main()
