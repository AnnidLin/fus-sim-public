"""Validate the completed H115 source-model/registration evidence package."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(
    run_dir: Path,
    audit_dir: Path,
    brief_dir: Path,
    figure_dir: Path,
    manuscript_consistency: Path | None = None,
) -> dict:
    execution = read_json(run_dir / "execution_status.json")
    stage = read_json(run_dir / "stage_result.json")
    nominal = read_json(run_dir / "comparison.json")
    effective = read_json(audit_dir / "effective_dx0p5_coordinate_audit.json")
    sensitivity = read_json(audit_dir / "source_registration_sensitivity.json")
    brief = read_json(brief_dir / "evidence_brief.json")
    contract = read_json(brief_dir / "validation_contract.json")
    gap = read_json(brief_dir / "gap_feedback.json")
    figure_manifest = read_json(figure_dir / "figure_manifest.json")

    with np.load(run_dir / "pressure_max_mpa.npz") as archive:
        pressure = np.asarray(archive["pressure_max_mpa"], dtype=float)
    samples = [json.loads(line) for line in (run_dir / "device_history.jsonl").read_text(encoding="utf-8").splitlines() if line]
    cpu = [float(sample["equivalent_cores"]) for sample in samples if sample.get("equivalent_cores") is not None]
    working_set = [float(sample["working_set_gib"]) for sample in samples if sample.get("working_set_gib") is not None]
    free_memory = [float(sample["system_free_memory_gib"]) for sample in samples if sample.get("system_free_memory_gib") is not None]
    png = Path(figure_manifest["outputs"]["png"]["path"])
    pdf = Path(figure_manifest["outputs"]["pdf"]["path"])
    effective_checks = effective.get("checks", {})
    nominal_checks = nominal.get("checks", {})
    checks = {
        "brief_authorized_before_run": brief.get("status") == "authorized_pending_exact_dry_run_and_device_gate",
        "contract_frozen_before_run": contract.get("status") == "frozen_before_candidate_propagation",
        "dry_run_passed": read_json(run_dir / "exact_dry_run_report.json").get("status") == "passed",
        "single_run_completed": stage.get("status") == "completed" and stage.get("return_code") == 0,
        "guarded_execution_completed": execution.get("status") == "completed" and execution.get("result", {}).get("stopped_reason") is None,
        "pressure_finite_nonzero": bool(np.isfinite(pressure).all() and float(np.max(pressure)) > 0),
        "device_samples_present": bool(samples),
        "cpu_within_6p5_cores": bool(cpu) and max(cpu) <= 6.5,
        "working_set_within_16_gib": bool(working_set) and max(working_set) <= 16.0,
        "free_memory_at_least_4_gib": bool(free_memory) and min(free_memory) >= 4.0,
        "effective_correction_preserves_two_true_failures": effective_checks.get("axial_peak_position") is False and effective_checks.get("transverse_normalized_l2") is False,
        "effective_width_bug_is_corrected": effective_checks.get("transverse_x_width") is True and effective_checks.get("transverse_y_width") is True,
        "nominal_candidate_explicitly_nonpassing": nominal.get("status") == "observation_with_failed_preregistered_checks" and nominal_checks and not any(nominal_checks.values()),
        "source_geometry_materially_explanatory": sensitivity.get("source_geometry_materially_explanatory") is True and all(sensitivity.get("material_explanation_checks", {}).values()),
        "secondary_arms_do_not_replace_primary": all(not value["registration_summary"]["primary_result_replaced"] for value in sensitivity.get("simulations", {}).values()),
        "gap_feedback_closes_solver_scope": gap.get("additional_solver_authorized") is False,
        "figure_png_hash_matches": png.is_file() and sha256(png) == figure_manifest["outputs"]["png"]["sha256"],
        "figure_pdf_hash_matches": pdf.is_file() and sha256(pdf) == figure_manifest["outputs"]["pdf"]["sha256"],
    }
    if manuscript_consistency is not None:
        consistency = read_json(manuscript_consistency)
        checks["manuscript_consistency_passed"] = consistency.get("status") == "passed" and not consistency.get("failed_checks")
    artifacts = [
        run_dir / "pressure_max_mpa.npz",
        run_dir / "summary.json",
        run_dir / "focus_metrics.json",
        run_dir / "comparison.json",
        audit_dir / "effective_dx0p5_coordinate_audit.json",
        audit_dir / "effective_dx0p3_coordinate_audit.json",
        audit_dir / "source_registration_sensitivity.json",
        brief_dir / "evidence_brief.json",
        brief_dir / "validation_contract.json",
        brief_dir / "gap_feedback.json",
        png,
        pdf,
    ]
    if manuscript_consistency is not None:
        artifacts.append(manuscript_consistency)
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_with_nonpassing_external_validation" if all(checks.values()) else "failed",
        "checks": checks,
        "device_extrema": {
            "max_equivalent_cores": max(cpu) if cpu else None,
            "max_working_set_gib": max(working_set) if working_set else None,
            "min_system_free_memory_gib": min(free_memory) if free_memory else None,
            "samples": len(samples),
        },
        "artifact_sha256": {str(path): sha256(path) for path in artifacts if path.is_file()},
        "claim_boundary": "Package integrity and sensitivity closure pass; the primary external comparison remains nonpassing.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--brief-dir", type=Path, required=True)
    parser.add_argument("--figure-dir", type=Path, required=True)
    parser.add_argument("--manuscript-consistency", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.run_dir, args.audit_dir, args.brief_dir, args.figure_dir, args.manuscript_consistency)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
