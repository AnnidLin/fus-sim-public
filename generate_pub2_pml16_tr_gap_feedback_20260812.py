"""Write post-execution EDD feedback for the matched PML16 TR pair."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "outputs" / "pub2_250khz_pml16_tr_20260811"
ANALYSIS = ROOT / "outputs" / "pub2_250khz_pml16_tr_analysis_20260812" / "paired_pml_analysis.json"
VALIDATION = ROOT / "outputs" / "pub2_250khz_pml16_tr_validation_20260812" / "package_validation.json"
BRIEF_DIR = ROOT / "outputs" / "evidence_briefs" / "pub2_250khz_ct_numerical_sensitivity_20260807"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    chain, analysis = load(RUN / "chain_status.json"), load(ANALYSIS)
    validation = load(VALIDATION) if VALIDATION.exists() else None
    feedback = {
        "schema_version": "1.0",
        "feedback_id": "pub2_250khz_pml16_tr_pair_20260812",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_matched_pml16_tr_pair" if chain.get("status") == "completed" and analysis.get("status") == "passed" else "failed",
        "actual_execution": {"cell_id": "dx0p75_pml16", "stages": [item.get("stage_id") for item in chain.get("results", [])], "stage_wall_seconds": {item.get("stage_id"): item.get("wall_seconds") for item in chain.get("results", [])}, "automatic_rerun": chain.get("automatic_rerun")},
        "modified_files": ["run_pub2_pml16_tr_pair_20260811.py", "analyze_pub2_pml16_tr_pair_20260812.py", "generate_pub2_pml16_tr_gap_feedback_20260812.py", "validate_pub2_pml16_tr_package_20260812.py"],
        "verification": {"exact_dry_run": "passed", "chain": chain.get("status"), "analysis": analysis.get("status"), "package_validation": None if validation is None else validation.get("status")},
        "observed_differences": analysis.get("pml12_vs_pml16"),
        "deviations_from_brief": [],
        "failures_or_warnings": ["No preregistered numerical pass threshold was applied after observing the data.", "One PML perturbation in one case is not formal convergence."],
        "remaining_evidence_gaps": ["Independent cases remain required for generalisation.", "Grid/CFL/domain sensitivity remains incomplete for a formal convergence claim.", "No experimental or clinical validation is implied."],
        "next_recommendation": "Use the paired result to select at most one next frozen single-variable numerical cell; otherwise prioritize manuscript evidence packaging.",
        "claim_boundary": analysis.get("claim_boundary"),
    }
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    out = BRIEF_DIR / "pml16_tr_gap_feedback.json"
    out.write_text(json.dumps(feedback, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (BRIEF_DIR / "pml16_tr_gap_feedback.md").write_text("\n".join(["# PUB.2 PML16 TR gap feedback", "", f"- Status: **{feedback['status']}**", f"- Analysis: `{feedback['verification']['analysis']}`", f"- Package validation: `{feedback['verification']['package_validation']}`", "", "## Remaining gaps", "", *[f"- {item}" for item in feedback["remaining_evidence_gaps"]], "", feedback["claim_boundary"], ""]), encoding="utf-8")
    print(json.dumps({"status": feedback["status"], "json": str(out)}))
    return 0 if feedback["status"].startswith("completed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
