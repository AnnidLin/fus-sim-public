from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
COL_DIR = ROOT / "outputs/collinear_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard"
COR_DIR = ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard"
OUT_DIR = ROOT / "outputs/collinear_vs_corrected_baseline_079"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pct_delta(new: float, old: float) -> float:
    return round((new - old) / old * 100, 2) if old else 0.0


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    col_fm = load_json(COL_DIR / "focus_metrics.json")
    cor_fm = load_json(COR_DIR / "focus_metrics.json")
    col_sum = load_json(COL_DIR / "summary.json")
    cor_sum = load_json(COR_DIR / "summary.json")

    metrics = {
        "global_peak_mpa": ("Global peak (MPa)", "MPa"),
        "target_pressure_mpa": ("Target pressure (MPa)", "MPa"),
        "target_window_peak_mpa": ("Target-window peak (MPa)", "MPa"),
        "global_peak_to_target_distance_mm": ("Global peak-to-target distance (mm)", "mm"),
        "effective_peak_mpa": ("Effective peak (MPa)", "MPa"),
        "effective_peak_to_target_distance_mm": ("Effective peak-to-target distance (mm)", "mm"),
    }

    rows = []
    for key, (label, unit) in metrics.items():
        col_v = col_fm.get(key)
        cor_v = cor_fm.get(key)
        rows.append(
            {
                "metric": label,
                "unit": unit,
                "collinear": col_v,
                "corrected_baseline": cor_v,
                "delta_collinear_vs_corrected_pct": pct_delta(col_v, cor_v),
            }
        )

    runtime_col = col_sum.get("runtime_seconds")
    runtime_cor = cor_sum.get("runtime_seconds")
    rows.append(
        {
            "metric": "Runtime",
            "unit": "s",
            "collinear": runtime_col,
            "corrected_baseline": runtime_cor,
            "delta_collinear_vs_corrected_pct": pct_delta(runtime_col, runtime_cor),
        }
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": "079",
        "candidate_id": "candidate_006",
        "comparison": "collinear_vs_corrected_baseline",
        "collinear_dir": str(COL_DIR.relative_to(ROOT)),
        "corrected_baseline_dir": str(COR_DIR.relative_to(ROOT)),
        "metrics": rows,
    }
    (OUT_DIR / "comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown report
    md_lines = [
        "# Collinear vs Corrected Baseline Pressure Comparison: 079 candidate_006",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Collinear dir: `{report['collinear_dir']}`",
        f"- Corrected baseline dir: `{report['corrected_baseline_dir']}`",
        "",
        "## Pressure Metrics",
        "",
        "| Metric | Collinear | Corrected Baseline | Delta (collinear vs corrected) |",
        "|---|---:|---:|---:|",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['metric']} | {r['collinear']} | {r['corrected_baseline']} | {r['delta_collinear_vs_corrected_pct']:+}% |"
        )
    md_lines.extend([
        "",
        "## Interpretation",
        "",
        "- Collinear `(+0,+0)` entry crosses more skull bone along the beam axis (see `outputs/entry_offset_sensitivity_079/`).",
        "- Corrected baseline `(+10,+0)` tilts the beam to skim the skull edge, reducing attenuation and increasing target pressure.",
        "- The corrected baseline's higher target pressure comes at the cost of representing a less typical transcranial beam path.",
        "",
        "## Claim boundary",
        "",
        "- This is an engineering comparison of two entry geometries, not evidence of numerical convergence or clinical safety.",
    ])
    (OUT_DIR / "comparison.md").write_text("\n".join(md_lines), encoding="utf-8")

    # Plot
    labels_plot = [r["metric"].replace(" (MPa)", "").replace(" (mm)", "") for r in rows[:-1]]
    col_vals = [r["collinear"] for r in rows[:-1]]
    cor_vals = [r["corrected_baseline"] for r in rows[:-1]]

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()
    for ax, label, col_v, cor_v in zip(axes, labels_plot, col_vals, cor_vals):
        ax.bar(["collinear", "corrected"], [col_v, cor_v])
        ax.set_title(label)
        ax.set_ylabel("Value")
    fig.suptitle("Collinear vs Corrected Baseline Pressure Metrics")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "comparison.png", dpi=150)
    plt.close(fig)

    print(json.dumps(rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
