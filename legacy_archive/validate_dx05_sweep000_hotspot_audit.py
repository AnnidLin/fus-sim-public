from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
AUDIT_DIR = PROJECT_ROOT / "outputs" / "ct_sweep_hotspot_audit" / "079_sweep_000_dx0p5"
AUDIT_JSON = AUDIT_DIR / "hotspot_audit.json"
AUDIT_MD = AUDIT_DIR / "hotspot_audit.md"
AXIS_CSV = AUDIT_DIR / "beam_axis_profile.csv"
OUT_JSON = AUDIT_DIR / "hotspot_audit_validation.json"
OUT_MD = AUDIT_DIR / "hotspot_audit_validation.md"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": str(evidence)})


def main() -> None:
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8-sig"))
    markdown = AUDIT_MD.read_text(encoding="utf-8-sig")
    checks: list[dict[str, Any]] = []
    hotspots = {item.get("name"): item for item in audit.get("hotspots", [])}
    scaling = audit.get("source_pressure_scaling", {})
    threshold = scaling.get("safe_threshold_estimate", {})
    blocked = set(audit.get("blocked_claims", []))

    add(checks, "files.present", AUDIT_JSON.is_file() and AUDIT_MD.is_file() and AXIS_CSV.is_file(), AUDIT_DIR)
    add(
        checks,
        "claim_level.bounded",
        audit.get("claim_level") == "hotspot_localization_and_source_pressure_screening_not_validation",
        audit.get("claim_level"),
    )
    add(
        checks,
        "hotspot.skull_localized",
        audit.get("decision", {}).get("hotspot_material") == "skull_bone"
        and hotspots.get("pressure_global_peak", {}).get("material") == "skull_bone"
        and hotspots.get("cem43_peak", {}).get("material") == "skull_bone",
        audit.get("decision", {}),
    )
    add(
        checks,
        "target.not_hotspot",
        audit.get("decision", {}).get("target_is_hotspot") is False
        and hotspots.get("target", {}).get("distance_to_target_mm") == 0.0,
        hotspots.get("target"),
    )
    add(
        checks,
        "scaling.screening_only",
        scaling.get("claim_level") == "screening_estimate_not_thermal_validation"
        and audit.get("decision", {}).get("rerun_required_for_scaled_safety_claim") is True,
        scaling,
    )
    add(
        checks,
        "scaling.threshold_plausible",
        0.0 < float(threshold.get("source_pressure_mpa", 0.0)) < float(scaling.get("current_source_pressure_mpa", 0.0)),
        threshold,
    )
    required_blocked = {
        "numerical convergence",
        "validated source-pressure safety threshold",
        "clinical or medical safety",
        "paper-grade pressure baseline",
    }
    add(checks, "claims.blocked", required_blocked.issubset(blocked), sorted(blocked))
    add(
        checks,
        "report.states_not_validation",
        "not for declaring safety" in markdown and "does not establish numerical convergence" in markdown,
        AUDIT_MD,
    )

    failed = [item for item in checks if item["status"] == "fail"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# dx0.5 Sweep 000 Hotspot Audit Validation",
                "",
                f"- audit valid: `{result['audit_valid']}`",
                f"- failed check count: `{result['failed_check_count']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"audit_valid": result["audit_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
