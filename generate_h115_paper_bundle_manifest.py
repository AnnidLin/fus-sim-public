"""Create a fixed-scope hash manifest for the H115 paper-facing evidence bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED = [
    "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md",
    "paper/PUB2_METHODS_RESULTS_EVIDENCE_20260812.md",
    "paper/UCL_H115_PAPER_READINESS_20260823.md",
    "paper/UCL_H115_VALIDATION_DECISION_BRIEF_ZH_20260826.md",
    "paper/MANUSCRIPT_EVIDENCE_MAP.md",
    "paper/PUB2_REPORTING_CHECKLIST_20260812.md",
    "paper/PUB2_PUBLIC_HYDROPHONE_VALIDATION_FEASIBILITY_20260812.md",
    "paper/H115_REPRODUCTION_RECIPE_20260826.md",
    "paper/H115_REVIEWER_RISK_REGISTER_20260826.md",
    "paper/H115_DELIVERABLES_INDEX_ZH_20260826.md",
    "paper/h115_submission_preflight_20260826/submission_preflight.json",
    "paper/h115_submission_preflight_20260826/submission_preflight.md",
    "paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/figure_manifest.json",
    "paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/figure_ucl_h115_grid_sensitivity.png",
    "paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/figure_ucl_h115_grid_sensitivity.pdf",
    "paper/figures/ucl_h115_source_registration_20260825/figure_manifest.json",
    "paper/figures/ucl_h115_source_registration_20260825/figure_ucl_h115_source_registration.png",
    "paper/figures/ucl_h115_source_registration_20260825/figure_ucl_h115_source_registration.pdf",
    "paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.json",
    "paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.csv",
    "paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.md",
    "paper/tables/ucl_h115_validation_20260826/h115_methods_parameters.json",
    "paper/tables/ucl_h115_validation_20260826/h115_methods_parameters.csv",
    "paper/tables/ucl_h115_validation_20260826/h115_methods_parameters.md",
    "outputs/evidence_briefs/ucl_h115_source_registration_20260825/evidence_brief.json",
    "outputs/evidence_briefs/ucl_h115_source_registration_20260825/validation_contract.json",
    "outputs/evidence_briefs/ucl_h115_source_registration_20260825/gap_feedback.json",
    "outputs/ucl_h115_source_registration_audit_20260825/source_registration_sensitivity.json",
    "outputs/ucl_h115_source_registration_audit_20260825/manuscript_consistency.json",
    "outputs/ucl_h115_source_registration_audit_20260825/package_validation.json",
    "outputs/ucl_h115_recheck_20260826/reproducibility_recheck.json",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> dict:
    files = []
    missing = []
    for relative in EXPECTED:
        path = ROOT / relative
        if not path.is_file():
            missing.append(relative)
            continue
        files.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not missing and len(files) == len(EXPECTED) else "failed",
        "expected_count": len(EXPECTED),
        "file_count": len(files),
        "missing": missing,
        "files": files,
        "excluded_large_artifacts": ["pressure_max_mpa.npz; retained in the execution package validation"],
        "claim_boundary": "Paper-facing traceability only; not successful external validation or formal convergence.",
    }


def markdown(report: dict) -> str:
    lines = [
        "# UCL H115 paper bundle manifest",
        "",
        f'- status: `{report["status"]}`',
        f'- files: `{report["file_count"]}/{report["expected_count"]}`',
        "- large pressure fields: excluded here and retained in the execution package validation",
        "",
        "| Path | Bytes | SHA-256 |",
        "|---|---:|---|",
    ]
    lines.extend(f'| `{item["path"]}` | {item["size_bytes"]} | `{item["sha256"]}` |' for item in report["files"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.output_dir / "manifest.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "file_count": report["file_count"], "missing": report["missing"]}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
