from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("outputs/paper_skeleton_20260715")

# Authoritative source data files (already existing, no new simulation).
CLOSEOUT_JSON = Path("outputs/acoustic_stage_closeout_20260714/d60_acoustic_stage_closeout.json")
CONFIRMATION_JSON = Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_confirmation_20260714/d60_r78p330_confirmation_report.json")
GRID_CONV_JSON = Path("outputs/freefield_aperture_calibration/d60_grid_convergence_corrected_20260716/d60_grid_convergence_report.json")
CALIBRATION_JSON = Path("outputs/freefield_current_tuned_calibration/ap30_r35_f500_dx0p75_pml12_standard/free_field_calibration_summary.json")
SOURCE_FIGURE = Path("outputs/acoustic_stage_closeout_20260714/d60_source_correction_figure.png")
SOURCE_METRICS_CSV = Path("outputs/acoustic_stage_closeout_20260714/d60_source_correction_metrics.csv")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_assets(figures_dir: Path) -> dict[str, str]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    copied_figure = figures_dir / "figure_1_source_correction.png"
    if SOURCE_FIGURE.is_file():
        shutil.copy2(SOURCE_FIGURE, copied_figure)
    copied_csv = figures_dir / "source_correction_metrics.csv"
    if SOURCE_METRICS_CSV.is_file():
        shutil.copy2(SOURCE_METRICS_CSV, copied_csv)
    return {
        "figure_1_png": copied_figure.relative_to(OUTPUT_DIR).as_posix(),
        "source_metrics_csv": copied_csv.relative_to(OUTPUT_DIR).as_posix(),
    }


def build_parameter_table(closeout: dict[str, Any], calibration: dict[str, Any]) -> list[dict[str, str]]:
    baseline = closeout["baseline_r74p435_dx0p75"]
    corrected = closeout["corrected_r78p330_dx0p75"]
    return [
        {"category": "Transducer", "parameter": "Frequency", "value": "500 kHz", "source": "fixed baseline"},
        {"category": "Transducer", "parameter": "Aperture diameter", "value": "60.0 mm", "source": "D60 source"},
        {"category": "Transducer", "parameter": "Nominal radius of curvature", "value": "74.435 mm (baseline) / 78.330 mm (corrected)", "source": "Gate B calibration"},
        {"category": "Transducer", "parameter": "F-number", "value": "1.24 (baseline) / 1.31 (corrected)", "source": "computed from aperture/radius"},
        {"category": "Transducer", "parameter": "Source pressure convention", "value": "1.0 MPa", "source": "Gao 2022 seed protocol"},
        {"category": "Transducer", "parameter": "Source model", "value": "geometric bowl (k-Wave makeBowl)", "source": "simulate_kwave_3d_focus.py"},
        {"category": "Solver", "parameter": "Solver", "value": "k-Wave (k-space pseudospectral)", "source": "Treeby 2010"},
        {"category": "Solver", "parameter": "Grid spacing", "value": "0.75 mm", "source": "dx0.75 standard"},
        {"category": "Solver", "parameter": "Grid shape", "value": f"{baseline['grid_shape'][0]}x{baseline['grid_shape'][1]}x{baseline['grid_shape'][2]}", "source": "closeout JSON"},
        {"category": "Solver", "parameter": "PPW (water, 500 kHz)", "value": "4.0", "source": "computed"},
        {"category": "Solver", "parameter": "PML size", "value": "12 voxels (9.0 mm)", "source": "closeout JSON"},
        {"category": "Solver", "parameter": "CFL", "value": "0.2", "source": "closeout JSON"},
        {"category": "Solver", "parameter": "Backend", "value": "CPU / Python k-wave-python 0.6.1", "source": "environment record"},
        {"category": "Current tuned (legacy)", "parameter": "Aperture / radius", "value": "30 mm / 35 mm", "source": "calibration JSON"},
        {"category": "Current tuned (legacy)", "parameter": "Free-field target-window peak", "value": f"{calibration['pressure']['target_window_peak_mpa']:.3f} MPa", "source": "calibration JSON"},
    ]


def build_results_table(closeout: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = closeout["baseline_r74p435_dx0p75"]
    corrected = closeout["corrected_r78p330_dx0p75"]
    rows = [
        {
            "metric": "Global peak pressure",
            "baseline_r74p435": f"{baseline['global_peak_mpa']:.3f} MPa",
            "corrected_r78p330": f"{corrected['global_peak_mpa']:.3f} MPa",
            "change": f"{closeout['changes']['global_peak_percent']:+.2f}%",
        },
        {
            "metric": "Target pressure",
            "baseline_r74p435": f"{baseline['target_pressure_mpa']:.3f} MPa",
            "corrected_r78p330": f"{corrected['target_pressure_mpa']:.3f} MPa",
            "change": f"{closeout['changes']['target_pressure_percent']:+.2f}%",
        },
        {
            "metric": "Target/global peak ratio",
            "baseline_r74p435": f"{baseline['target_to_global_peak_ratio']:.4f}",
            "corrected_r78p330": f"{corrected['target_to_global_peak_ratio']:.4f}",
            "change": f"{closeout['changes']['target_to_global_percentage_points']:+.4f}",
        },
        {
            "metric": "Refined focus error",
            "baseline_r74p435": f"{baseline['refined_focus_error_mm']:.3f} mm ({baseline['refined_focus_error_percent']:.3f}%)",
            "corrected_r78p330": f"{corrected['refined_focus_error_mm']:.3f} mm ({corrected['refined_focus_error_percent']:.3f}%)",
            "change": f"{closeout['changes']['refined_focus_error_percentage_points']:+.3f} pp",
        },
        {
            "metric": "Lateral -6 dB width",
            "baseline_r74p435": f"{baseline['minus6db_lateral_equivalent_mm']:.3f} mm",
            "corrected_r78p330": f"{corrected['minus6db_lateral_equivalent_mm']:.3f} mm",
            "change": f"{closeout['changes']['lateral_width_percent']:+.2f}%",
        },
        {
            "metric": "Axial -6 dB width",
            "baseline_r74p435": f"{baseline['minus6db_axial_width_mm']:.3f} mm",
            "corrected_r78p330": f"{corrected['minus6db_axial_width_mm']:.3f} mm",
            "change": f"{closeout['changes']['axial_width_percent']:+.2f}%",
        },
        {
            "metric": "Boundary distance",
            "baseline_r74p435": f"{baseline['global_boundary_distance_voxels']} voxels",
            "corrected_r78p330": f"{corrected['global_boundary_distance_voxels']} voxels",
            "change": "—",
        },
    ]
    return rows


def write_tables(parameter_table: list[dict[str, str]], results_table: list[dict[str, Any]], tables_dir: Path) -> dict[str, str]:
    tables_dir.mkdir(parents=True, exist_ok=True)

    param_path = tables_dir / "table_1_parameters.csv"
    with param_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "parameter", "value", "source"])
        writer.writeheader()
        writer.writerows(parameter_table)

    results_path = tables_dir / "table_2_results.csv"
    with results_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "baseline_r74p435", "corrected_r78p330", "change"])
        writer.writeheader()
        writer.writerows(results_table)

    return {
        "table_1_parameters_csv": param_path.relative_to(OUTPUT_DIR).as_posix(),
        "table_2_results_csv": results_path.relative_to(OUTPUT_DIR).as_posix(),
    }


def write_skeleton_report(
    closeout: dict[str, Any],
    confirmation: dict[str, Any],
    grid_conv: dict[str, Any],
    calibration: dict[str, Any],
    paths: dict[str, str],
    output_path: Path,
) -> None:
    baseline = closeout["baseline_r74p435_dx0p75"]
    corrected = closeout["corrected_r78p330_dx0p75"]
    dx05 = grid_conv["dx0p5"]
    dx05_err = float(dx05["refined_focus_error_percent"])
    gate_b_pass = str(grid_conv.get("status", "")) == "gate_b_dx075_dx05_pass"
    waveform_ok = bool(grid_conv.get("waveform_complete"))
    if gate_b_pass:
        abstract_limitations_grid = (
            f"Grid convergence at dx = 0.5 mm passed the preregistered 5% focus-error gate "
            f"(observed {dx05_err:.3f}%) with the complete target waveform recorded via a low-memory "
            f"point-sensor architecture; convergence is established at the engineering level only."
        )
        discussion_grid_point = (
            f"5. Cross-grid check: the dx0.5 point-waveform run passed the preregistered focus-error "
            f"gate (refined focus error {dx05_err:.3f}%) and recorded the complete target waveform "
            f"with a low-memory point-sensor architecture. dx0.75/dx0.5 convergence is established "
            f"at the engineering level; dx0.375 and PML/CFL sensitivity remain open."
        )
        limitations_grid_point = (
            f"3. **Grid convergence engineering-level only**: dx0.5 passed the ≤5% focus-error gate "
            f"(observed {dx05_err:.3f}%) with target waveform recorded; dx0.375 and PML/CFL "
            f"sensitivity remain open."
        )
    elif waveform_ok:
        abstract_limitations_grid = (
            f"Grid convergence at dx = 0.5 mm recorded the complete target waveform but failed the "
            f"preregistered 5% focus-error gate (observed {dx05_err:.3f}%)."
        )
        discussion_grid_point = (
            f"5. Cross-grid check: the dx0.5 point-waveform run recorded the complete target waveform "
            f"but refined focus error was {dx05_err:.3f}% (fails ≤5% gate). Therefore dx0.75/dx0.5 "
            f"convergence is not established."
        )
        limitations_grid_point = (
            f"3. **Grid convergence incomplete**: dx0.5 failed the ≤5% focus-error gate "
            f"(observed {dx05_err:.3f}%) despite the recorded target waveform."
        )
    else:
        abstract_limitations_grid = (
            "Grid convergence at dx = 0.5 mm failed the preregistered 5% focus-error gate because "
            "the complete target waveform was not recorded (full-domain history would require "
            "~110 GiB)."
        )
        discussion_grid_point = (
            f"5. Cross-grid check: dx0.5 run showed refined focus error {dx05_err:.3f}% and the "
            f"target waveform could not be recorded due to ~110 GiB memory demand. Therefore "
            f"dx0.75/dx0.5 convergence is not established."
        )
        limitations_grid_point = (
            "3. **Grid convergence incomplete**: dx0.5 failed the ≤5% focus-error gate and lacks "
            "target waveform."
        )
    text = f"""# Manuscript Skeleton: Acoustic-Field-First Engineering Baseline

> Date: 2026-07-15
> Status: P2 paper skeleton and results package
> Scope: Free-field source calibration for a single-case, patient-specific tFUS simulation-methods study
> Claim level: engineering validation only; no clinical safety, paper-grade convergence, or transcranial efficacy claims

## Suggested title

Source-geometry calibration of a 60-mm aperture, 500 kHz focused ultrasound transducer in homogeneous free field for patient-specific transcranial simulation

## Abstract (structured draft)

**Background**: Patient-specific transcranial focused ultrasound (tFUS) simulation requires a reproducible source model before transcranial pressure claims can be interpreted. Current literature often reports transcranial pressures without a calibrated source-to-free-field chain.

**Objective**: Calibrate a geometric bowl source (60-mm aperture, 500 kHz) in homogeneous free field and quantify the effect of first-order curvature correction on focal position accuracy.

**Methods**: We used the k-Wave k-space pseudospectral solver with a 0.75-mm grid (PPW = 4), PML = 12 voxels, and CFL = 0.2. A nominal radius of curvature of 74.435 mm was compared against a corrected radius of 78.330 mm. Focus metrics included refined focal-position error, target-to-global peak-pressure ratio, and -6 dB axial/lateral widths.

**Results**: The corrected radius reduced refined focal error from {baseline['refined_focus_error_percent']:.3f}% to {corrected['refined_focus_error_percent']:.3f}% and increased target/global ratio from {baseline['target_to_global_peak_ratio']:.4f} to {corrected['target_to_global_peak_ratio']:.4f}. Global peak pressure decreased by {abs(closeout['changes']['global_peak_percent']):.2f}%; lateral -6 dB width changed by {closeout['changes']['lateral_width_percent']:+.2f}%. The corrected field and target waveform were finite, with the global peak 27 voxels from the boundary.

**Limitations**: These results are homogeneous free-field evidence only. {abstract_limitations_grid} No transcranial pressure, thermal, or clinical claims are supported.

**Conclusion**: First-order curvature correction improves free-field focal calibration for the D60 source. Before transcranial interpretation, the source must pass cross-grid convergence and be tested on true skull-crossing trajectories.

## Introduction (bullet outline)

1. tFUS neuromodulation simulation depends on accurate source representation.
2. Geometric bowl sources are common but their focal position can deviate from nominal curvature due to grid rasterization and finite aperture.
3. Reference works (Pasquinelli 2020, Chen 2023) emphasize free-field transducer calibration before transcranial comparison.
4. Current gap: many studies jump to CT pressure without explicit source calibration.
5. Working question: Can a simple curvature correction bring a geometric D60 bowl source into focal alignment in free field?

## Methods (draft)

### Transducer model

- Geometric bowl source generated with k-Wave `makeBowl`.
- Aperture diameter: 60.0 mm.
- Nominal radius of curvature: 74.435 mm (baseline) and 78.330 mm (corrected).
- Source pressure convention: 1.0 MPa (Gao 2022 seed protocol).
- Frequency: 500 kHz.

### Numerical solver

- k-Wave k-space pseudospectral method (Treeby 2010), Python backend v0.6.1.
- Grid spacing: 0.75 mm (PPW = 4 in water at 500 kHz).
- Grid shape: {baseline['grid_shape'][0]} x {baseline['grid_shape'][1]} x {baseline['grid_shape'][2]} voxels.
- PML: 12 voxels (9.0 mm thickness).
- CFL: 0.2.
- Medium: homogeneous water (c = 1500 m/s, ρ = 1000 kg/m³, α = 0).
- Runtime: ~{baseline['runtime_s'] / 60:.1f} min (baseline) and ~{corrected['runtime_s'] / 60:.1f} min (corrected).

### Metrics

- Refined focal-position error: sub-voxel parabolic refinement of axial pressure maximum relative to geometric target distance ({baseline['target_distance_mm']:.3f} mm).
- Target-to-global peak-pressure ratio.
- -6 dB axial and lateral widths through the global peak.
- Boundary distance of global peak in voxels.
- Target waveform recorded at geometric focus (1,000 samples).

## Results (draft)

In homogeneous free-field simulations, increasing the nominal radius of curvature from 74.435 mm to 78.330 mm shifted the refined axial pressure maximum from {baseline['refined_focus_axial_from_source_mm']:.3f} mm to {corrected['refined_focus_axial_from_source_mm']:.3f} mm from the source centre. The refined focal-position error decreased from {baseline['refined_focus_error_percent']:.3f}% to {corrected['refined_focus_error_percent']:.3f}% ({closeout['changes']['refined_focus_error_percentage_points']:+.3f} percentage points), passing the preregistered ≤4% gate. The target-to-global peak-pressure ratio increased from {baseline['target_to_global_peak_ratio']:.4f} to {corrected['target_to_global_peak_ratio']:.4f}. The global peak pressure changed from {baseline['global_peak_mpa']:.3f} MPa to {corrected['global_peak_mpa']:.3f} MPa ({closeout['changes']['global_peak_percent']:+.2f}%), and the equivalent lateral -6 dB width changed from {baseline['minus6db_lateral_equivalent_mm']:.3f} mm to {corrected['minus6db_lateral_equivalent_mm']:.3f} mm ({closeout['changes']['lateral_width_percent']:+.2f}%). The corrected field remained finite and the global peak was {corrected['global_boundary_distance_voxels']} voxels from the nearest boundary.

See Table 2 and Figure 1 for the full metric comparison.

## Figure 1

- **File**: `{paths['figure_1_png']}`
- **Caption**: Free-field source calibration of a 60-mm aperture, 500 kHz bowl transducer in homogeneous water. (a) Baseline nominal radius 74.435 mm; (b) corrected nominal radius 78.330 mm. The geometric target is marked with a cyan cross. (c) Beam-axis peak-pressure profiles. (d) Prespecified calibration metrics: refined focal-position error and target-to-global peak-pressure ratio. The corrected radius reduced focal error from 3.555% to 1.364% and increased target/global ratio from 0.982 to 0.991.
- **Reproducibility**: Values are traceable to `{paths['source_metrics_csv']}`.

## Tables

- **Table 1**: Simulation and source parameters → `{paths['table_1_parameters_csv']}`
- **Table 2**: Free-field calibration metrics, baseline vs corrected → `{paths['table_2_results_csv']}`

## Discussion (outline)

1. The D60 source geometry is now internally calibrated in homogeneous free field at dx0.75.
2. The 1.364% refined focal error is within the preregistered engineering gate (≤4%).
3. The small lateral width change (+3.92%) suggests the correction translated the focal maximum without materially broadening the focus.
4. Comparison with the legacy 30-mm aperture / 35-mm radius tuned source: that source produced a free-field target-window peak of {calibration['pressure']['target_window_peak_mpa']:.3f} MPa at 1.0 MPa source pressure, but the D60 source is the frozen geometry for the acoustic paper route.
{discussion_grid_point}

## Limitations (explicit)

1. **Homogeneous free field only**: no skull, no transcranial interpretation.
2. **No hydrophone validation**: all pressures are simulation-derived.
{limitations_grid_point}
4. **PPW = 4 at dx0.75**: below the ≥6–8 PPW often recommended for paper-grade tFUS simulation.
5. **Single source geometry**: no aperture/radius sweep in the current manuscript core.
6. **CT pressure blocked**: until source calibration and cross-grid convergence pass.
7. **No clinical or safety claims**: this is an engineering methods step.

## Conclusion

First-order curvature correction improves the free-field focal calibration of a 60-mm aperture, 500 kHz geometric bowl source. The corrected source can serve as a reproducible starting point for future transcranial trajectory screening, but transcranial pressure and thermal conclusions require additional grid-convergence, skull-crossing, and validation steps.

## References (key)

- Treeby & Cox 2010 — k-Wave toolbox.
- Pasquinelli et al. 2020 — transducer modeling and hydrophone validation.
- Chen et al. 2023 — human skull numerical/experimental benchmark.
- Montanaro et al. 2021 — CT parameter and skull heterogeneity sensitivity.
- Gao et al. 2022 — seed protocol and thermal model reference.

## Manuscript claim policy

- **Allowed claims**: free-field source calibration improvement; reproducible engineering baseline; focal metric quantification.
- **Blocked claims**: clinical safety, paper-grade numerical convergence, transcranial efficacy, profile-default promotion, tuned-focus baseline.
"""
    output_path.write_text(text, encoding="utf-8")


def build_json(
    closeout: dict[str, Any],
    confirmation: dict[str, Any],
    grid_conv: dict[str, Any],
    calibration: dict[str, Any],
    paths: dict[str, str],
) -> dict[str, Any]:
    baseline = closeout["baseline_r74p435_dx0p75"]
    corrected = closeout["corrected_r78p330_dx0p75"]
    return {
        "skeleton_version": "1.0.0",
        "date": "2026-07-15",
        "claim_level": "engineering_validation_only",
        "allowed_claims": [
            "free-field source calibration improvement",
            "reproducible engineering baseline",
            "focal metric quantification",
        ],
        "blocked_claims": [
            "clinical safety",
            "paper-grade numerical convergence",
            "transcranial efficacy",
            "profile-default promotion",
            "tuned-focus baseline",
            "hydrophone-equivalent accuracy",
        ],
        "manuscript_title": "Source-geometry calibration of a 60-mm aperture, 500 kHz focused ultrasound transducer in homogeneous free field for patient-specific transcranial simulation",
        "key_numbers": {
            "baseline_refined_focus_error_percent": baseline["refined_focus_error_percent"],
            "corrected_refined_focus_error_percent": corrected["refined_focus_error_percent"],
            "baseline_target_to_global": baseline["target_to_global_peak_ratio"],
            "corrected_target_to_global": corrected["target_to_global_peak_ratio"],
            "baseline_global_peak_mpa": baseline["global_peak_mpa"],
            "corrected_global_peak_mpa": corrected["global_peak_mpa"],
            "dx0p5_refined_focus_error_percent": grid_conv["dx0p5"]["refined_focus_error_percent"],
            "dx0p5_waveform_complete": grid_conv["waveform_complete"],
            "legacy_aperture_mm": calibration["config"]["aperture_mm"],
            "legacy_radius_mm": calibration["config"]["radius_mm"],
            "legacy_freefield_target_window_mpa": calibration["pressure"]["target_window_peak_mpa"],
        },
        "deliverables": paths,
        "next_action": "Review manuscript skeleton; decide whether to (a) proceed with P3 fine-grid decision gate, or (b) refine the skeleton into a full draft using only satisfied/fillable evidence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    closeout = read_json(CLOSEOUT_JSON)
    confirmation = read_json(CONFIRMATION_JSON)
    grid_conv = read_json(GRID_CONV_JSON)
    calibration = read_json(CALIBRATION_JSON)

    figures_dir = args.output_dir / "figure_1_package"
    tables_dir = args.output_dir / "tables"

    asset_paths = copy_assets(figures_dir)
    parameter_table = build_parameter_table(closeout, calibration)
    results_table = build_results_table(closeout)
    table_paths = write_tables(parameter_table, results_table, tables_dir)

    paths = {**asset_paths, **table_paths}
    write_skeleton_report(closeout, confirmation, grid_conv, calibration, paths, args.output_dir / "manuscript_skeleton.md")

    skeleton_json = build_json(closeout, confirmation, grid_conv, calibration, paths)
    (args.output_dir / "paper_skeleton.json").write_text(json.dumps(skeleton_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir), "key_numbers": skeleton_json["key_numbers"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
