from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from select_paper_gate_a_fixed_radius import bowl_source_labels
from select_paper_gate_a_trajectories import angular_separation_deg


ROOT = Path(__file__).resolve().parent
POOL = ROOT / "outputs" / "paper_gate_a_trajectory_selection_079" / "gate_a_trajectory_selection.json"
A4 = ROOT / "outputs" / "paper_gate_a_d60_trajectory_selection_079" / "gate_a_d60_trajectory_selection.json"
OUTPUT = ROOT / "outputs" / "a5_heldout_d60_trajectory_selection_20260719"
MIN_SEPARATION_DEG = 6.0
QUANTILES = (0.25, 0.50, 0.75)


def separated(beam: np.ndarray, other_beams: list[np.ndarray], minimum_deg: float) -> bool:
    return all(angular_separation_deg(beam, other) >= minimum_deg for other in other_beams)


def render(output: Path, labels: np.ndarray, selected: list[dict]) -> None:
    for rank, item in enumerate(selected, start=1):
        source = np.asarray(item["source_index_ijk"], dtype=int)
        entry = np.asarray(item["entry_index_ijk"], dtype=int)
        target = np.asarray(item["entry_plan"]["target_index_ijk"], dtype=int)
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), constrained_layout=True)
        axes[0].imshow(labels[:, :, target[2]].T, origin="lower", cmap="gray", interpolation="nearest")
        axes[0].plot([source[0], entry[0], target[0]], [source[1], entry[1], target[1]], "o-", color="#c43d32")
        axes[0].set_title("Axial")
        axes[1].imshow(labels[:, target[1], :].T, origin="lower", cmap="gray", interpolation="nearest")
        axes[1].plot([source[0], entry[0], target[0]], [source[2], entry[2], target[2]], "o-", color="#196fa6")
        axes[1].set_title("Coronal")
        fig.suptitle(f"Held-out D60 candidate {rank}: {item['candidate_id']}")
        fig.savefig(output / f"heldout_{rank}_{item['candidate_id']}.png", dpi=180, facecolor="white")
        plt.close(fig)


def main() -> None:
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    a4 = json.loads(A4.read_text(encoding="utf-8"))
    model_path = Path(pool["fixed"]["model"])
    if not model_path.is_absolute():
        model_path = ROOT / model_path
    with np.load(model_path) as model:
        labels = np.asarray(model["labels"], dtype=np.uint8)
        dx_m = float(np.asarray(model["dx_m"]).item())
    target = np.asarray(pool["fixed"]["target_index_ijk"], dtype=int)
    radius_mm = float(a4["fixed"]["radius_mm"])
    aperture_mm = float(a4["fixed"]["aperture_mm"])
    excluded_ids = {str(item["candidate_id"]) for item in a4["selected"]}
    a4_beams = [np.asarray(item["beam_unit"], dtype=float) for item in a4["selected"]]

    eligible = []
    for item in pool["candidates"]:
        if not item.get("geometry_gate_pass") or str(item["candidate_id"]) in excluded_ids:
            continue
        beam = np.asarray(item["beam_unit"], dtype=float)
        if separated(beam, a4_beams, MIN_SEPARATION_DEG):
            eligible.append(item)
    scores = np.asarray([float(item["difficulty_score"]) for item in eligible], dtype=float)
    targets = [float(np.quantile(scores, q)) for q in QUANTILES] if len(scores) else []

    evaluated: dict[str, dict] = {}
    selected: list[dict] = []
    selected_beams: list[np.ndarray] = []
    for target_score in targets:
        ranked = sorted(eligible, key=lambda item: abs(float(item["difficulty_score"]) - target_score))
        for item in ranked:
            candidate_id = str(item["candidate_id"])
            if candidate_id in {str(value["candidate_id"]) for value in selected}:
                continue
            beam = np.asarray(item["beam_unit"], dtype=float)
            if not separated(beam, selected_beams, MIN_SEPARATION_DEG):
                continue
            if candidate_id not in evaluated:
                counts, points = bowl_source_labels(
                    labels,
                    np.asarray(item["source_index_ijk"], dtype=int),
                    target,
                    radius_mm,
                    aperture_mm,
                    dx_m,
                )
                evaluated[candidate_id] = {
                    "source_label_counts": counts,
                    "source_points": points,
                    "background_only": counts == {"0": points},
                }
            if not evaluated[candidate_id]["background_only"]:
                continue
            choice = dict(item)
            choice.update(evaluated[candidate_id])
            choice["entry_plan"] = dict(choice["entry_plan"])
            choice["entry_plan"]["paper_gate_a_aperture_mm"] = aperture_mm
            choice["heldout_quantile_target"] = target_score
            selected.append(choice)
            selected_beams.append(beam)
            break

    status = "heldout_selection_ready" if len(selected) == 3 else "heldout_selection_blocked"
    report = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "outputs/evidence_briefs/a5_heldout_trajectory_selection/evidence_brief.md",
        "pool": str(POOL.relative_to(ROOT)).replace("\\", "/"),
        "a4_exclusion_ids": sorted(excluded_ids),
        "minimum_angular_separation_deg": MIN_SEPARATION_DEG,
        "eligible_geometry_count": len(eligible),
        "source_masks_evaluated": len(evaluated),
        "selected": selected,
        "evaluated_source_safety": evaluated,
        "pressure_execution_authorized": False,
        "manual_review_required": len(selected) == 3,
        "next": (
            "gross anatomy review then preregister absolute-gate TR protocol"
            if len(selected) == 3
            else "do not run pressure; Case 079 lacks a complete independent held-out set under frozen gates"
        ),
        "claim_level": "geometry_and_source_mask_only",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "heldout_selection.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for rank, item in enumerate(selected, start=1):
        candidate_dir = OUTPUT / str(item["candidate_id"])
        candidate_dir.mkdir(exist_ok=True)
        plan = dict(item["entry_plan"])
        plan["heldout_rank"] = rank
        plan["pressure_execution_authorized"] = False
        (candidate_dir / "entry_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    render(OUTPUT, labels, selected)
    print(json.dumps({"status": status, "eligible": len(eligible), "evaluated": len(evaluated), "selected": [item["candidate_id"] for item in selected]}))


if __name__ == "__main__":
    main()
