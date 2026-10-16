from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


QUICK = Path("outputs/a4_quick_screen_20260718/offset_y+00p0_z-20p0/tr/summary_calibrate.json")
STANDARD = Path("outputs/a4b_standard_tr_confirmation_20260719/offset_y+00p0_z-20p0/dryrun_calibrate/quality_dry_run_summary.json")
OUTPUT = Path("outputs/a4b_standard_tr_confirmation_20260719/preset_equivalence")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pick(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for key in path.split("."):
        value = value[key]
    return value


FINGERPRINT_PATHS = (
    "config.stage",
    "config.frequency_hz",
    "config.calibration_pressure_pa",
    "config.source_pressure_pa",
    "config.normalize_source",
    "config.transducer_radius_m",
    "config.aperture_diameter_m",
    "config.tone_burst_cycles",
    "config.cfl",
    "config.simulation_time_s",
    "config.pml_size",
    "config.backend",
    "config.device",
    "config.quick_mode",
    "config.quick_lateral_half_width_m",
    "config.quick_post_target_margin_m",
    "config.nearfield_exclusion_m",
    "config.record_target_waveform",
    "model.model_shape",
    "model.source_model_shape",
    "model.crop_origin_ijk",
    "model.dx_m",
    "model.target_index_ijk",
    "source.bowl_index_ijk",
    "source.target_index_ijk",
    "source.radius_grid_points",
    "source.diameter_grid_points",
    "source.source_points",
    "source.source_label_counts",
    "simulation_quality.grid_size",
    "simulation_quality.voxel_count",
    "simulation_quality.dx_m",
    "simulation_quality.frequency_hz",
    "simulation_quality.cfl",
    "simulation_quality.pml_size",
    "simulation_quality.dt_s",
    "simulation_quality.nt",
    "simulation_quality.simulation_time_s",
)


def compare(quick: dict[str, Any], standard: dict[str, Any]) -> dict[str, Any]:
    differences = []
    fingerprint = {}
    for path in FINGERPRINT_PATHS:
        quick_value = pick(quick, path)
        standard_value = pick(standard, path)
        fingerprint[path] = quick_value
        if quick_value != standard_value:
            differences.append({"path": path, "quick": quick_value, "standard": standard_value})
    equivalent = not differences
    return {
        "status": "evidence_redundant_do_not_run" if equivalent else "numerical_upgrade_detected",
        "numerically_equivalent": equivalent,
        "quick_preset_label": quick["config"]["preset"],
        "standard_preset_label": standard["config"]["preset"],
        "fingerprint": fingerprint,
        "differences": differences,
        "pressure_execution_authorized_by_equivalence_gate": not equivalent,
        "interpretation": (
            "Only the preset label differs; repeating pressure propagation would add no numerical evidence."
            if equivalent
            else "At least one numerical field differs; review the differences before any pressure execution."
        ),
    }


def write(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "preset_equivalence_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# A4b Quick vs Standard Preset Equivalence Audit",
        "",
        f"- Status: `{report['status']}`",
        f"- Numerically equivalent: {report['numerically_equivalent']}",
        f"- Labels: `{report['quick_preset_label']}` vs `{report['standard_preset_label']}`",
        f"- Numerical differences: {len(report['differences'])}",
        f"- Pressure execution authorized by this gate: {report['pressure_execution_authorized_by_equivalence_gate']}",
        "",
        str(report["interpretation"]),
        "",
        "The original A4 quick hold remains unchanged. This audit only prevents a label-only duplicate run.",
    ]
    (output_dir / "preset_equivalence_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", type=Path, default=QUICK)
    parser.add_argument("--standard", type=Path, default=STANDARD)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = compare(load(args.quick), load(args.standard))
    write(report, args.output_dir)
    print(json.dumps({"status": report["status"], "equivalent": report["numerically_equivalent"]}))


if __name__ == "__main__":
    main()

