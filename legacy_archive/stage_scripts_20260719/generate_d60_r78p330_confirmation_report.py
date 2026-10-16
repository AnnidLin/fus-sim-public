from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_d60_grid_convergence_report import field_metrics, percent_change


BASELINE = Path("outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run")
CORRECTED = Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run")
OUTPUT = Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_confirmation_20260714")


def build_report(baseline_dir: Path, corrected_dir: Path) -> dict[str, object]:
    baseline = field_metrics(baseline_dir.resolve())
    corrected = field_metrics(corrected_dir.resolve())
    checks = {
        "runner_ok": corrected["runner_status"] == "kwave_ok",
        "refined_focus_error_le_4_percent": corrected["refined_focus_error_percent"] <= 4.0,
        "target_to_global_ge_0p9": corrected["target_to_global_peak_ratio"] >= 0.9,
        "field_finite": corrected["all_arrays_finite"],
        "boundary_distance_ge_12": corrected["global_boundary_distance_voxels"] >= 12,
        "waveform_recorded_and_finite": bool(
            corrected["target_waveform_recorded"] and corrected["target_waveform_finite"]
        ),
        "source_background_only": corrected["source_label_counts"] == {"0": 5022},
    }
    passed = all(checks.values())
    return {
        "status": "r78p330_dx0p75_confirmation_pass" if passed else "r78p330_dx0p75_confirmation_fail",
        "baseline_r74p435": baseline,
        "corrected_r78p330": corrected,
        "comparison": {
            "global_peak_change_percent": percent_change(
                baseline["global_peak_mpa"], corrected["global_peak_mpa"]
            ),
            "refined_focus_error_improvement_percentage_points": (
                baseline["refined_focus_error_percent"] - corrected["refined_focus_error_percent"]
            ),
            "refined_focus_error_reduction_percent": percent_change(
                baseline["refined_focus_error_percent"], corrected["refined_focus_error_percent"]
            ),
        },
        "acceptance": checks,
        "passed": passed,
        "dx0p5_confirmation_authorized": passed,
        "ct_pressure_authorized": False,
        "next": (
            "Prepare and run exactly one R78.330 dx0.5 free-field confirmation."
            if passed
            else "Stop and review the source correction; do not run dx0.5."
        ),
    }


def write_report(report: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "d60_r78p330_confirmation_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    b = report["baseline_r74p435"]
    c = report["corrected_r78p330"]
    x = report["comparison"]
    lines = [
        "# D60 R78.330 dx0.75 Confirmation",
        "",
        f"- Status: `{report['status']}`",
        f"- Refined focus error: {b['refined_focus_error_percent']:.3f}% -> {c['refined_focus_error_percent']:.3f}%",
        f"- Improvement: {x['refined_focus_error_improvement_percentage_points']:.3f} percentage points",
        f"- Global peak: {b['global_peak_mpa']:.4f} -> {c['global_peak_mpa']:.4f} MPa",
        f"- Target/global: {c['target_to_global_peak_ratio']:.4f}",
        f"- Boundary distance: {c['global_boundary_distance_voxels']} voxels",
        f"- Target waveform complete: {c['target_waveform_recorded'] and c['target_waveform_finite']}",
        f"- dx0.5 confirmation authorized: {report['dx0p5_confirmation_authorized']}",
        "- CT pressure authorized: false",
        "",
        "This is engineering free-field source-calibration evidence, not CT or clinical evidence.",
    ]
    (output_dir / "d60_r78p330_confirmation_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE)
    parser.add_argument("--corrected-dir", type=Path, default=CORRECTED)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = build_report(args.baseline_dir, args.corrected_dir)
    write_report(report, args.output_dir)
    print(json.dumps({"status": report["status"], "passed": report["passed"]}))


if __name__ == "__main__":
    main()

