from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
AUDIT_PATH = ROOT / "outputs/p6a_focus_metric_semantics_audit/079_candidate_006_dx0p75/focus_metric_semantics_audit.json"
OUT_JSON = ROOT / "outputs/p6a_focus_metric_semantics_audit/079_candidate_006_dx0p75/focus_metric_semantics_audit_validation.json"
OUT_MD = ROOT / "outputs/p6a_focus_metric_semantics_audit/079_candidate_006_dx0p75/focus_metric_semantics_audit_validation.md"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": str(evidence)})


def main() -> None:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8-sig"))
    metrics = audit.get("metrics", {})
    decision = audit.get("decision", {})
    checks: list[dict[str, Any]] = []
    add(checks, "audit.case", audit.get("case_id") == "079", audit.get("case_id"))
    add(checks, "audit.no_kwave", audit.get("no_kwave_execution") is True, audit.get("no_kwave_execution"))
    add(checks, "legacy.preserved", audit.get("legacy_regression", {}).get("all_preserved") is True, audit.get("legacy_regression"))
    add(checks, "semantics.version", metrics.get("metric_semantics_version") == "2.0.0", metrics.get("metric_semantics_version"))
    add(checks, "beam_axis.global_peak_retained", metrics.get("beam_axis_effective_peak_index_ijk") == metrics.get("global_peak_index_ijk"), metrics.get("beam_axis_effective_peak_index_ijk"))
    add(checks, "post_entry.prefocal", metrics.get("post_entry_peak_axial_shortfall_to_target_mm", 0) > 20, metrics.get("post_entry_peak_axial_shortfall_to_target_mm"))
    add(checks, "target_window.near_target", abs(metrics.get("target_window_peak_axial_shortfall_to_target_mm", 99)) < 5, metrics.get("target_window_peak_axial_shortfall_to_target_mm"))
    add(checks, "decision.next", decision.get("recommended_next_packet") == "P6b_post_skull_beam_axis_profile_and_interface_audit" and decision.get("authorization") == "not_required_read_only_no_kwave", decision)
    add(checks, "decision.pressure_blocked", decision.get("pressure_execution_authorized") is False, decision.get("pressure_execution_authorized"))
    blocked = set(audit.get("blocked_claims", []))
    add(checks, "claims.bounded", {"tuned focus", "numerical convergence", "clinical or medical safety"}.issubset(blocked), sorted(blocked))
    failed = [item for item in checks if item["status"] == "fail"]
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "audit_valid": not failed, "failed_check_count": len(failed), "checks": checks, "failed_checks": failed}
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(f"# P6a Audit Validation\n\n- audit valid: `{result['audit_valid']}`\n- failed check count: `{len(failed)}`\n", encoding="utf-8")
    print(json.dumps({"audit_valid": result["audit_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
