from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_PLAN = PROJECT_ROOT / "outputs/paper_gate_b_freefield_closure/dx0p75/entry_plan.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_dx0p75/entry_plan.json"


def expanded_plan(source_plan: dict[str, object], aperture_mm: float, pml_size: int) -> dict[str, object]:
    dx_mm = float(source_plan["dx_m"]) * 1e3
    source = np.asarray(source_plan["source_center_index_ijk"], dtype=int)
    target = np.asarray(source_plan["target_index_ijk"], dtype=int)
    beam_axis = target - source
    beam_unit = beam_axis / np.linalg.norm(beam_axis)
    distance_mm = float(np.linalg.norm(beam_axis) * dx_mm)
    lateral_margin = int(np.ceil((aperture_mm / 2.0 + 12.0) / dx_mm)) + pml_size
    axial_margin = int(np.ceil(12.0 / dx_mm)) + pml_size
    raw_source = np.zeros(3, dtype=int)
    raw_target = np.rint(beam_unit * (distance_mm / dx_mm)).astype(int)
    minima = np.minimum(raw_source, raw_target)
    maxima = np.maximum(raw_source, raw_target)
    margins = np.array([axial_margin, lateral_margin, lateral_margin], dtype=int)
    new_source = raw_source - minima + margins
    new_target = raw_target - minima + margins
    shape = maxima - minima + 1 + 2 * margins
    entry = new_source + np.rint(beam_unit * (16.0 / dx_mm)).astype(int)
    return {
        **source_plan,
        "description": f"Expanded homogeneous free-field plan for D{aperture_mm:g} mm aperture",
        "source_center_index_ijk": new_source.tolist(),
        "target_index_ijk": new_target.tolist(),
        "entry_index_ijk": entry.tolist(),
        "skull_exit_index_ijk": entry.tolist(),
        "beam_axis": (new_target - new_source).tolist(),
        "source_to_target_distance_mm": float(np.linalg.norm(new_target - new_source) * dx_mm),
        "source_to_entry_distance_mm": float(np.linalg.norm(entry - new_source) * dx_mm),
        "model_shape": shape.tolist(),
        "paper_aperture_mm": aperture_mm,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-plan", type=Path, default=SOURCE_PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--aperture-mm", type=float, default=60.0)
    parser.add_argument("--pml-size", type=int, default=12)
    args = parser.parse_args()
    source_plan = json.loads(args.source_plan.read_text(encoding="utf-8"))
    plan = expanded_plan(source_plan, args.aperture_mm, args.pml_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "shape": plan["model_shape"], "distance_mm": plan["source_to_target_distance_mm"]}))


if __name__ == "__main__":
    main()
