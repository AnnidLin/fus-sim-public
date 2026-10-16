from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
PLAN_PATH = PROJECT_ROOT / "outputs/simple_hu300_ct_cfl_sensitivity_plan/079_candidate_006_dx0p75_pml12/ct_cfl_sensitivity_plan.json"
OUT_JSON = PROJECT_ROOT / "outputs/simple_hu300_ct_cfl_sensitivity_plan/079_candidate_006_dx0p75_pml12/ct_cfl_sensitivity_plan_validation.json"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8-sig"))
    checks: list[dict[str, Any]] = []
    decision = plan.get("decision", {})
    candidates = plan.get("candidates", [])
    add(checks, "module", plan.get("module") == "ct_cfl_sensitivity_plan", str(plan.get("module")))
    add(checks, "plan.ready", decision.get("plan_ready") is True, str(decision))
    add(checks, "pressure.blocked", decision.get("pressure_run_allowed") is False, str(decision))
    add(checks, "paper.false", decision.get("paper_grade_ready") is False, str(decision))
    add(checks, "candidates.three", len(candidates) == 3, f"count={len(candidates)}")
    add(checks, "baseline.cfl", plan.get("baseline", {}).get("cfl") == 0.2, str(plan.get("baseline")))
    not_executed = set(plan.get("not_executed", []))
    add(checks, "not_executed.no_pressure", "k-Wave pressure simulation" in not_executed, str(sorted(not_executed)))
    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ct_cfl_sensitivity_plan_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ct_cfl_sensitivity_plan_valid": result["ct_cfl_sensitivity_plan_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
