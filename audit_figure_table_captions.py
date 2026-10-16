"""Audit manuscript figure/table captions against retained artifact semantics."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(root: Path) -> dict:
    text = (root / "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md").read_text(encoding="utf-8-sig")
    main = load(root / "paper/figures/pub2_20260812/figure_manifest.json")
    grid = load(root / "paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/figure_manifest.json")
    source = load(root / "paper/figures/ucl_h115_source_registration_20260825/figure_manifest.json")
    endpoints = load(root / "paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.json")
    methods = load(root / "paper/tables/ucl_h115_validation_20260826/h115_methods_parameters.json")
    checks = {
        "figure2_projection_and_coordinates_disclosed": all(token in text for token in ("Maximum projections", "along the k/z dimension", "physical coordinates relative to the frozen target", "does not represent a single anatomical slice")),
        "figure2_pressure_definition_matches_manifest": "temporal peak pressure magnitude" in text and main["pressure_definition"].startswith("max(abs(p_max), abs(p_min))"),
        "figure2_shared_scale_disclosed": "same 0–3.962-MPa scale" in text,
        "figure3_endpoint_definitions_disclosed": all(token in text for token in ("target divided by the global pressure maximum", "Euclidean distance from the global pressure maximum to the target", "no population-level error bars")),
        "figure4_signed_difference_and_alignment_disclosed": all(token in text for token in ("Signed PML16-minus-PML12", "maximum absolute difference along k/z", "stored full-model crop origins", "same symmetric colour scale")),
        "figure4_blocks_formal_convergence": "tests one PML perturbation only and does not establish formal numerical convergence" in text,
        "supplementary_grid_caption_matches_boundary": "two grids do not establish formal convergence" in text and "not formal convergence" in grid["claim_boundary"],
        "supplementary_source_caption_marks_secondary_arms": all(token in text for token in ("shifted arms do not replace the unshifted primary result", "not complex-pressure aperture deconvolution")) and "secondary only" in source["claim_boundary"],
        "endpoint_table_caption_retains_nonpassing_verdict": endpoints.get("row_count") == 24 and "Passing package-integrity checks do not replace the nonpassing external-validation verdict" in text,
        "methods_table_caption_retains_non_paper_grade": len(methods.get("rows", [])) == 3 and all(row.get("is_paper_grade") is False for row in methods["rows"]) and "remain explicitly non-paper-grade in machine metadata" in text,
        "all_five_manifests_passed_or_bounded": endpoints.get("status") == "passed" and methods.get("status") == "passed" and all(item.get("claim_boundary") for item in (main, grid, source)),
    }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": "TRACE-20260829-001",
        "status": "passed_caption_semantics" if all(checks.values()) else "failed",
        "submission_ready": False,
        "artifact_group_count": 5,
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "Caption-to-manifest agreement supports traceability only; it is not physical validation or submission authorization.",
    }


def render(report: dict) -> str:
    lines = ["# Figure/table caption semantics audit", "", f"Status: `{report['status']}`  ", f"Artifact groups: `{report['artifact_group_count']}`", "", "## Checks", ""]
    lines += [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()]
    lines += ["", report["claim_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "caption_semantics_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "caption_semantics_audit.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed_checks"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
