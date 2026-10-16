"""Generate the H115 simulation/reproducibility methods table from accepted summaries."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def row(label: str, summary: dict, package: dict, geometry_source: str) -> dict:
    config = summary["config"]
    quality = summary["simulation_quality"]
    runtime = summary["runtime"]
    device = package["device_extrema"]
    return {
        "model": label,
        "geometry_source": geometry_source,
        "radius_mm": float(config["transducer_radius_m"]) * 1e3,
        "aperture_diameter_mm": float(config["aperture_diameter_m"]) * 1e3,
        "dx_mm": float(summary["dx_m"]) * 1e3,
        "ppw_min": float(quality["ppw_min_sound_speed"]),
        "pml_points": int(config["pml_size"]),
        "pml_thickness_mm": int(config["pml_size"]) * float(summary["dx_m"]) * 1e3,
        "cfl": float(config["cfl"]),
        "dt_ns": float(runtime["dt_s"]) * 1e9,
        "nt": int(runtime["nt"]),
        "cycles": int(config["tone_burst_cycles"]),
        "simulation_time_us": float(config["simulation_time_s"]) * 1e6,
        "grid": "x".join(str(value) for value in summary["model_shape"]),
        "source_points": int(summary["source"]["source_points"]),
        "solver_runtime_min": float(runtime["runtime_s"]) / 60.0,
        "max_equivalent_cores": float(device["max_equivalent_cores"]),
        "max_working_set_gib": float(device["max_working_set_gib"]),
        "min_system_free_memory_gib": float(device["min_system_free_memory_gib"]),
        "quality_evidence_level": quality["evidence_level"],
        "is_paper_grade": bool(quality["is_paper_grade"]),
    }


def markdown(rows: list[dict]) -> str:
    lines = [
        "# Supplementary table — UCL H115 simulation and resource parameters",
        "",
        "| Model | Geometry | Radius / aperture (mm) | dx / PPW | PML | CFL / dt / nt | Grid / source points | Solver runtime | Device extrema |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in rows:
        lines.append(
            f'| {item["model"]} | {item["geometry_source"]} | '
            f'{item["radius_mm"]:.2f} / {item["aperture_diameter_mm"]:.2f} | '
            f'{item["dx_mm"]:.2f} mm / {item["ppw_min"]:.2f} | '
            f'{item["pml_points"]} points ({item["pml_thickness_mm"]:.2f} mm) | '
            f'{item["cfl"]:.2f} / {item["dt_ns"]:.3f} ns / {item["nt"]} | '
            f'{item["grid"]} / {item["source_points"]} | {item["solver_runtime_min"]:.2f} min | '
            f'CPU {item["max_equivalent_cores"]:.3f} cores; WS {item["max_working_set_gib"]:.3f} GiB; free {item["min_system_free_memory_gib"]:.3f} GiB |'
        )
    lines.extend(
        [
            "",
            "All runs used 270 kHz, 16 cycles, 180 us, homogeneous water, CPU backend and the standard engineering preset. Device extrema are independently read from package-validation records. These rows document execution and do not upgrade the nonpassing external-validation verdict or establish formal convergence.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--effective-dx0p5-dir", type=Path, required=True)
    parser.add_argument("--effective-dx0p3-dir", type=Path, required=True)
    parser.add_argument("--nominal-dx0p5-dir", type=Path, required=True)
    parser.add_argument("--nominal-package", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    rows = [
        row("Effective bowl, dx0.50 mm", read_json(args.effective_dx0p5_dir / "summary.json"), read_json(args.effective_dx0p5_dir / "package_validation.json"), "paper-derived effective bowl"),
        row("Effective bowl, dx0.30 mm", read_json(args.effective_dx0p3_dir / "summary.json"), read_json(args.effective_dx0p3_dir / "package_validation.json"), "paper-derived effective bowl"),
        row("Nominal bowl, dx0.50 mm", read_json(args.nominal_dx0p5_dir / "summary.json"), read_json(args.nominal_package), "HDF5 nominal 64/64-mm union"),
    ]
    checks = {
        "three_rows": len(rows) == 3,
        "shared_frequency_cycles_duration": all(
            read_json(directory / "summary.json")["config"]["frequency_hz"] == 270000.0
            and read_json(directory / "summary.json")["config"]["tone_burst_cycles"] == 16
            and abs(read_json(directory / "summary.json")["config"]["simulation_time_s"] - 180e-6) < 1e-12
            for directory in (args.effective_dx0p5_dir, args.effective_dx0p3_dir, args.nominal_dx0p5_dir)
        ),
        "device_gates": all(item["max_equivalent_cores"] <= 6.5 and item["max_working_set_gib"] <= 16.0 and item["min_system_free_memory_gib"] >= 4.0 for item in rows),
        "engineering_not_paper_grade": all(not item["is_paper_grade"] for item in rows),
    }
    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "rows": rows,
        "claim_boundary": "Reproducibility table only; external validation remains nonpassing and two grids are not formal convergence.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "h115_methods_parameters.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.output_dir / "h115_methods_parameters.md").write_text(markdown(rows), encoding="utf-8")
    with (args.output_dir / "h115_methods_parameters.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"status": report["status"], "checks": checks}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
