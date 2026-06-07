from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
PROGRAM_PATH = PROJECT_ROOT / "outputs/m2_baseline_hardening_program/m2_baseline_hardening_program.json"
OUT_JSON = PROJECT_ROOT / "outputs/m2_baseline_hardening_program/m2_baseline_hardening_program_validation.json"
OUT_MD = PROJECT_ROOT / "outputs/m2_baseline_hardening_program/m2_baseline_hardening_program_validation.md"

REQUIRED_BLOCKED = {
    "additional pressure execution before CFL/environment gate",
    "paper-grade reproduction claim",
    "validated pressure baseline claim",
    "medical or safety conclusion",
    "source-backed alpha pressure eligibility claim",
    "profile/default promotion",
}


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    program = json.loads(PROGRAM_PATH.read_text(encoding="utf-8-sig"))
    checks: list[dict[str, Any]] = []
    add(checks, "program.version", program.get("program_version") == "1.0.0", str(program.get("program_version")))
    add(checks, "program.module", program.get("module") == "m2_baseline_hardening_program", str(program.get("module")))
    state = program.get("current_state", {})
    add(checks, "state.m2", state.get("maturity_level") == "M2_standard_engineering_baseline_hardening", str(state))
    add(checks, "state.paper_false", state.get("paper_grade_ready") is False, str(state))
    add(checks, "state.profile_false", state.get("profile_promotion_allowed") is False, str(state))
    prereqs = program.get("completed_governance_prerequisites", [])
    valid_prereqs = [item for item in prereqs if item.get("status") == "v1_complete" and item.get("validation", {}).get("valid") is True]
    add(checks, "prereqs.seven_complete", len(valid_prereqs) == 7, f"valid_prereqs={len(valid_prereqs)}")
    target = program.get("next_execution_target", {})
    add(
        checks,
        "target.environment_sensitivity_plan",
        target.get("target_id") == "environment_record_and_numerical_sensitivity_plan",
        str(target),
    )
    add(checks, "target.read_only", target.get("target_type") == "read_only_planning", str(target))
    add(checks, "target.no_pressure", target.get("pressure_execution_allowed") is False, str(target))
    cfl_prereq = [
        item for item in prereqs
        if item.get("name") == "Read-only CFL/environment gate"
        and item.get("status") == "complete"
        and item.get("validation", {}).get("valid") is True
    ]
    add(checks, "prereqs.cfl_environment_complete", len(cfl_prereq) == 1, f"matches={len(cfl_prereq)}")
    blocked = set(program.get("blocked_actions", []))
    add(checks, "blocked.required", REQUIRED_BLOCKED.issubset(blocked), str(sorted(REQUIRED_BLOCKED - blocked)))
    not_executed = set(program.get("not_executed", []))
    add(checks, "not_executed.no_kwave", "k-Wave simulation" in not_executed, str(sorted(not_executed)))
    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "m2_baseline_hardening_program_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# M2 Baseline Hardening Program Validation\n\n"
        f"- valid: `{result['m2_baseline_hardening_program_valid']}`\n"
        f"- failed check count: `{result['failed_check_count']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"m2_baseline_hardening_program_valid": result["m2_baseline_hardening_program_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
