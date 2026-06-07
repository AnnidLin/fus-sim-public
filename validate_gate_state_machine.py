from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MACHINE = PROJECT_ROOT / "outputs/gate_state_machine/gate_state_machine.json"
OUT_DIR = PROJECT_ROOT / "outputs/gate_state_machine"

REQUIRED_GATES = {
    "mapping_profile_gate",
    "alpha_semantics_gate",
    "pressure_execution_gate",
    "numerical_quality_gate",
    "interpretation_gate",
    "paper_grade_gate",
}
ALLOWED_STATUSES = {"pass", "warn", "block"}
EXPECTED_STATUS = {
    "mapping_profile_gate": "warn",
    "alpha_semantics_gate": "block",
    "pressure_execution_gate": "pass",
    "numerical_quality_gate": "block",
    "interpretation_gate": "warn",
    "paper_grade_gate": "block",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def validate(machine: dict[str, Any], machine_path: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    gates = machine.get("gates", {})
    missing = sorted(REQUIRED_GATES - set(gates))
    extra = sorted(set(gates) - REQUIRED_GATES)
    add(checks, "machine.version", machine.get("state_machine_version") == "1.0.0", f"version={machine.get('state_machine_version')}")
    add(checks, "gates.required", not missing and not extra, f"missing={missing}; extra={extra}")

    bad_status = {
        gate: payload.get("status")
        for gate, payload in gates.items()
        if not isinstance(payload, dict) or payload.get("status") not in ALLOWED_STATUSES
    }
    add(checks, "gates.status_values", not bad_status, f"bad_status={bad_status}")

    mismatched = {
        gate: gates.get(gate, {}).get("status")
        for gate, expected in EXPECTED_STATUS.items()
        if gates.get(gate, {}).get("status") != expected
    }
    add(checks, "gates.expected_current_status", not mismatched, f"mismatched={mismatched}")

    missing_next = [gate for gate, payload in gates.items() if not isinstance(payload, dict) or not payload.get("next_action")]
    add(checks, "gates.next_action", not missing_next, f"missing_next={missing_next}")

    missing_blocks = [
        gate for gate, payload in gates.items()
        if gate in {"alpha_semantics_gate", "numerical_quality_gate", "paper_grade_gate"} and not payload.get("blocks")
    ]
    add(checks, "gates.block_lists", not missing_blocks, f"missing_blocks={missing_blocks}")

    policy = machine.get("transition_policy", {})
    add(
        checks,
        "transition.no_run_upgrade",
        policy.get("run_success_cannot_upgrade_profile") is True
        and policy.get("run_success_cannot_upgrade_paper_grade") is True,
        f"run_success_cannot_upgrade_profile={policy.get('run_success_cannot_upgrade_profile')}; run_success_cannot_upgrade_paper_grade={policy.get('run_success_cannot_upgrade_paper_grade')}",
    )
    add(
        checks,
        "transition.paper_grade_requires_all_gates",
        policy.get("paper_grade_requires_all_gates_pass") is True,
        f"paper_grade_requires_all_gates_pass={policy.get('paper_grade_requires_all_gates_pass')}",
    )

    locks = machine.get("global_locks", {})
    add(checks, "locks.paper_grade_false", locks.get("paper_grade_ready") is False, f"paper_grade_ready={locks.get('paper_grade_ready')}")
    add(
        checks,
        "locks.medical_false",
        locks.get("medical_or_safety_conclusion_allowed") is False,
        f"medical_or_safety_conclusion_allowed={locks.get('medical_or_safety_conclusion_allowed')}",
    )
    add(
        checks,
        "locks.profile_false",
        locks.get("profile_promotion_allowed") is False and locks.get("default_profile_change_allowed") is False,
        f"profile_promotion_allowed={locks.get('profile_promotion_allowed')}; default_profile_change_allowed={locks.get('default_profile_change_allowed')}",
    )
    add(
        checks,
        "next_gate.cfl_environment",
        machine.get("recommended_next_gate") == "cfl_environment_gate",
        f"recommended_next_gate={machine.get('recommended_next_gate')}",
    )

    failed = [item for item in checks if item["status"] != "pass"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "machine_path": rel(machine_path),
        "state_machine_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }


def write_report(result: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "gate_state_machine_validation.json"
    md_path = OUT_DIR / "gate_state_machine_validation.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Gate State Machine Validation",
        "",
        f"- state machine valid: `{result['state_machine_valid']}`",
        f"- failed check count: `{result['failed_check_count']}`",
        "",
        "| Status | Check | Evidence |",
        "|---|---|---|",
    ]
    for item in result["checks"]:
        lines.append(f"| `{item['status']}` | `{item['check_id']}` | {item['evidence']} |")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the fus-sim gate state machine.")
    parser.add_argument("--machine", default=str(DEFAULT_MACHINE))
    args = parser.parse_args()
    machine_path = Path(args.machine)
    result = validate(read_json(machine_path), machine_path)
    write_report(result)
    print(json.dumps({"state_machine_valid": result["state_machine_valid"], "failed_check_count": result["failed_check_count"]}))
    if not result["state_machine_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
