from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "outputs/post_p5_research_gap_review/079_candidate_006/research_gap_review.json"
OUT_JSON = ROOT / "outputs/post_p5_research_gap_review/079_candidate_006/research_gap_review_validation.json"
OUT_MD = ROOT / "outputs/post_p5_research_gap_review/079_candidate_006/research_gap_review_validation.md"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": str(evidence)})


def main() -> None:
    review = json.loads(REVIEW.read_text(encoding="utf-8-sig"))
    checks: list[dict[str, Any]] = []
    obs = review.get("observations", {})
    feas = review.get("dx0p5_feasibility", {})
    decision = review.get("decision", {})
    geom = obs.get("peak_geometry", {})
    add(checks, "review.case", review.get("case_id") == "079", review.get("case_id"))
    add(checks, "evidence.pml_cfl", obs.get("pml16_stable_within_thresholds") is True and obs.get("cfl01_stable_within_thresholds") is True, obs)
    add(checks, "focus.prefocal_axial", geom.get("global_peak", {}).get("axial_shortfall_to_target_mm", 0) > 20 and geom.get("effective_peak", {}).get("axial_shortfall_to_target_mm", 0) > 15, geom)
    add(checks, "dx05.dry_run", feas.get("dry_run_quality_only") is True and feas.get("source_labels") == {"0": 1997}, feas.get("source_labels"))
    add(checks, "dx05.output_no_conflict", feas.get("output_conflict") is False, feas.get("future_output_dir"))
    add(checks, "dx05.hard_stop_not_feasible", feas.get("fits_hard_stop") is False and feas.get("first_order_runtime_estimate_min", 0) > feas.get("hard_stop_min", 0), feas)
    add(checks, "decision.single_no_run_packet", decision.get("recommended_next_packet") == "P6a_focus_metric_semantics_and_prefocal_root_cause_audit" and decision.get("authorization") == "not_required_read_only_no_kwave", decision)
    add(checks, "decision.pressure_blocked", feas.get("pressure_execution_authorized") is False, feas.get("pressure_execution_authorized"))
    blocked = set(review.get("blocked_claims", []))
    add(checks, "claims.bounded", {"numerical convergence", "tuned focus", "clinical or medical safety"}.issubset(blocked), sorted(blocked))
    failed = [item for item in checks if item["status"] == "fail"]
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "review_valid": not failed, "failed_check_count": len(failed), "checks": checks, "failed_checks": failed}
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(f"# Research Gap Review Validation\n\n- review valid: `{result['review_valid']}`\n- failed check count: `{len(failed)}`\n", encoding="utf-8")
    print(json.dumps({"review_valid": result["review_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
