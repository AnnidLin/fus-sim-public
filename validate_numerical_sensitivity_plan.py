from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
PLAN_PATH = PROJECT_ROOT / "outputs/numerical_sensitivity_planning/079_candidate_006/numerical_sensitivity_plan.json"
OUT_JSON = PROJECT_ROOT / "outputs/numerical_sensitivity_planning/079_candidate_006/numerical_sensitivity_plan_validation.json"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8-sig"))
    checks: list[dict[str, Any]] = []
    status = plan.get("plan_status", {})
    decision = plan.get("decision", {})
    add(checks, "module", plan.get("module") == "numerical_sensitivity_planning", str(plan.get("module")))
    add(checks, "grid.available", status.get("grid_plan") == "available", str(status))
    add(checks, "pml.available", status.get("pml_plan") == "available", str(status))
    add(checks, "cfl.available", status.get("cfl_plan") == "available", str(status))
    add(checks, "pressure.blocked", decision.get("pressure_execution_allowed") is False, str(decision))
    add(checks, "paper.false", decision.get("paper_grade_ready") is False, str(decision))
    not_executed = set(plan.get("not_executed", []))
    add(checks, "not_executed.no_pressure", "k-Wave pressure simulation" in not_executed, str(sorted(not_executed)))
    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "numerical_sensitivity_plan_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"numerical_sensitivity_plan_valid": result["numerical_sensitivity_plan_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
