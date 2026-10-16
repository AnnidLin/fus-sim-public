from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/acoustic_model_3d.npz"
OUT_DIR = PROJECT_ROOT / "outputs/entry_offset_sensitivity_079"
PYTHON = r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe"

OFFSETS_MM = [
    (0.0, 0.0),
    (5.0, 0.0),
    (10.0, 0.0),
    (-5.0, 0.0),
    (0.0, 5.0),
    (0.0, -5.0),
]

STANDOFF_MM = 16.0


def run_plan(offset_mm: tuple[float, float]) -> dict | None:
    y, z = offset_mm
    out_subdir = OUT_DIR / f"offset_y{y:+04.0f}_z{z:+04.0f}"
    out_subdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        PYTHON,
        "plan_ct_target_entry.py",
        "--model",
        str(MODEL_PATH),
        "--output-dir",
        str(out_subdir),
        "--source-standoff-mm",
        str(STANDOFF_MM),
        f"--entry-offset-mm={y},{z}",
    ]
    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True, capture_output=True, text=True)
        plan = json.loads((out_subdir / "entry_plan.json").read_text(encoding="utf-8"))
        return plan
    except Exception as exc:
        print(f"Failed for offset {offset_mm}: {exc}")
        return None


def beam_axis_stats(plan: dict, model_data: dict) -> dict:
    labels = model_data["labels"]
    hu = model_data["hu"]
    alpha = model_data["alpha_coeff"]
    dx_m = float(model_data["dx_m"].item())
    dx_mm = dx_m * 1e3

    source = np.array(plan["source_center_index_ijk"], dtype=int)
    target = np.array(plan["target_index_ijk"], dtype=int)
    beam_vec = target - source
    beam_len = np.linalg.norm(beam_vec)
    if beam_len <= 0:
        return {}
    beam_unit = beam_vec / beam_len
    steps = np.arange(0, int(beam_len) + 2)

    skull_count = 0
    max_hu = -9999.0
    total_alpha = 0.0
    n = 0
    for t in steps:
        idx = np.round(source + t * beam_unit).astype(int)
        if not (np.all(idx >= 0) and np.all(idx < labels.shape)):
            continue
        if labels[tuple(idx)] == 2:
            skull_count += 1
        max_hu = max(max_hu, float(hu[tuple(idx)]))
        total_alpha += float(alpha[tuple(idx)])
        n += 1

    return {
        "skull_voxels_along_beam": skull_count,
        "skull_crossing_mm": round(skull_count * dx_mm, 3),
        "max_hu_along_beam": round(max_hu, 1),
        "mean_alpha_db_mhz_cm": round(total_alpha / n, 3) if n else None,
        "source_to_target_mm": plan["source_to_target_distance_mm"],
        "skull_path_length_mm": plan["skull_path_length_mm"],
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model_data = dict(np.load(MODEL_PATH))

    results = []
    for offset in OFFSETS_MM:
        print(f"Planning offset {offset}...")
        plan = run_plan(offset)
        if plan is None:
            continue
        stats = beam_axis_stats(plan, model_data)
        results.append(
            {
                "offset_mm": list(offset),
                "plan": plan,
                "beam_axis_stats": stats,
            }
        )

    # Summary table sorted by skull crossing along actual beam axis
    results.sort(key=lambda r: r["beam_axis_stats"].get("skull_voxels_along_beam", 0), reverse=True)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": "079",
        "candidate_id": "candidate_006",
        "model": str(MODEL_PATH),
        "source_standoff_mm": STANDOFF_MM,
        "candidates": results,
    }
    (OUT_DIR / "entry_offset_sensitivity.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Markdown report
    md_lines = [
        "# Entry Offset Sensitivity Plan for 079 candidate_006",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Model: `{MODEL_PATH}`",
        f"- Source standoff: `{STANDOFF_MM} mm`",
        "",
        "## Candidates ranked by actual skull crossing along source-to-target beam axis",
        "",
        "| Offset Y,Z (mm) | Skull voxels along beam | Skull crossing (mm) | Max HU along beam | Mean alpha | S2T (mm) | Planned skull path (mm) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        s = r["beam_axis_stats"]
        offset = r["offset_mm"]
        md_lines.append(
            f"| ({offset[0]:+.0f}, {offset[1]:+.0f}) | {s.get('skull_voxels_along_beam')} | "
            f"{s.get('skull_crossing_mm')} | {s.get('max_hu_along_beam')} | "
            f"{s.get('mean_alpha_db_mhz_cm')} | {s.get('source_to_target_mm')} | {s.get('skull_path_length_mm')} |"
        )
    md_lines.extend([
        "",
        "## Recommendation",
        "",
        "- Choose an offset with higher actual skull crossing if the goal is to represent realistic transcranial attenuation.",
        "- Choose an offset with lower actual skull crossing if the goal is to maximize focal pressure at the target.",
        "- Any new pressure run must still pass dry-run-quality and require explicit authorization.",
    ])
    (OUT_DIR / "entry_offset_sensitivity.md").write_text("\n".join(md_lines), encoding="utf-8")

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))
    offsets = [f"({r['offset_mm'][0]:+.0f},{r['offset_mm'][1]:+.0f})" for r in results]
    crossings = [r["beam_axis_stats"].get("skull_crossing_mm", 0) for r in results]
    ax.bar(offsets, crossings)
    ax.set_ylabel("Skull crossing along beam (mm)")
    ax.set_xlabel("Entry offset Y,Z (mm)")
    ax.set_title("Entry Offset vs Actual Skull Crossing")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "entry_offset_sensitivity.png", dpi=150)
    plt.close(fig)

    print(json.dumps({f"({r['offset_mm'][0]:+.0f},{r['offset_mm'][1]:+.0f})": r["beam_axis_stats"] for r in results}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
