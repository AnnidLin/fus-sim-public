from __future__ import annotations

import json
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent
GATE_A_DIR = PROJECT_ROOT / "outputs/paper_gate_a_trajectory_selection_079"
OUTPUT_DIR = PROJECT_ROOT / "outputs/paper_gate_b_freefield_closure"
RADIUS_MM = 74.4353753
APERTURE_MM = 30.0
PML_SIZE = 12


def make_plan(dx_mm: float, beam_unit: np.ndarray) -> dict[str, object]:
    beam_axis = np.rint(beam_unit * (RADIUS_MM / dx_mm)).astype(int)
    lateral_margin_gp = int(np.ceil((APERTURE_MM / 2.0 + 12.0) / dx_mm)) + PML_SIZE
    axial_margin_gp = int(np.ceil(12.0 / dx_mm)) + PML_SIZE
    raw_source = np.zeros(3, dtype=int)
    raw_target = beam_axis
    minima = np.minimum(raw_source, raw_target)
    maxima = np.maximum(raw_source, raw_target)
    margins = np.array([axial_margin_gp, lateral_margin_gp, lateral_margin_gp], dtype=int)
    source = raw_source - minima + margins
    target = raw_target - minima + margins
    shape = maxima - minima + 1 + 2 * margins
    entry = source + np.rint(beam_unit * (16.0 / dx_mm)).astype(int)
    distance_mm = float(np.linalg.norm(target - source) * dx_mm)
    return {
        "description": "Paper Gate B homogeneous free-field geometry",
        "entry_direction": "synthetic_freefield_fixed_source",
        "entry_offset_mm": [0.0, 0.0],
        "target_index_ijk": target.tolist(),
        "source_center_index_ijk": source.tolist(),
        "entry_index_ijk": entry.tolist(),
        "skull_exit_index_ijk": entry.tolist(),
        "beam_axis": (target - source).tolist(),
        "source_center_label": 0,
        "entry_label": 0,
        "target_label": 0,
        "has_skull_crossing": False,
        "source_standoff_mm": 16.0,
        "source_to_entry_distance_mm": float(np.linalg.norm(entry - source) * dx_mm),
        "source_to_target_distance_mm": distance_mm,
        "skull_path_length_mm": 0.0,
        "dx_m": dx_mm * 1e-3,
        "model_shape": shape.tolist(),
        "paper_gate_b_fixed_radius_mm": RADIUS_MM,
        "paper_gate_b_aperture_mm": APERTURE_MM,
    }


def main() -> None:
    gate_a = json.loads((GATE_A_DIR / "gate_a_trajectory_selection.json").read_text(encoding="utf-8"))
    medium = sorted(gate_a["selected"], key=lambda item: float(item["difficulty_score"]))[1]
    beam_unit = np.asarray(medium["beam_unit"], dtype=float)
    beam_unit /= np.linalg.norm(beam_unit)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plans = []
    for dx_mm, name in ((0.75, "dx0p75"), (0.5, "dx0p5")):
        plan = make_plan(dx_mm, beam_unit)
        plan_dir = OUTPUT_DIR / name
        plan_dir.mkdir(exist_ok=True)
        (plan_dir / "entry_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        plans.append({"name": name, "path": str(plan_dir / "entry_plan.json"), "plan": plan})
    summary = {
        "status": "plans_generated_pressure_not_authorized",
        "orientation_source": medium["candidate_id"],
        "beam_unit": beam_unit.tolist(),
        "fixed": {"radius_mm": RADIUS_MM, "aperture_mm": APERTURE_MM, "frequency_khz": 500.0},
        "plans": plans,
        "pressure_execution_authorized": False,
    }
    (OUTPUT_DIR / "gate_b_freefield_plans.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "plans": [item["name"] for item in plans]}))


if __name__ == "__main__":
    main()
