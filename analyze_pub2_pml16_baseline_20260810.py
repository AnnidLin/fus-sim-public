"""Compare the PUB.2 PML12 and PML16 baseline fields on their common domain."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807" / "baseline"
CANDIDATE = ROOT / "outputs" / "pub2_250khz_pml16_baseline_20260810"
OUTPUT = ROOT / "outputs" / "pub2_250khz_pml16_baseline_analysis_20260810"
CONFIG_KEYS = (
    "model_path", "entry_plan_path", "frequency_hz", "source_pressure_pa",
    "transducer_radius_m", "aperture_diameter_m", "tone_burst_cycles", "cfl",
    "simulation_time_s", "pml_size", "preset", "backend", "device",
    "quick_mode", "quick_lateral_half_width_m", "quick_post_target_margin_m",
    "alpha_power", "nearfield_exclusion_m", "record_target_waveform",
    "allow_entry_plan_resolution_mismatch",
)
METRIC_KEYS = (
    "global_peak_mpa", "target_pressure_mpa", "target_window_peak_mpa",
    "target_to_global_peak_ratio", "global_peak_to_target_distance_mm",
    "effective_peak_mpa", "effective_peak_to_target_distance_mm",
    "target_to_effective_peak_ratio",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_field(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as archive:
        return {
            "field": np.asarray(archive["pressure_max_mpa"], dtype=np.float32),
            "origin": np.asarray(archive["crop_origin_ijk"], dtype=np.int64),
            "target": np.asarray(archive["target_index_ijk"], dtype=np.int64),
            "dx_m": float(np.asarray(archive["dx_m"])),
            "source_points": int(np.asarray(archive["source_mask"]).sum()),
        }


def common_views(reference: dict[str, Any], candidate: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    ref_field = reference["field"]
    cand_field = candidate["field"]
    ref_origin = reference["origin"]
    cand_origin = candidate["origin"]
    start = np.maximum(ref_origin, cand_origin)
    stop = np.minimum(ref_origin + np.array(ref_field.shape), cand_origin + np.array(cand_field.shape))
    if np.any(stop <= start):
        raise ValueError("PML12 and PML16 domains do not overlap")
    ref_start = start - ref_origin
    cand_start = start - cand_origin
    shape = stop - start
    ref_slices = tuple(slice(int(x), int(x + n)) for x, n in zip(ref_start, shape))
    cand_slices = tuple(slice(int(x), int(x + n)) for x, n in zip(cand_start, shape))
    return ref_field[ref_slices], cand_field[cand_slices], {
        "full_model_start_ijk": start.tolist(),
        "full_model_stop_exclusive_ijk": stop.tolist(),
        "shape": shape.tolist(),
        "reference_slices_start_ijk": ref_start.tolist(),
        "candidate_slices_start_ijk": cand_start.tolist(),
    }


def compare_configs(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    values = {}
    mismatches = []
    for key in CONFIG_KEYS:
        left, right = reference.get(key), candidate.get(key)
        equal = left == right
        values[key] = {"pml12": left, "pml16": right, "equal": equal}
        if not equal:
            mismatches.append(key)
    return {
        "fields": values,
        "mismatches": mismatches,
        "only_pml_size_changed": mismatches == ["pml_size"] and reference.get("pml_size") == 12 and candidate.get("pml_size") == 16,
    }


def build_report() -> dict[str, Any]:
    ref_summary = load_json(REFERENCE / "summary.json")
    cand_summary = load_json(CANDIDATE / "summary.json")
    ref_metrics = load_json(REFERENCE / "focus_metrics.json")
    cand_metrics = load_json(CANDIDATE / "focus_metrics.json")
    execution = load_json(CANDIDATE / "execution_status.json")
    monitor = load_json(CANDIDATE / "monitor_status.json")
    reference = load_field(REFERENCE / "pressure_max_mpa.npz")
    candidate = load_field(CANDIDATE / "pressure_max_mpa.npz")
    ref_view, cand_view, alignment = common_views(reference, candidate)
    difference = cand_view.astype(np.float64) - ref_view.astype(np.float64)
    ref_norm = float(np.linalg.norm(ref_view.astype(np.float64).ravel()))
    diff_norm = float(np.linalg.norm(difference.ravel()))
    max_ref = float(np.max(np.abs(ref_view)))
    config = compare_configs(ref_summary["config"], cand_summary["config"])
    scalar = {}
    for key in METRIC_KEYS:
        left = float(ref_metrics[key])
        right = float(cand_metrics[key])
        delta = right - left
        scalar[key] = {
            "pml12": left, "pml16": right, "difference": delta,
            "relative_difference": None if left == 0 else delta / abs(left),
        }
    full_target_ref = (reference["origin"] + reference["target"]).tolist()
    full_target_cand = (candidate["origin"] + candidate["target"]).tolist()
    checks = {
        "execution_completed": execution.get("status") == "completed",
        "monitor_completed": monitor.get("status") == "completed" and monitor.get("return_code") == 0,
        "only_pml_size_changed": config["only_pml_size_changed"],
        "dx_equal": reference["dx_m"] == candidate["dx_m"],
        "full_target_equal": full_target_ref == full_target_cand,
        "source_points_equal_4971": reference["source_points"] == candidate["source_points"] == 4971,
        "reference_domain_fully_covered": alignment["shape"] == list(reference["field"].shape),
        "common_fields_finite_nonzero": bool(np.isfinite(ref_view).all() and np.isfinite(cand_view).all() and np.max(cand_view) > 0),
    }
    return {
        "schema_version": "1.0",
        "report_id": "pub2_250khz_pml16_baseline_analysis_20260810",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "claim_level": "single_case_single_variable_boundary_sensitivity_observation",
        "checks": checks,
        "configuration": config,
        "coordinate_alignment": {
            **alignment,
            "reference_shape": list(reference["field"].shape),
            "candidate_shape": list(candidate["field"].shape),
            "reference_origin_ijk": reference["origin"].tolist(),
            "candidate_origin_ijk": candidate["origin"].tolist(),
            "full_target_reference_ijk": full_target_ref,
            "full_target_candidate_ijk": full_target_cand,
        },
        "common_domain_field_difference": {
            "relative_l2": None if ref_norm == 0 else diff_norm / ref_norm,
            "relative_linf": None if max_ref == 0 else float(np.max(np.abs(difference))) / max_ref,
            "max_absolute_difference_mpa": float(np.max(np.abs(difference))),
            "mean_absolute_difference_mpa": float(np.mean(np.abs(difference))),
        },
        "scalar_metrics": scalar,
        "runtime_s": {
            "pml12": float(ref_summary["runtime"]["runtime_s"]),
            "pml16": float(cand_summary["runtime"]["runtime_s"]),
        },
        "artifacts": {
            "reference_field": {"path": str((REFERENCE / "pressure_max_mpa.npz").relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(REFERENCE / "pressure_max_mpa.npz")},
            "candidate_field": {"path": str((CANDIDATE / "pressure_max_mpa.npz").relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(CANDIDATE / "pressure_max_mpa.npz")},
        },
        "decision": {
            "pml16_baseline_cell_complete": all(checks.values()),
            "formal_convergence_established": False,
            "automatic_additional_cells_authorized": False,
        },
        "claim_boundary": "One Case079 baseline PML12-versus-PML16 observation on the aligned common domain; no formal convergence, TR sensitivity, efficacy or safety claim.",
    }


def main() -> int:
    report = build_report()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "pml16_baseline_analysis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    field = report["common_domain_field_difference"]
    metrics = report["scalar_metrics"]
    lines = [
        "# PUB.2 PML16 baseline sensitivity analysis", "",
        f"- Status: **{report['status']}**", "- Changed factor: PML 12 → 16 only",
        f"- Common-domain relative L2: `{field['relative_l2']:.8g}`",
        f"- Common-domain relative L∞: `{field['relative_linf']:.8g}`",
        f"- Global peak relative change: `{metrics['global_peak_mpa']['relative_difference']:.8g}`",
        f"- Target pressure relative change: `{metrics['target_pressure_mpa']['relative_difference']:.8g}`",
        "", report["claim_boundary"], "",
    ]
    (OUTPUT / "pml16_baseline_analysis.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "json": str(OUTPUT / "pml16_baseline_analysis.json")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
