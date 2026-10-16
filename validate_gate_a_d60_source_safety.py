from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from select_paper_gate_a_fixed_radius import bowl_source_labels


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_SELECTION = PROJECT_ROOT / "outputs/paper_gate_a_trajectory_selection_079/gate_a_trajectory_selection.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/paper_gate_a_trajectory_selection_079/d60_source_safety_report.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the D60 bowl mask on the three frozen Gate A trajectories.")
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--aperture-mm", type=float, default=60.0)
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    model_path = Path(selection["fixed"]["model"])
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    with np.load(model_path) as model:
        labels = np.asarray(model["labels"], dtype=np.uint8)
        dx_m = float(model["dx_m"])
    target = np.asarray(selection["fixed"]["target_index_ijk"], dtype=int)
    radius_mm = float(selection["fixed"]["radius_mm"])

    trajectories = []
    for item in selection["selected"]:
        label_counts, source_points = bowl_source_labels(
            labels,
            np.asarray(item["source_index_ijk"], dtype=int),
            target,
            radius_mm,
            args.aperture_mm,
            dx_m,
        )
        safe = label_counts == {"0": source_points}
        trajectories.append(
            {
                "candidate_id": item["candidate_id"],
                "source_index_ijk": item["source_index_ijk"],
                "source_standoff_mm": item.get(
                    "source_to_entry_mm", item["entry_plan"]["source_standoff_mm"]
                ),
                "skull_path_length_mm": item["skull_crossing_mm"],
                "source_points": source_points,
                "source_label_counts": label_counts,
                "background_only": safe,
            }
        )

    all_safe = len(trajectories) == 3 and all(item["background_only"] for item in trajectories)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "gate_a_d60_source_safe" if all_safe else "gate_a_d60_source_unsafe",
        "selection_status": selection["status"],
        "radius_mm": radius_mm,
        "aperture_mm": args.aperture_mm,
        "dx_mm": dx_m * 1e3,
        "trajectory_count": len(trajectories),
        "all_background_only": all_safe,
        "trajectories": trajectories,
        "pressure_execution_authorized": False,
        "next": "plan the first bounded CT pressure run only after governance review" if all_safe else "revise D60 source placement before any CT pressure",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "all_background_only": all_safe}))


if __name__ == "__main__":
    main()
