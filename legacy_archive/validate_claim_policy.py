from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
POLICY_PATH = PROJECT_ROOT / "outputs/claim_policy/claim_policy.json"
OUT_JSON = PROJECT_ROOT / "outputs/claim_policy/claim_policy_validation.json"
OUT_MD = PROJECT_ROOT / "outputs/claim_policy/claim_policy_validation.md"

REQUIRED_BLOCKED = {
    "validated pressure baseline",
    "paper-grade reproduction",
    "medical or safety conclusion",
    "source-backed alpha pressure eligibility",
    "default profile promotion",
}
REQUIRED_FALSE_FLAGS = {
    "paper_grade_ready",
    "medical_or_safety_conclusion_allowed",
    "profile_promotion_allowed",
    "default_profile_change_allowed",
    "source_backed_alpha_pressure_eligible",
    "thermal_safety_claim_allowed",
    "validated_pressure_baseline_allowed",
}


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8-sig"))
    checks: list[dict[str, Any]] = []
    add(checks, "policy.version", policy.get("policy_version") == "1.0.0", str(policy.get("policy_version")))
    add(checks, "policy.module", policy.get("module") == "claim_policy", str(policy.get("module")))
    blocked = set(policy.get("blocked_claims", []))
    allowed = set(policy.get("allowed_claims", []))
    add(checks, "blocked.required", REQUIRED_BLOCKED.issubset(blocked), str(sorted(REQUIRED_BLOCKED - blocked)))
    add(checks, "blocked.not_allowed", not (REQUIRED_BLOCKED & allowed), str(sorted(REQUIRED_BLOCKED & allowed)))
    flags = policy.get("claim_flags", {})
    bad_flags = {flag: flags.get(flag) for flag in REQUIRED_FALSE_FLAGS if flags.get(flag) is not False}
    add(checks, "flags.required_false", not bad_flags, str(bad_flags))
    gates = policy.get("gate_snapshot", {})
    add(checks, "gates.paper_grade_blocked", gates.get("paper_grade_gate") == "block", str(gates))
    add(checks, "gates.alpha_blocked", gates.get("alpha_semantics_gate") == "block", str(gates))
    add(checks, "gates.numerical_blocked", gates.get("numerical_quality_gate") == "block", str(gates))
    fields = set(policy.get("required_report_fields", []))
    add(checks, "report_fields.claim_policy", {"allowed_claims", "blocked_claims", "claim_level"}.issubset(fields), str(sorted(fields)))
    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim_policy_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Claim Policy Validation\n\n"
        f"- valid: `{result['claim_policy_valid']}`\n"
        f"- failed check count: `{result['failed_check_count']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"claim_policy_valid": result["claim_policy_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
