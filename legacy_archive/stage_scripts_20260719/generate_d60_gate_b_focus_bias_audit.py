from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


COARSE = Path("outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run/summary.json")
FINE = Path("outputs/freefield_aperture_calibration/d60_dx0p5_fieldonly_20260713/run/summary.json")
COMPARISON = Path("outputs/freefield_aperture_calibration/d60_grid_convergence_20260713/d60_grid_convergence_report.json")
OUTPUT = Path("outputs/freefield_aperture_calibration/d60_gate_b_focus_bias_audit_20260714")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def summarize_geometry(summary: dict[str, Any], refined: dict[str, Any]) -> dict[str, Any]:
    dx_mm = float(summary["dx_m"]) * 1e3
    source = np.asarray(summary["source"]["source_center_index_ijk"], dtype=float)
    target = np.asarray(summary["target_index_ijk"], dtype=float)
    beam = target - source
    target_distance_mm = float(np.linalg.norm(beam) * dx_mm)
    radius_gp = int(summary["source"]["radius_grid_points"])
    diameter_gp = int(summary["source"]["diameter_grid_points"])
    effective_radius_mm = radius_gp * dx_mm
    requested_radius_mm = float(summary["config"]["transducer_radius_m"]) * 1e3
    rounded_sphere_center = source + np.rint(radius_gp * beam / np.linalg.norm(beam))
    refined_axial_mm = float(refined["refined_focus_axial_from_source_mm"])
    source_points = int(summary["source"]["source_points"])
    return {
        "dx_mm": dx_mm,
        "source_center_index_ijk": source.astype(int).tolist(),
        "target_index_ijk": target.astype(int).tolist(),
        "target_distance_mm": target_distance_mm,
        "requested_radius_mm": requested_radius_mm,
        "radius_grid_points": radius_gp,
        "effective_radius_mm": effective_radius_mm,
        "radius_rounding_error_mm": effective_radius_mm - requested_radius_mm,
        "diameter_grid_points": diameter_gp,
        "effective_diameter_mm": (diameter_gp - 1) * dx_mm,
        "source_points": source_points,
        "source_surface_area_proxy_mm2": source_points * dx_mm**2,
        "rounded_sphere_center_index_ijk": rounded_sphere_center.astype(int).tolist(),
        "sphere_center_to_target_error_mm": float(np.linalg.norm(rounded_sphere_center - target) * dx_mm),
        "refined_focus_axial_from_source_mm": refined_axial_mm,
        "refined_shortfall_from_grid_target_mm": target_distance_mm - refined_axial_mm,
        "refined_shortfall_from_requested_radius_mm": requested_radius_mm - refined_axial_mm,
        "refined_error_vs_requested_radius_percent": (requested_radius_mm - refined_axial_mm) / requested_radius_mm * 100.0,
        "refined_error_vs_effective_radius_percent": (effective_radius_mm - refined_axial_mm) / effective_radius_mm * 100.0,
    }


def build_audit(coarse_summary: dict[str, Any], fine_summary: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    coarse = summarize_geometry(coarse_summary, comparison["dx0p75"])
    fine = summarize_geometry(fine_summary, comparison["dx0p5"])
    aperture_mm = float(fine_summary["config"]["aperture_diameter_m"]) * 1e3
    aperture_area_mm2 = math.pi * (aperture_mm / 2.0) ** 2
    for item in (coarse, fine):
        item["source_surface_area_proxy_error_percent"] = (
            (item["source_surface_area_proxy_mm2"] - aperture_area_mm2) / aperture_area_mm2 * 100.0
        )

    grid = [int(v) for v in fine_summary["model_shape"]]
    nt = int(fine_summary["runtime"]["nt"])
    full_history_bytes = math.prod(grid) * nt * 8
    common_shortfall_delta = (
        fine["refined_shortfall_from_requested_radius_mm"]
        - coarse["refined_shortfall_from_requested_radius_mm"]
    )
    candidate_mm = fine["requested_radius_mm"] + fine["refined_shortfall_from_requested_radius_mm"]
    return {
        "status": "diagnosis_complete_no_pressure_run",
        "coarse_dx0p75": coarse,
        "fine_dx0p5": fine,
        "cross_grid": {
            "target_distance_delta_fine_minus_coarse_mm": fine["target_distance_mm"] - coarse["target_distance_mm"],
            "refined_focus_axial_delta_fine_minus_coarse_mm": fine["refined_focus_axial_from_source_mm"] - coarse["refined_focus_axial_from_source_mm"],
            "residual_shortfall_delta_common_radius_mm": common_shortfall_delta,
            "reported_refined_focal_displacement_mm": comparison["comparison"]["focal_displacement_mm"],
            "global_peak_change_percent": comparison["comparison"]["global_peak_change_percent"],
            "lateral_width_change_percent": comparison["comparison"]["lateral_width_change_percent"],
            "axial_width_change_percent": comparison["comparison"]["axial_width_change_percent"],
            "source_area_proxy_change_percent": (fine["source_surface_area_proxy_mm2"] - coarse["source_surface_area_proxy_mm2"]) / fine["source_surface_area_proxy_mm2"] * 100.0,
        },
        "sensor_memory": {
            "grid_shape": grid,
            "nt": nt,
            "full_domain_float64_history_gib": full_history_bytes / 2**30,
            "target_only_float64_history_kib": nt * 8 / 2**10,
            "root_cause": "One kSensor mask applies to every record; adding p to a full-domain p_max/p_min sensor requests the complete voxel-time history.",
            "recommended_architecture": "Keep the full-domain run field-only; use a separate target-only run or backend support for a distinct point sensor.",
        },
        "hypotheses": {
            "sphere_center_quantization": {"finding": "excluded_as_primary_cause", "evidence": "Rounded sphere center equals the target on both grids."},
            "independent_target_distance_rounding": {"finding": "minor_contributor", "evidence_mm": fine["target_distance_mm"] - coarse["target_distance_mm"]},
            "source_surface_rasterization": {"finding": "supported_contributor_not_isolated"},
            "finite_aperture_proximal_shift": {"finding": "supported_but_not_separated_from_rasterization"},
            "field_instability": {"finding": "not_supported"},
        },
        "decision": {
            "ct_pressure_authorized": False,
            "more_long_runs_now": False,
            "current_absolute_focus_gate_interpretation": "Keep target accuracy as a source-calibration gate, but do not label it a pure grid-convergence failure.",
            "single_corrected_radius_candidate_mm": candidate_mm,
            "candidate_semantics": "First-order compensation equal to the fine-grid proximal shortfall; planning only.",
            "next_run_sequence": [
                "one dx0.75 corrected-radius confirmation",
                "one dx0.5 confirmation only if dx0.75 absolute error is <=4%",
                "no CT pressure until both source-calibration and cross-grid gates pass",
            ],
        },
    }


def render_markdown(audit: dict[str, Any]) -> str:
    c, f, x = audit["coarse_dx0p75"], audit["fine_dx0p5"], audit["cross_grid"]
    m, d = audit["sensor_memory"], audit["decision"]
    return f"""# D60 Gate B Focus-Bias Audit

## Decision

Gate B remains closed and CT pressure remains blocked. The result is a **source-calibration failure with otherwise stable cross-grid field metrics**, not a broad field-convergence failure. No pressure simulation was run for this audit.

## Geometry reconstruction

| Metric | dx0.75 | dx0.5 |
|---|---:|---:|
| Source-target distance (mm) | {c['target_distance_mm']:.6f} | {f['target_distance_mm']:.6f} |
| Requested curvature radius (mm) | {c['requested_radius_mm']:.6f} | {f['requested_radius_mm']:.6f} |
| Effective integer-grid radius (mm) | {c['effective_radius_mm']:.6f} | {f['effective_radius_mm']:.6f} |
| Sphere-center-to-target error (mm) | {c['sphere_center_to_target_error_mm']:.6f} | {f['sphere_center_to_target_error_mm']:.6f} |
| Source area proxy error (%) | {c['source_surface_area_proxy_error_percent']:.3f} | {f['source_surface_area_proxy_error_percent']:.3f} |
| Refined focus axial position (mm) | {c['refined_focus_axial_from_source_mm']:.6f} | {f['refined_focus_axial_from_source_mm']:.6f} |
| Error vs common requested radius (%) | {c['refined_error_vs_requested_radius_percent']:.3f} | {f['refined_error_vs_requested_radius_percent']:.3f} |

The local `make_bowl` sphere center lands exactly on the target for both grids. Independent grid rounding changes source-target distance by {x['target_distance_delta_fine_minus_coarse_mm']:.3f} mm, so it is only a minor contributor.

## Field interpretation

- Refined focal displacement: {x['reported_refined_focal_displacement_mm']:.3f} mm.
- Global peak change: {x['global_peak_change_percent']:.3f}%.
- Lateral / axial -6 dB width change: {x['lateral_width_change_percent']:.3f}% / {x['axial_width_change_percent']:.3f}%.
- Residual refined axial-focus change in a common-radius frame: {x['residual_shortfall_delta_common_radius_mm']:.3f} mm.

This supports a proximal finite-aperture focus shift plus grid-dependent source rasterization. It does not support an unstable pressure field.

## Waveform memory

The failed full-domain waveform request implied {m['full_domain_float64_history_gib']:.2f} GiB for `{m['grid_shape']}` x `{m['nt']}` float64 samples; a target-only history is {m['target_only_float64_history_kib']:.2f} KiB. Keep full-domain recording field-only and obtain a waveform only through a separate target-only run or a backend change.

## Highest-efficiency next step

Use exactly one planning candidate, `R={d['single_corrected_radius_candidate_mm']:.3f} mm`, from the fine-grid proximal shortfall. It is not yet validated.

1. One dx0.75 corrected-radius confirmation after a new Evidence Brief and dry-run.
2. Require <=4% absolute target error before dx0.5.
3. One dx0.5 confirmation only after that margin.
4. No CT pressure until source calibration and cross-grid checks both pass.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coarse-summary", type=Path, default=COARSE)
    parser.add_argument("--fine-summary", type=Path, default=FINE)
    parser.add_argument("--comparison", type=Path, default=COMPARISON)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    audit = build_audit(load_json(args.coarse_summary), load_json(args.fine_summary), load_json(args.comparison))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "d60_gate_b_focus_bias_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "d60_gate_b_focus_bias_audit.md").write_text(render_markdown(audit), encoding="utf-8")


if __name__ == "__main__":
    main()
