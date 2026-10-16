from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from select_paper_gate_a_fixed_radius import bowl_source_labels
from select_paper_gate_a_trajectories import angular_separation_deg, write_outputs


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "outputs/paper_gate_a_trajectory_selection_079"


def render_selected(labels: np.ndarray, selected: list[dict[str, object]]) -> None:
    for rank, item in enumerate(selected, start=1):
        source = np.asarray(item["source_index_ijk"], dtype=int)
        entry = np.asarray(item["entry_index_ijk"], dtype=int)
        target = np.asarray(item["entry_plan"]["target_index_ijk"], dtype=int)
        fig, axes = plt.subplots(1, 2, figsize=(11, 5))
        axes[0].imshow(labels[:, :, target[2]].T, origin="lower", cmap="gray", interpolation="nearest")
        axes[0].plot([source[0], entry[0], target[0]], [source[1], entry[1], target[1]], "o-", color="tab:red")
        axes[0].set_title("Axial: source-entry-target")
        axes[0].set_xlabel("i")
        axes[0].set_ylabel("j")
        axes[1].imshow(labels[:, target[1], :].T, origin="lower", cmap="gray", interpolation="nearest")
        axes[1].plot([source[0], entry[0], target[0]], [source[2], entry[2], target[2]], "o-", color="tab:blue")
        axes[1].set_title("Coronal: source-entry-target")
        axes[1].set_xlabel("i")
        axes[1].set_ylabel("k")
        fig.suptitle(f"Gate A {['low', 'medium', 'high'][rank - 1]}: {item['candidate_id']}")
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / f"selected_{rank}_{item['candidate_id']}.png", dpi=160)
        plt.close(fig)


def main() -> None:
    summary_path = OUTPUT_DIR / "gate_a_trajectory_selection.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    model_path = Path(summary["fixed"]["model"])
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    data = np.load(model_path)
    labels = np.asarray(data["labels"], dtype=np.uint8)
    dx_m = float(np.asarray(data["dx_m"]).item())
    target = np.asarray(summary["fixed"]["target_index_ijk"], dtype=int)
    radius_mm = float(summary["fixed"]["radius_mm"])
    aperture_mm = float(summary["fixed"]["aperture_mm"])

    selected = sorted(summary["selected"], key=lambda item: float(item["difficulty_score"]))
    safe_selected = [item for item in selected if item.get("hard_gate_pass")]
    if len(safe_selected) != 2:
        raise ValueError(f"Expected two source-safe initial selections, found {len(safe_selected)}.")

    fallback = None
    ranked = sorted(
        (item for item in summary["candidates"] if item.get("geometry_gate_pass")),
        key=lambda item: float(item["difficulty_score"]),
        reverse=True,
    )
    for item in ranked:
        beam = np.asarray(item["beam_unit"], dtype=float)
        if any(angular_separation_deg(beam, np.asarray(other["beam_unit"], dtype=float)) < 6.0 for other in safe_selected):
            continue
        label_counts, source_points = bowl_source_labels(
            labels,
            np.asarray(item["source_index_ijk"], dtype=int),
            target,
            radius_mm,
            aperture_mm,
            dx_m,
        )
        item["source_label_counts"] = label_counts
        item["source_points"] = source_points
        item["hard_gate_pass"] = label_counts == {"0": source_points}
        if item["hard_gate_pass"]:
            fallback = item
            break
        if "bowl_mask_not_background_only" not in item["failure_reasons"]:
            item["failure_reasons"].append("bowl_mask_not_background_only")

    if fallback is None:
        raise RuntimeError("No source-safe high-difficulty fallback candidate was found.")

    final_selected = sorted([*safe_selected, fallback], key=lambda item: float(item["difficulty_score"]))
    summary["selected"] = final_selected
    summary["passing_candidate_count"] = 3
    summary["status"] = "gate_a_candidates_selected_manual_review_pending"
    summary["selection_note"] = "High-difficulty initial candidate failed bowl source safety; replaced by first angularly separated source-safe candidate in descending difficulty order."
    write_outputs(OUTPUT_DIR, summary)
    render_selected(labels, final_selected)
    print(json.dumps({"status": summary["status"], "selected": [item["candidate_id"] for item in final_selected]}))


if __name__ == "__main__":
    main()
