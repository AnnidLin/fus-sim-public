"""Generate a small homogeneous-water model and entry plan for H115 dry-run QA."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


REFERENCE_EXTENT_M = np.array([0.1005, 0.0805, 0.0805], dtype=float)
SOURCE_STANDOFF_M = 0.010


def build_geometry(dx_m: float, radius_m: float) -> dict[str, object]:
    if dx_m <= 0 or radius_m <= 0:
        raise ValueError("dx and radius must be positive")
    shape = tuple(int(round(value / dx_m)) for value in REFERENCE_EXTENT_M)
    source = np.array(
        [int(round(SOURCE_STANDOFF_M / dx_m)), shape[1] // 2, shape[2] // 2],
        dtype=np.int32,
    )
    target = source + np.array([int(round(radius_m / dx_m)), 0, 0], dtype=np.int32)
    if np.any(target >= np.asarray(shape)):
        raise ValueError("target lies outside the water model")
    return {
        "shape": shape,
        "source": source,
        "target": target,
        "beam_axis": np.array([1, 0, 0], dtype=np.int32),
        "physical_extent_m": np.asarray(shape, dtype=float) * dx_m,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dx-mm", type=float, default=0.50)
    parser.add_argument("--radius-mm", type=float, default=61.39)
    parser.add_argument("--aperture-mm", type=float, default=50.40)
    parser.add_argument("--sound-speed-m-s", type=float, default=1482.3)
    parser.add_argument("--density-kg-m3", type=float, default=998.2)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dx_m = args.dx_mm * 1e-3
    radius_m = args.radius_mm * 1e-3
    if args.aperture_mm <= 0 or args.aperture_mm > 2.0 * args.radius_mm:
        raise ValueError("aperture must be positive and no larger than the source sphere diameter")
    geometry = build_geometry(dx_m, radius_m)
    shape = geometry["shape"]
    sound_speed = np.full(shape, args.sound_speed_m_s, dtype=np.float32)
    density = np.full(shape, args.density_kg_m3, dtype=np.float32)
    alpha_coeff = np.zeros(shape, dtype=np.float32)
    labels = np.zeros(shape, dtype=np.uint8)

    np.savez_compressed(
        args.output_dir / "acoustic_model_3d.npz",
        sound_speed=sound_speed,
        density=density,
        alpha_coeff=alpha_coeff,
        labels=labels,
        dx_m=np.array(dx_m, dtype=np.float32),
        target_index_ijk=geometry["target"],
        alpha_power=np.array(2.0, dtype=np.float32),
        alpha_mode=np.array("no_absorption"),
        alpha_unit_semantics=np.array("dB/(MHz^2 cm); value fixed to zero"),
        alpha_coeff_kind=np.array("homogeneous_water_zero"),
        alpha_source_route=np.array("ucl_h115_water_dryrun_evidence_brief"),
        alpha_semantics_status=np.array("free_field"),
        alpha_pressure_allowed=np.array(True),
        alpha_pressure_allowed_state=np.array("allowed"),
    )
    entry_plan = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "UCL H115 homogeneous-water measurement validation dry-run",
        "dx_m": dx_m,
        "model_shape": list(shape),
        "physical_extent_mm": (np.asarray(shape, dtype=float) * dx_m * 1e3).tolist(),
        "source_standoff_mm": float(geometry["source"][0] * dx_m * 1e3),
        "target_index_ijk": geometry["target"].tolist(),
        "source_center_index_ijk": geometry["source"].tolist(),
        "entry_index_ijk": geometry["source"].tolist(),
        "beam_axis": geometry["beam_axis"].tolist(),
        "source_to_target_distance_mm": float(np.linalg.norm(geometry["target"] - geometry["source"]) * dx_m * 1e3),
        "coordinate_scope": "synthetic homogeneous water; not registered to CT or Case079",
    }
    (args.output_dir / "entry_plan.json").write_text(json.dumps(entry_plan, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "1.0",
        "status": "generated_for_dry_run_only",
        "model_shape": list(shape),
        "dx_mm": args.dx_mm,
        "ppw_at_270khz": args.sound_speed_m_s / 270000.0 / dx_m,
        "water": {"sound_speed_m_s": args.sound_speed_m_s, "density_kg_m3": args.density_kg_m3, "alpha_coeff": 0.0},
        "source": {
            "frequency_hz": 270000.0,
            "radius_mm": args.radius_mm,
            "aperture_diameter_mm": args.aperture_mm,
            "geometry_role": "effective" if (args.radius_mm, args.aperture_mm) == (61.39, 50.40) else "explicit_candidate",
        },
        "claim_boundary": "dry-run geometry only; no solver output",
    }
    (args.output_dir / "model_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "output_dir": str(args.output_dir), "model_shape": shape}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
