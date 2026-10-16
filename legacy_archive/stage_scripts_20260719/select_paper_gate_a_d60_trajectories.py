from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from select_paper_gate_a_fixed_radius import bowl_source_labels
from select_paper_gate_a_trajectories import angular_separation_deg


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_ROOT / "outputs/paper_gate_a_trajectory_selection_079/gate_a_trajectory_selection.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/paper_gate_a_d60_trajectory_selection_079"


def render_selected(output_dir: Path, labels: np.ndarray, selected: list[dict[str, object]]) -> None:
    for rank, item in enumerate(selected, start=1):
        source = np.asarray(item["source_index_ijk"], dtype=int)
        entry = np.asarray(item["entry_index_ijk"], dtype=int)
        target = np.asarray(item["entry_plan"]["target_index_ijk"], dtype=int)
        fig, axes = plt.subplots(1, 2, figsize=(11, 5))
        axes[0].imshow(labels[:, :, target[2]].T, origin="lower", cmap="gray", interpolation="nearest")
        axes[0].plot([source[0], entry[0], target[0]], [source[1], entry[1], target[1]], "o-", color="tab:red")
        axes[0].set_title("Axial: source-entry-target")
        axes[1].imshow(labels[:, target[1], :].T, origin="lower", cmap="gray", interpolation="nearest")
        axes[1].plot([source[0], entry[0], target[0]], [source[2], entry[2], target[2]], "o-", color="tab:blue")
        axes[1].set_title("Coronal: source-entry-target")
        fig.suptitle(f"D60 Gate A {['low', 'medium', 'high'][rank - 1]}: {item['candidate_id']}")
        fig.tight_layout()
        fig.savefig(output_dir / f"selected_{rank}_{item['candidate_id']}.png", dpi=160)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Select D60-safe trajectories from frozen Gate A geometry candidates.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--aperture-mm", type=float, default=60.0)
    parser.add_argument("--min-separation-deg", type=float, default=6.0)
    args = parser.parse_args()

    original = json.loads(args.input.read_text(encoding="utf-8"))
    model_path = Path(original["fixed"]["model"])
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    with np.load(model_path) as model:
        labels = np.asarray(model["labels"], dtype=np.uint8)
        dx_m = float(model["dx_m"])
    target = np.asarray(original["fixed"]["target_index_ijk"], dtype=int)
    radius_mm = float(original["fixed"]["radius_mm"])
    candidates = [item for item in original["candidates"] if item.get("geometry_gate_pass")]
    scores = np.asarray([float(item["difficulty_score"]) for item in candidates])
    target_scores = [float(scores.min()), float(np.median(scores)), float(scores.max())]

    selected: list[dict[str, object]] = []
    evaluated: dict[str, dict[str, object]] = {}
    for target_score in target_scores:
        ranked = sorted(candidates, key=lambda item: abs(float(item["difficulty_score"]) - target_score))
        choice = None
        for item in ranked:
            if item in selected:
                continue
            beam = np.asarray(item["beam_unit"], dtype=float)
            if any(
                angular_separation_deg(beam, np.asarray(other["beam_unit"], dtype=float)) < args.min_separation_deg
                for other in selected
            ):
                continue
            candidate_id = str(item["candidate_id"])
            if candidate_id not in evaluated:
                counts, points = bowl_source_labels(
                    labels,
                    np.asarray(item["source_index_ijk"], dtype=int),
                    target,
                    radius_mm,
                    args.aperture_mm,
                    dx_m,
                )
                evaluated[candidate_id] = {
                    "source_label_counts": counts,
                    "source_points": points,
                    "background_only": counts == {"0": points},
                }
            if evaluated[candidate_id]["background_only"]:
                choice = dict(item)
                choice.update(evaluated[candidate_id])
                choice["hard_gate_pass"] = True
                choice["failure_reasons"] = []
                choice["entry_plan"] = dict(choice["entry_plan"])
                choice["entry_plan"]["paper_gate_a_aperture_mm"] = args.aperture_mm
                break
        if choice is None:
            break
        selected.append(choice)

    status = "gate_a_d60_candidates_selected_manual_review_pending" if len(selected) == 3 else "gate_a_d60_blocked"
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "case_id": original["case_id"],
        "fixed": {
            **original["fixed"],
            "aperture_mm": args.aperture_mm,
            "minimum_angular_separation_deg": args.min_separation_deg,
        },
        "source_selection": str(args.input.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "geometry_passing_candidate_count": len(candidates),
        "source_masks_evaluated": len(evaluated),
        "difficulty_target_scores": target_scores,
        "selected": selected,
        "evaluated_source_safety": evaluated,
        "pressure_execution_authorized": False,
        "manual_review_required": ["eye_orbit_avoidance", "sinus_and_air_cavity_review", "selected_slice_review"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "gate_a_d60_trajectory_selection.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for rank, item in enumerate(selected, start=1):
        plan = dict(item["entry_plan"])
        plan["paper_gate_a_rank"] = rank
        plan["paper_gate_a_difficulty"] = ["low", "medium", "high"][rank - 1]
        candidate_dir = args.output_dir / str(item["candidate_id"])
        candidate_dir.mkdir(exist_ok=True)
        (candidate_dir / "entry_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    render_selected(args.output_dir, labels, selected)
    print(json.dumps({"status": status, "selected": [item["candidate_id"] for item in selected], "evaluated": len(evaluated)}))


if __name__ == "__main__":
    main()
