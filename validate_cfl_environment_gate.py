from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_GATE = PROJECT_ROOT / "outputs/cfl_environment_gate/cfl_environment_gate.json"
OUT_DIR = PROJECT_ROOT / "outputs/cfl_environment_gate"

ALLOWED_STATUSES = {"pass", "warn", "block"}
REQUIRED_BLOCKED_CLAIMS = {
    "paper-grade reproduction",
    "validated pressure baseline",
    "medical or safety conclusion",
    "source-backed alpha pressure eligibility",
    "profile/default promotion",
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


def validate(gate: dict[str, Any], gate_path: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    decision = gate.get("decision", {})
    quality = gate.get("observed_run_quality", {})
    check_items = gate.get("checks", [])
    blocked_claims = set(gate.get("blocked_claims", []))
    missing_blocks = sorted(REQUIRED_BLOCKED_CLAIMS - blocked_claims)

    add(checks, "gate.version", gate.get("gate_version") == "1.0.0", f"gate_version={gate.get('gate_version')}")
    add(checks, "gate.module", gate.get("module") == "cfl_environment_gate", f"module={gate.get('module')}")
    add(checks, "decision.status_value", decision.get("gate_status") in ALLOWED_STATUSES, f"gate_status={decision.get('gate_status')}")
    add(checks, "decision.no_pressure", decision.get("pressure_execution_allowed") is False, str(decision))
    add(checks, "decision.paper_false", decision.get("paper_grade_ready") is False, str(decision))
    add(checks, "decision.medical_false", decision.get("medical_or_safety_conclusion_allowed") is False, str(decision))
    add(checks, "decision.profile_false", decision.get("profile_promotion_allowed") is False, str(decision))
    add(checks, "quality.preset_standard", quality.get("preset") == "standard", f"preset={quality.get('preset')}")
    add(checks, "quality.cfl_recorded", isinstance(quality.get("cfl"), (int, float)), f"cfl={quality.get('cfl')}")
    add(checks, "quality.pml_recorded", isinstance(quality.get("pml_size"), int), f"pml_size={quality.get('pml_size')}")
    add(checks, "environment.partial_or_complete", decision.get("environment_record_status") in {"partial", "complete"}, str(decision))
    add(checks, "checks.present", len(check_items) >= 8, f"check_count={len(check_items)}")
    add(checks, "claims.required_blocked", not missing_blocks, f"missing_blocked_claims={missing_blocks}")
    not_executed = set(gate.get("not_executed", []))
    add(checks, "not_executed.no_kwave", "k-Wave simulation" in not_executed, str(sorted(not_executed)))
    add(checks, "not_executed.no_thermal", "thermal simulation" in not_executed, str(sorted(not_executed)))

    failed = [item for item in checks if item["status"] != "pass"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_path": rel(gate_path),
        "cfl_environment_gate_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }


def write_report(result: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "cfl_environment_gate_validation.json"
    md_path = OUT_DIR / "cfl_environment_gate_validation.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# CFL / Environment Gate Validation",
        "",
        f"- valid: `{result['cfl_environment_gate_valid']}`",
        f"- failed check count: `{result['failed_check_count']}`",
        "",
        "| Status | Check | Evidence |",
        "|---|---|---|",
    ]
    for item in result["checks"]:
        evidence = str(item["evidence"]).replace("\n", " ")
        if len(evidence) > 180:
            evidence = evidence[:177] + "..."
        lines.append(f"| `{item['status']}` | `{item['check_id']}` | {evidence} |")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the read-only CFL/environment gate.")
    parser.add_argument("--gate", default=str(DEFAULT_GATE))
    args = parser.parse_args()
    gate_path = Path(args.gate)
    result = validate(read_json(gate_path), gate_path)
    write_report(result)
    print(json.dumps({"cfl_environment_gate_valid": result["cfl_environment_gate_valid"], "failed_check_count": result["failed_check_count"]}))
    if not result["cfl_environment_gate_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
