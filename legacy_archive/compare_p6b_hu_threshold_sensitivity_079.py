from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
MODEL_DIRS = {
    "hu250": ROOT / "outputs/ct_acoustic_model_3d_profile_hu250_dx0p75",
    "hu300": ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75",
    "hu400": ROOT / "outputs/ct_acoustic_model_3d_profile_hu400_dx0p75",
}
OUT_DIR = ROOT / "outputs/p6b_hu_threshold_sensitivity_079"


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as data:
        return {k: np.copy(data[k]) for k in data.files}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load hu300 model to get geometry consistent with P6b baseline
    base_model = load_npz(MODEL_DIRS["hu300"] / "acoustic_model_3d.npz")
    dx_m = float(base_model["dx_m"].item())
    dx_mm = dx_m * 1e3

    # Source and target indices in the full/source model grid, matching P6b baseline
    source_center_source = np.array([63, 174, 84])
    target_source = np.array([124, 161, 84])
    beam_vec = target_source - source_center_source
    beam_len_gp = np.linalg.norm(beam_vec)
    beam_unit = beam_vec / beam_len_gp
    steps = np.arange(0, int(beam_len_gp) + 2)

    models = {name: load_npz(path / "acoustic_model_3d.npz") for name, path in MODEL_DIRS.items()}

    rows = []
    for t in steps:
        pt_source_idx = np.round(source_center_source + t * beam_unit).astype(int)
        if not (np.all(pt_source_idx >= 0) and np.all(pt_source_idx < base_model["labels"].shape)):
            continue

        row: dict[str, object] = {
            "dist_mm": round(t * dx_mm, 3),
            "coords_source": pt_source_idx.tolist(),
        }
        for name, data in models.items():
            row[f"label_{name}"] = int(data["labels"][tuple(pt_source_idx)])
            row[f"hu_{name}"] = round(float(data["hu"][tuple(pt_source_idx)]), 1)
            row[f"c_{name}"] = round(float(data["sound_speed"][tuple(pt_source_idx)]), 1)
            row[f"rho_{name}"] = round(float(data["density"][tuple(pt_source_idx)]), 1)
            row[f"alpha_{name}"] = round(float(data["alpha_coeff"][tuple(pt_source_idx)]), 3)
        rows.append(row)

    # Aggregate skull crossing stats
    stats = {}
    for name in models:
        skull_steps = [r["dist_mm"] for r in rows if r[f"label_{name}"] == 2]
        stats[name] = {
            "skull_voxel_count": len(skull_steps),
            "skull_crossing_mm": round(len(skull_steps) * dx_mm, 3),
            "max_hu_along_axis": max(r[f"hu_{name}"] for r in rows),
        }

    # JSON report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": "079",
        "candidate_id": "candidate_006",
        "dx_mm": dx_mm,
        "beam_axis_profile": rows,
        "threshold_sensitivity": stats,
    }
    (OUT_DIR / "hu_threshold_sensitivity.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Markdown report
    md_lines = [
        "# P6b HU Threshold Sensitivity Audit: 079 candidate_006 dx0.75",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Grid spacing: `{dx_mm} mm`",
        "",
        "## Skull Crossing Sensitivity by HU Threshold",
        "",
        "| Threshold | Skull Voxels Along Beam | Skull Crossing (mm) | Max HU Along Beam |",
        "|---|---:|---:|---:|",
    ]
    for name, s in stats.items():
        md_lines.append(
            f"| `{name}` | {s['skull_voxel_count']} | {s['skull_crossing_mm']} | {s['max_hu_along_axis']} |"
        )
    md_lines.extend([
        "",
        "## Interpretation",
        "",
        "- `hu250` classifies the most voxels as skull along the beam axis.",
        "- `hu400` is the most conservative; fewer voxels reach the bone threshold.",
        "- Compare with the P6b baseline report to see how threshold choice changes the perceived skull attenuation path.",
        "",
        "## Sample Beam Axis Trace",
        "",
        "| Dist (mm) | Label hu250 | Label hu300 | Label hu400 | HU hu250 | HU hu300 | HU hu400 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for r in rows[::5]:  # sample every 5 steps
        md_lines.append(
            f"| {r['dist_mm']} | {r['label_hu250']} | {r['label_hu300']} | {r['label_hu400']} | "
            f"{r['hu_hu250']} | {r['hu_hu300']} | {r['hu_hu400']} |"
        )
    (OUT_DIR / "hu_threshold_sensitivity.md").write_text("\n".join(md_lines), encoding="utf-8")

    # Plot
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    dists = [r["dist_mm"] for r in rows]
    for ax, field, ylabel in zip(
        axes,
        ["label", "hu", "alpha"],
        ["Label (0=bg, 1=soft, 2=skull)", "HU", "Alpha (dB/MHz/cm)"],
    ):
        for name in models:
            vals = [r[f"{field}_{name}"] for r in rows]
            ax.plot(dists, vals, marker="o", markersize=2, label=name)
        ax.set_ylabel(ylabel)
        ax.legend()
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Distance along beam axis (mm)")
    fig.suptitle("HU Threshold Sensitivity Along Post-Skull Beam Axis")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "hu_threshold_sensitivity.png", dpi=150)
    plt.close(fig)

    print(f"Wrote reports to {OUT_DIR}")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
