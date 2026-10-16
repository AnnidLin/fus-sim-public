"""Generate post-execution EDD feedback for the PUB.2 PML16 baseline cell."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRIEF_DIR = ROOT / "outputs" / "evidence_briefs" / "pub2_250khz_ct_numerical_sensitivity_20260807"
ANALYSIS = ROOT / "outputs" / "pub2_250khz_pml16_baseline_analysis_20260810" / "pml16_baseline_analysis.json"
RUN = ROOT / "outputs" / "pub2_250khz_pml16_baseline_20260810"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    analysis = load(ANALYSIS)
    result = load(RUN / "stage_result.json")
    monitor = load(RUN / "monitor_status.json")
    validation_path = ROOT / "outputs" / "pub2_250khz_pml16_baseline_validation_20260810" / "package_validation.json"
    validation = load(validation_path) if validation_path.exists() else None
    feedback = {
        "schema_version": "1.0",
        "feedback_id": "pub2_250khz_pml16_baseline_20260810",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_single_pml_baseline_observation" if analysis.get("status") == "passed" and result.get("status") == "completed" else "failed",
        "actual_execution": {
            "cell_id": "dx0p75_pml16", "method": "baseline",
            "changed_factor": "pml_size 12 -> 16",
            "runtime_s": monitor.get("elapsed_s"), "return_code": monitor.get("return_code"),
            "core_outputs_valid": result.get("output_validation", {}).get("status") == "passed",
        },
        "modified_files": [
            "run_pub2_pml16_baseline_20260810.py",
            "analyze_pub2_pml16_baseline_20260810.py",
            "generate_pub2_pml16_gap_feedback_20260810.py",
            "validate_pub2_pml16_baseline_package_20260810.py",
        ],
        "verification": {
            "runner_preflight": "passed",
            "solver_monitor": monitor.get("status"),
            "analysis": analysis.get("status"),
            "package_validation": None if validation is None else validation.get("status"),
        },
        "observed_difference": analysis.get("common_domain_field_difference"),
        "deviations_from_brief": [],
        "failures_or_warnings": [
            "This is one baseline PML perturbation only; no TR/PML16 result was run.",
            "No preregistered numerical pass threshold was applied after observing the data.",
        ],
        "remaining_evidence_gaps": [
            "TR PML sensitivity remains unexecuted.",
            "Grid, CFL and domain cells remain unexecuted in PUB.2.",
            "A single PML perturbation is not formal convergence.",
        ],
        "next_recommendation": "Stop pressure execution at the user-authorized two-run boundary; review results before any additional matrix cell.",
        "claim_boundary": analysis.get("claim_boundary"),
    }
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    out = BRIEF_DIR / "pml16_baseline_gap_feedback.json"
    out.write_text(json.dumps(feedback, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# PUB.2 PML16 baseline gap feedback", "",
        f"- Status: **{feedback['status']}**",
        f"- Runtime: `{feedback['actual_execution']['runtime_s']}` s",
        f"- Analysis: `{feedback['verification']['analysis']}`",
        f"- Package validation: `{feedback['verification']['package_validation']}`",
        "", "## Remaining gaps", "",
        *[f"- {item}" for item in feedback["remaining_evidence_gaps"]],
        "", feedback["claim_boundary"], "",
    ]
    (BRIEF_DIR / "pml16_baseline_gap_feedback.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"status": feedback["status"], "json": str(out)}))
    return 0 if feedback["status"].startswith("completed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
