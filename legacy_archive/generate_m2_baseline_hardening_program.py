from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/m2_baseline_hardening_program"
BRIEF_DIR = PROJECT_ROOT / "outputs/evidence_briefs/m2_baseline_hardening_program"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def validation_status(path: str, key: str) -> dict[str, Any]:
    payload = read_json(PROJECT_ROOT / path)
    return {
        "path": path,
        "valid_key": key,
        "valid": payload.get(key) is True,
        "failed_check_count": payload.get("failed_check_count"),
    }


def build_program() -> dict[str, Any]:
    registry = read_json(PROJECT_ROOT / "outputs/evidence_registry/evidence_registry.json")
    maturity = read_json(PROJECT_ROOT / "outputs/maturity_model/maturity_model.json")
    cfl_gate = read_json(PROJECT_ROOT / "outputs/cfl_environment_gate/cfl_environment_gate.json")
    prerequisites = [
        {
            "item": 1,
            "name": "Evidence Registry",
            "status": "v1_complete",
            "validation": validation_status("outputs/evidence_registry/evidence_registry_validation.json", "registry_valid"),
        },
        {
            "item": 2,
            "name": "Profile / preset / run separation",
            "status": "v1_complete",
            "validation": validation_status(
                "outputs/profile_preset_run_contract/profile_preset_run_conformance.json",
                "contract_valid",
            ),
        },
        {
            "item": 3,
            "name": "Gate state machine",
            "status": "v1_complete",
            "validation": validation_status("outputs/gate_state_machine/gate_state_machine_validation.json", "state_machine_valid"),
        },
        {
            "item": 4,
            "name": "Run ledger",
            "status": "v1_complete",
            "validation": validation_status("outputs/run_ledger_validation.json", "ledger_valid"),
        },
        {
            "item": 5,
            "name": "Maturity model",
            "status": "v1_complete",
            "validation": validation_status("outputs/maturity_model/maturity_model_validation.json", "maturity_model_valid"),
        },
        {
            "item": 6,
            "name": "Claim policy",
            "status": "v1_complete",
            "validation": validation_status("outputs/claim_policy/claim_policy_validation.json", "claim_policy_valid"),
        },
        {
            "item": 7,
            "name": "Script/module boundary manifest",
            "status": "v1_complete",
            "validation": validation_status(
                "outputs/module_boundary_manifest/module_boundary_manifest_validation.json",
                "module_boundary_manifest_valid",
            ),
        },
        {
            "item": "M2G2",
            "name": "Read-only CFL/environment gate",
            "status": "complete",
            "validation": validation_status("outputs/cfl_environment_gate/cfl_environment_gate_validation.json", "cfl_environment_gate_valid"),
        },
    ]
    return {
        "program_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "m2_baseline_hardening_program",
        "scope": "hardening program for current simple_hu300 M2 engineering baseline",
        "current_state": {
            "maturity_level": maturity.get("current_level", registry.get("project_maturity_level", {}).get("current")),
            "paper_grade_ready": False,
            "validated_pressure_baseline": False,
            "medical_or_safety_conclusion_allowed": False,
            "profile_promotion_allowed": False,
            "cfl_environment_gate_status": cfl_gate.get("decision", {}).get("gate_status"),
            "environment_record_status": cfl_gate.get("decision", {}).get("environment_record_status"),
        },
        "completed_governance_prerequisites": prerequisites,
        "next_execution_target": {
            "target_id": "environment_record_and_numerical_sensitivity_plan",
            "target_type": "read_only_planning",
            "pressure_execution_allowed": False,
            "description": "Complete environment metadata capture and plan grid/PML/CFL sensitivity before any additional pressure comparison.",
            "success_criteria": [
                "historical and current environment fields are separated",
                "missing environment fields are explicitly tracked",
                "grid/PML/CFL sensitivity plan is read-only and does not batch-run pressure",
                "evidence registry is refreshed",
            ],
        },
        "milestones": [
            {"id": "M2G1", "name": "governance spine complete", "status": "complete"},
            {"id": "M2G2", "name": "read-only CFL/environment gate", "status": "complete"},
            {"id": "M2G3", "name": "environment record and numerical sensitivity planning", "status": "next"},
            {"id": "M2G4", "name": "decide whether one additional comparison run is justified", "status": "blocked_until_M2G3_and_user_authorization"},
            {"id": "M3", "name": "numerical sensitivity package", "status": "blocked"},
            {"id": "M5", "name": "paper-grade candidate", "status": "blocked"},
        ],
        "blocked_actions": [
            "additional pressure execution before CFL/environment gate",
            "paper-grade reproduction claim",
            "validated pressure baseline claim",
            "medical or safety conclusion",
            "source-backed alpha pressure eligibility claim",
            "profile/default promotion",
        ],
        "handoff_rule": [
            "future agents must read EVIDENCE_GOVERNANCE.md and outputs/evidence_registry/evidence_registry.json",
            "future agents must run relevant validators before claiming a governance item is complete",
            "future pressure requires explicit user authorization and runner/dry-run quality gates",
        ],
        "recommended_next_action": "Complete environment record and numerical sensitivity planning; do not run more pressure before explicit authorization.",
        "not_executed": [
            "k-Wave simulation",
            "thermal simulation",
            "paper-grade run",
            "profile/default promotion",
        ],
    }


def markdown(program: dict[str, Any]) -> str:
    lines = [
        "# M2 Baseline Hardening Program",
        "",
        f"- program version: `{program['program_version']}`",
        f"- current maturity: `{program['current_state']['maturity_level']}`",
        f"- next target: `{program['next_execution_target']['target_id']}`",
        f"- pressure execution allowed for next target: `{program['next_execution_target']['pressure_execution_allowed']}`",
        "",
        "## Completed Governance Prerequisites",
        "",
    ]
    for item in program["completed_governance_prerequisites"]:
        lines.append(
            f"- {item['item']}. {item['name']}: `{item['status']}`, "
            f"validation `{item['validation']['valid']}`"
        )
    lines.extend(["", "## Milestones", ""])
    for item in program["milestones"]:
        lines.append(f"- `{item['id']}` {item['name']}: `{item['status']}`")
    lines.extend(["", "## Blocked Actions", ""])
    lines.extend(f"- {item}" for item in program["blocked_actions"])
    lines.extend(["", "## Recommended Next Action", "", f"- {program['recommended_next_action']}", "", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in program["not_executed"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    program = build_program()
    program_path = OUT_DIR / "m2_baseline_hardening_program.json"
    report_path = OUT_DIR / "m2_baseline_hardening_program.md"
    program_path.write_text(json.dumps(program, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(markdown(program), encoding="utf-8")
    feedback = {
        "module": "m2_baseline_hardening_program",
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "defined M2 hardening program",
            "checked governance prerequisites 1-7",
            "kept next target read-only CFL/environment gate",
        ],
        "outputs": {
            "program": rel(program_path),
            "report": rel(report_path),
        },
        "decision": {
            "m2_baseline_hardening_program_status": "v1_complete",
            "current_maturity_level": program["current_state"]["maturity_level"],
            "next_execution_target": program["next_execution_target"]["target_id"],
            "pressure_execution_allowed_for_next_target": False,
        },
        "not_executed": program["not_executed"],
        "recommended_next_step": program["recommended_next_action"],
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "# Gap Feedback: M2 Baseline Hardening Program\n\n"
        "## Decision\n\n"
        "- M2 baseline hardening program status: `v1_complete`\n"
        f"- current maturity level: `{program['current_state']['maturity_level']}`\n"
        f"- next execution target: `{program['next_execution_target']['target_id']}`\n"
        "- pressure execution allowed for next target: `False`\n\n"
        "## Outputs\n\n"
        f"- `{rel(program_path)}`\n"
        f"- `{rel(report_path)}`\n\n"
        "## Not Executed\n\n"
        "- No k-Wave simulation.\n"
        "- No thermal simulation.\n"
        "- No paper-grade run.\n"
        "- No profile/default promotion.\n",
        encoding="utf-8",
    )
    print(f"Wrote {rel(program_path)}")


if __name__ == "__main__":
    main()
