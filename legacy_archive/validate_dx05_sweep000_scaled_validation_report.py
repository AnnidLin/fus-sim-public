from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_ROOT / "outputs" / "ct_sweep_scaled_pressure_validation" / "079_sweep_000_dx0p5_p038"
REPORT_JSON = REPORT_DIR / "scaled_pressure_validation.json"
REPORT_MD = REPORT_DIR / "scaled_pressure_validation.md"
OUT_JSON = REPORT_DIR / "scaled_pressure_validation_check.json"
OUT_MD = REPORT_DIR / "scaled_pressure_validation_check.md"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": str(evidence)})


def main() -> None:
    report = json.loads(REPORT_JSON.read_text(encoding="utf-8-sig"))
    markdown = REPORT_MD.read_text(encoding="utf-8-sig")
    checks: list[dict[str, Any]] = []
    decision = report.get("decision", {})
    scaled = report.get("cases", {}).get("scaled_0p38mpa", {})
    report_checks = report.get("checks", {})
    blocked = set(report.get("blocked_claims", []))

    add(checks, "files.present", REPORT_JSON.is_file() and REPORT_MD.is_file(), REPORT_DIR)
    add(
        checks,
        "claim_level.bounded",
        report.get("claim_level") == "scaled_pressure_engineering_validation_not_clinical_safety",
        report.get("claim_level"),
    )
    add(checks, "runner.ok", scaled.get("runner_status") == "kwave_ok", scaled)
    add(
        checks,
        "thermal.local_gates_pass",
        decision.get("scaled_validation_passed_local_thermal_gates") is True
        and scaled.get("overall_safe") is True
        and scaled.get("skull_max_cem43_min", 999.0) < 16.0
        and scaled.get("brain_max_cem43_min", 999.0) < 2.0,
        scaled,
    )
    add(
        checks,
        "scaling.physical_consistency",
        report_checks.get("pressure_scale_matches_source_within_1pct") is True
        and report_checks.get("temperature_scale_matches_power_within_5pct") is True,
        report_checks,
    )
    add(
        checks,
        "not_tuned_focus",
        report_checks.get("target_still_not_tuned_focus") is True,
        report_checks,
    )
    required_blocked = {
        "clinical or medical safety",
        "paper-grade pressure baseline",
        "numerical convergence",
        "tuned focus",
    }
    add(
        checks,
        "claims.boundaries",
        decision.get("clinical_or_medical_safety_conclusion_allowed") is False
        and required_blocked.issubset(blocked),
        sorted(blocked),
    )
    add(
        checks,
        "report.states_engineering_only",
        "not a clinical or medical safety conclusion" in markdown,
        REPORT_MD,
    )

    failed = [item for item in checks if item["status"] == "fail"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# dx0.5 Sweep 000 Scaled Pressure Validation Check",
                "",
                f"- report valid: `{result['report_valid']}`",
                f"- failed check count: `{result['failed_check_count']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"report_valid": result["report_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
