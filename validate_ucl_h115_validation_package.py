"""Validate the UCL H115 measurement summary and water-only dry-run package."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


EXPECTED_SHA256 = "0275af014151ca972c0c7799af2735e345554c460f797f217bd8ceb4f3dfa0ad"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_npz(path: Path, expected_points: int) -> dict[str, object]:
    require(path.exists(), f"missing {path}")
    with np.load(path) as data:
        required = {"coordinates_m", "pressure_amplitude_pa", "pressure_phase_rad", "normalized_amplitude"}
        require(required <= set(data.files), f"{path} missing arrays {sorted(required - set(data.files))}")
        coordinates = np.asarray(data["coordinates_m"])
        pressure = np.asarray(data["pressure_amplitude_pa"])
        normalized = np.asarray(data["normalized_amplitude"])
        require(coordinates.shape == (expected_points, 3), f"unexpected coordinates shape {coordinates.shape}")
        require(pressure.shape == (expected_points,), f"unexpected pressure shape {pressure.shape}")
        require(np.isfinite(coordinates).all(), "coordinates are non-finite")
        require(np.isfinite(pressure).all() and np.all(pressure >= 0), "pressure amplitude is invalid")
        require(np.isfinite(normalized).all(), "normalized amplitude is non-finite")
        require(abs(float(normalized.max()) - 1.0) < 1e-12, "normalized map maximum is not one")
        return {"path": str(path), "points": expected_points, "peak_pressure_pa": float(pressure.max())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--dryrun-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    summary = json.loads((args.measurement_dir / "summary.json").read_text(encoding="utf-8"))
    require(summary["status"] == "completed", "measurement summary is not completed")
    require(summary["input"]["sha256"] == EXPECTED_SHA256, "measurement input hash drift")
    require(summary["artifact_checks"]["input_integrity"] == "pass", "input integrity did not pass")
    require(summary["artifact_checks"]["all_pressure_amplitudes_finite_and_nonnegative"] == "pass", "pressure check did not pass")
    require(summary["axial_qcw"]["minus6db_axial_width_mm"] is None, "censored axial width must remain null")
    require(summary["axial_qcw"]["minus6db_axial_width_status"] == "left_censored", "axial censoring state drift")

    transverse = validate_npz(args.measurement_dir / "qcw_transverse_map.npz", 7921)
    axial = validate_npz(args.measurement_dir / "qcw_axial_profile.npz", 121)

    model_manifest = json.loads((args.model_dir / "model_manifest.json").read_text(encoding="utf-8"))
    require(model_manifest["status"] == "generated_for_dry_run_only", "model scope drift")
    require(model_manifest["ppw_at_270khz"] >= 8.0, "model PPW is below the brief's stop condition")
    require((args.model_dir / "acoustic_model_3d.npz").exists(), "water model is missing")
    require((args.model_dir / "entry_plan.json").exists(), "water entry plan is missing")

    dryrun = json.loads((args.dryrun_dir / "quality_dry_run_summary.json").read_text(encoding="utf-8"))
    require(dryrun["dry_run_quality_only"] is True, "quality artifact is not dry-run only")
    require(dryrun["simulation_quality"]["ppw_min_sound_speed"] >= 8.0, "dry-run PPW is too low")
    require(dryrun["simulation_quality"]["memory_estimate"]["estimated_mb"] < 16 * 1024, "dry-run memory estimate exceeds gate")
    require(not (args.dryrun_dir / "pressure_max_mpa.npz").exists(), "dry-run unexpectedly contains a pressure field")
    contract = json.loads((args.dryrun_dir / "validation_contract.json").read_text(encoding="utf-8"))
    require(contract["status"] == "preregistered_before_pressure_simulation", "comparison contract was not preregistered")

    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "checks": {
            "measurement_summary": "pass",
            "transverse_npz": transverse,
            "axial_npz": axial,
            "water_model_contract": "pass",
            "papergrade_dryrun_only": "pass",
            "comparison_contract_preregistered": "pass",
        },
        "paper_grade_blockers": dryrun["simulation_quality"]["paper_grade_blockers"],
        "claim_boundary": "package integrity pass does not mean paper-grade simulation validation",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
