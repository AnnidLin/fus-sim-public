from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
LEDGER_PATH = PROJECT_ROOT / "outputs" / "run_ledger.jsonl"
OUT_JSON = PROJECT_ROOT / "outputs" / "run_ledger_validation.json"
OUT_MD = PROJECT_ROOT / "outputs" / "run_ledger_validation.md"


REQUIRED_BLOCKED = {"validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion"}


def read_entries() -> list[dict[str, Any]]:
    return [json.loads(line) for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    entries = read_entries()
    checks: list[dict[str, Any]] = []
    add(checks, "ledger.exists", LEDGER_PATH.exists(), str(LEDGER_PATH))
    add(checks, "ledger.entry_count", len(entries) >= 1, f"entry_count={len(entries)}")
    run_ids = [item.get("run_id") for item in entries]
    add(checks, "ledger.unique_run_ids", len(run_ids) == len(set(run_ids)), f"run_ids={run_ids}")
    standard = [item for item in entries if item.get("claim_level") == "standard_engineering_pressure_output"]
    add(checks, "ledger.standard_run_present", bool(standard), f"standard_count={len(standard)}")
    unauthorized = [item.get("run_id") for item in entries if not item.get("authorization")]
    add(checks, "ledger.authorization_present", not unauthorized, f"missing_authorization={unauthorized}")
    bad_claims = [item.get("run_id") for item in entries if item.get("claim_level") in {"paper_grade_candidate", "medical_or_safety_conclusion"}]
    add(checks, "ledger.no_upgraded_claims", not bad_claims, f"bad_claim_runs={bad_claims}")
    missing_blocks = [
        item.get("run_id") for item in entries
        if not REQUIRED_BLOCKED.issubset(set(item.get("blocked_claims", [])))
    ]
    add(checks, "ledger.required_blocked_claims", not missing_blocks, f"missing_blocks={missing_blocks}")
    missing_outputs = [
        item.get("run_id") for item in entries
        if item.get("pressure_generated") and not (PROJECT_ROOT / item.get("pressure_path", "")).exists()
    ]
    add(checks, "ledger.pressure_paths_exist", not missing_outputs, f"missing_outputs={missing_outputs}")
    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Run Ledger Validation\n\n"
        f"- ledger valid: `{result['ledger_valid']}`\n"
        f"- failed check count: `{result['failed_check_count']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"ledger_valid": result["ledger_valid"], "failed_check_count": result["failed_check_count"]}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
