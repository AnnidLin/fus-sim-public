from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = PROJECT_ROOT / "outputs/profile_preset_run_contract/profile_preset_run_contract.json"
OUT_DIR = PROJECT_ROOT / "outputs/profile_preset_run_contract"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def validate(contract: dict[str, Any], contract_path: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    profile = contract.get("profile", {})
    preset = contract.get("preset", {})
    run = contract.get("run", {})
    separation = contract.get("separation_policy", {})
    claims = contract.get("claim_policy", {})
    target = contract.get("conformance_target", {})

    check(checks, "contract.version", contract.get("contract_version") == "1.0.0", f"contract_version={contract.get('contract_version')}")
    check(checks, "profile.status", profile.get("profile_status") == target.get("expected_profile_status"), f"profile_status={profile.get('profile_status')}")
    check(checks, "profile.not_validated", profile.get("validated_pressure_baseline") is False, f"validated_pressure_baseline={profile.get('validated_pressure_baseline')}")
    check(checks, "profile.no_promotion", profile.get("profile_promotion_allowed") is False and profile.get("default_profile_change_allowed") is False, f"profile_promotion_allowed={profile.get('profile_promotion_allowed')}; default_profile_change_allowed={profile.get('default_profile_change_allowed')}")
    check(checks, "preset.level", preset.get("preset_level") == target.get("expected_preset_level"), f"preset_level={preset.get('preset_level')}")
    check(checks, "preset.not_paper_grade", preset.get("is_paper_grade") is False, f"is_paper_grade={preset.get('is_paper_grade')}")
    check(checks, "run.claim_level", run.get("run_claim_level") == target.get("expected_run_claim_level"), f"run_claim_level={run.get('run_claim_level')}")
    check(checks, "run.completed", run.get("run_completed") is True and run.get("pressure_generated") is True, f"run_completed={run.get('run_completed')}; pressure_generated={run.get('pressure_generated')}")

    required_separation = [
        "profile_success_does_not_upgrade_preset",
        "preset_success_does_not_upgrade_profile",
        "run_success_does_not_upgrade_profile",
        "run_success_does_not_upgrade_paper_grade",
        "paper_grade_requires_separate_gate",
        "profile_promotion_requires_separate_gate",
    ]
    missing_or_false = [key for key in required_separation if separation.get(key) is not True]
    check(checks, "separation.required_rules", not missing_or_false, f"missing_or_false={missing_or_false}")

    blocked = set(claims.get("blocked_claims", []))
    required_blocks = {
        "validated pressure baseline",
        "paper-grade reproduction",
        "medical or safety conclusion",
        "default profile promotion",
        "source-backed alpha pressure eligibility",
    }
    check(checks, "claims.required_blocks", required_blocks.issubset(blocked), f"missing={sorted(required_blocks - blocked)}")
    check(checks, "claims.paper_grade_false", claims.get("paper_grade_ready") is False, f"paper_grade_ready={claims.get('paper_grade_ready')}")
    check(checks, "claims.medical_false", claims.get("medical_or_safety_conclusion_allowed") is False, f"medical_or_safety_conclusion_allowed={claims.get('medical_or_safety_conclusion_allowed')}")

    failed = [item for item in checks if item["status"] != "pass"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contract_path": rel(contract_path),
        "contract_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }


def write_report(result: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "profile_preset_run_conformance.json"
    md_path = OUT_DIR / "profile_preset_run_conformance.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Profile / Preset / Run Conformance",
        "",
        f"- contract valid: `{result['contract_valid']}`",
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
    parser = argparse.ArgumentParser(description="Validate profile/preset/run separation contract.")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    args = parser.parse_args()
    contract_path = Path(args.contract)
    result = validate(read_json(contract_path), contract_path)
    write_report(result)
    print(json.dumps({"contract_valid": result["contract_valid"], "failed_check_count": result["failed_check_count"]}))
    if not result["contract_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
