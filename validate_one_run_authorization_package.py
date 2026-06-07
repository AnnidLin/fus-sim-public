from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
PACKAGE_PATH = PROJECT_ROOT / "outputs/one_run_authorization_package/079_candidate_006/one_run_authorization_package.json"
OUT_JSON = PROJECT_ROOT / "outputs/one_run_authorization_package/079_candidate_006/one_run_authorization_package_validation.json"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8-sig"))
    checks: list[dict[str, Any]] = []
    decision = package.get("decision", {})
    candidates = package.get("candidates", [])
    recommended = package.get("recommended_candidate")
    add(checks, "module", package.get("module") == "one_run_authorization_package", str(package.get("module")))
    add(checks, "package.ready", decision.get("package_ready") is True, str(decision))
    add(checks, "pressure.blocked", decision.get("pressure_execution_allowed_now") is False, str(decision))
    add(checks, "authorization.required", decision.get("requires_explicit_user_authorization") is True, str(decision))
    add(checks, "recommended.exists", isinstance(recommended, dict), str(recommended))
    add(checks, "recommended.one", decision.get("recommended_candidate_id") == recommended.get("candidate_id"), str(decision))
    add(checks, "candidates.nonempty", len(candidates) >= 3, f"count={len(candidates)}")
    not_executed = set(package.get("not_executed", []))
    add(checks, "not_executed.no_pressure", "k-Wave pressure simulation" in not_executed, str(sorted(not_executed)))
    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "one_run_authorization_package_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"one_run_authorization_package_valid": result["one_run_authorization_package_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
