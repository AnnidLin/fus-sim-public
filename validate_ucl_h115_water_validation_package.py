"""Independent artifact validator for the completed UCL H115 water run."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(run_dir: Path, require_grid_sensitivity: bool = False) -> dict:
    execution = read_json(run_dir / "execution_status.json")
    stage = read_json(run_dir / "stage_result.json")
    comparison = read_json(run_dir / "comparison.json")
    required = ["pressure_max_mpa.npz", "summary.json", "focus_metrics.json", "device_history.jsonl"]
    with np.load(run_dir / "pressure_max_mpa.npz") as archive:
        pressure = np.asarray(archive["pressure_max_mpa"], dtype=float)
    samples = [json.loads(line) for line in (run_dir / "device_history.jsonl").read_text(encoding="utf-8").splitlines() if line]
    cpu = [sample["equivalent_cores"] for sample in samples if sample.get("equivalent_cores") is not None]
    working_set = [sample["working_set_gib"] for sample in samples if sample.get("working_set_gib") is not None]
    free_memory = [sample["system_free_memory_gib"] for sample in samples if sample.get("system_free_memory_gib") is not None]
    checks = {
        "required_artifacts_exist": all((run_dir / name).is_file() for name in required),
        "stage_completed_with_zero_return": stage.get("status") == "completed" and stage.get("return_code") == 0,
        "guarded_execution_completed": execution.get("status") == "completed" and execution.get("result", {}).get("stopped_reason") is None,
        "pressure_field_finite_and_nonzero": bool(np.isfinite(pressure).all() and float(np.max(pressure)) > 0.0),
        "device_history_present": bool(samples),
        "cpu_within_6p5_cores": bool(cpu) and max(cpu) <= 6.5,
        "working_set_within_16_gib": bool(working_set) and max(working_set) <= 16.0,
        "free_memory_at_least_4_gib": bool(free_memory) and min(free_memory) >= 4.0,
        "comparison_is_explicitly_nonpassing": comparison.get("status") == "observation_with_failed_preregistered_checks",
        "failed_checks_are_recorded": comparison.get("checks", {}).get("axial_peak_position") is False
        and comparison.get("checks", {}).get("transverse_normalized_l2") is False
        and comparison.get("checks", {}).get("transverse_y_width") is False,
    }
    if require_grid_sensitivity:
        grid_path = run_dir / "grid_sensitivity.json"
        grid = read_json(grid_path) if grid_path.is_file() else {}
        metrics = grid.get("nearfield_excluded_metrics", {})
        checks["grid_sensitivity_complete"] = bool(
            grid.get("status") == "completed_grid_sensitivity_observation"
            and int(metrics.get("common_voxels", 0)) > 0
            and np.isfinite(float(metrics.get("scaled_relative_l2_percent", np.nan)))
        )
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_with_nonpassing_validation_observation" if all(checks.values()) else "failed",
        "checks": checks,
        "device_extrema": {
            "max_equivalent_cores": max(cpu) if cpu else None,
            "max_working_set_gib": max(working_set) if working_set else None,
            "min_system_free_memory_gib": min(free_memory) if free_memory else None,
            "samples": len(samples),
        },
        "claim_boundary": "This validates artifact integrity and guard compliance; it does not convert the nonpassing measurement comparison into acceptance evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-grid-sensitivity", action="store_true")
    args = parser.parse_args()
    result = validate(args.run_dir, require_grid_sensitivity=args.require_grid_sensitivity)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
