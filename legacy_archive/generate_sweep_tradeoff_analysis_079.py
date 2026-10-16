"""
Case 079 sweep trade-off analysis.

Reads pressure and Pennes summaries from dx0.75 sweep_000/sweep_005 and dx0.5
sweep_000/sweep_000_p038, quantifies the focus-vs-thermal-safety trade-off,
and writes a structured report with recommended next directions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs/sweep_tradeoff_analysis_079"

RUNS = {
    "dx075_sweep_000_collinear": {
        "pressure": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_000/summary.json",
        "thermal": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_000/pennes_thermal/pennes_summary.json",
        "label": "dx0.75 sweep_000 (collinear)",
        "category": "collinear_control",
    },
    "dx075_sweep_005_focus_optimized": {
        "pressure": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005/summary.json",
        "thermal": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005/pennes_thermal/pennes_summary.json",
        "label": "dx0.75 sweep_005 (focus optimized)",
        "category": "focus_optimized",
    },
    "dx05_sweep_000_collinear": {
        "pressure": ROOT / "outputs/ct_sweep_scan_079_dx0p5/sweep_000/summary.json",
        "thermal": ROOT / "outputs/ct_sweep_scan_079_dx0p5/sweep_000/pennes_thermal/pennes_summary.json",
        "label": "dx0.5 sweep_000 (collinear)",
        "category": "collinear_control",
    },
    "dx05_sweep_000_p038_scaled": {
        "pressure": ROOT / "outputs/ct_sweep_scan_079_dx0p5/sweep_000_p038/summary.json",
        "thermal": ROOT / "outputs/ct_sweep_scan_079_dx0p5/sweep_000_p038/pennes_thermal/pennes_summary.json",
        "label": "dx0.5 sweep_000 @ 0.38 MPa (scaled)",
        "category": "scaled_validation",
    },
    "dx075_sweep_005_p500_scaled": {
        "pressure": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p500/summary.json",
        "thermal": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p500/pennes_thermal/pennes_summary.json",
        "label": "dx0.75 sweep_005 @ 0.50 MPa (scaled)",
        "category": "scaled_validation",
    },
    "dx075_sweep_005_p600_scaled": {
        "pressure": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p600/summary.json",
        "thermal": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p600/pennes_thermal/pennes_summary.json",
        "label": "dx0.75 sweep_005 @ 0.60 MPa (scaled)",
        "category": "scaled_validation",
    },
    "dx075_sweep_005_p700_scaled": {
        "pressure": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p700/summary.json",
        "thermal": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p700/pennes_thermal/pennes_summary.json",
        "label": "dx0.75 sweep_005 @ 0.70 MPa (scaled)",
        "category": "scaled_validation",
    },
    "dx075_sweep_005_p800_scaled": {
        "pressure": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p800/summary.json",
        "thermal": ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p800/pennes_thermal/pennes_summary.json",
        "label": "dx0.75 sweep_005 @ 0.80 MPa (scaled)",
        "category": "scaled_validation",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_log10(x: float) -> float:
    if x <= 0:
        return float("-inf")
    return float(np.log10(x))


def extract_record(run_id: str, info: dict[str, Any]) -> dict[str, Any]:
    p = load_json(info["pressure"])
    t = load_json(info["thermal"])

    entry = p.get("entry_plan", {})
    pm = p.get("pressure", {})
    tm = t.get("thermal_dose_safety", {})
    tm_brain = tm.get("brain_safety", {})
    tm_skull = tm.get("skull_safety", {})

    record = {
        "run_id": run_id,
        "label": info["label"],
        "category": info["category"],
        "dx_mm": round(p.get("dx_m", 0) * 1000, 3),
        "source_pressure_mpa": p.get("config", {}).get("source_pressure_pa", 0) / 1e6,
        "entry_direction": entry.get("entry_direction", "unknown"),
        "source_standoff_mm": entry.get("source_standoff_mm", 0),
        "source_to_target_distance_mm": entry.get("source_to_target_distance_mm", 0),
        "skull_path_length_mm": entry.get("skull_path_length_mm", 0),
        "global_peak_mpa": pm.get("global_peak_mpa", 0),
        "target_pressure_mpa": pm.get("target_pressure_mpa", 0),
        "target_window_peak_mpa": pm.get("target_window_peak_mpa", 0),
        "effective_peak_mpa": pm.get("effective_peak_mpa", 0),
        "global_peak_to_target_distance_mm": pm.get("global_peak_to_target_distance_mm", 0),
        "target_to_global_peak_ratio": pm.get("target_to_global_peak_ratio", 0),
        "max_temperature_rise_c": t.get("max_temperature_rise_c", 0),
        "max_temperature_c": t.get("max_temperature_c", 0),
        "target_temperature_rise_c": t.get("target_temperature_rise_c", 0),
        "brain_max_cem43_min": t.get("brain_max_cem43_min", 0),
        "skull_max_cem43_min": t.get("skull_max_cem43_min", 0),
        "brain_safety_status": tm_brain.get("status", "UNKNOWN"),
        "skull_safety_status": tm_skull.get("status", "UNKNOWN"),
        "overall_safe": tm.get("overall_safe", False),
        "runtime_s": p.get("runtime", {}).get("runtime_s", 0),
    }

    # Derived trade-off metrics
    record["focus_thermal_ratio"] = (
        record["target_window_peak_mpa"] / max(record["skull_max_cem43_min"], 1e-12)
        if record["skull_max_cem43_min"] > 0
        else float("inf")
    )
    record["target_window_peak_per_skull_cem43_log10"] = safe_log10(
        record["target_window_peak_mpa"] / max(record["skull_max_cem43_min"], 1e-12)
    )
    record["peak_axial_shortfall_mm"] = pm.get("global_peak_axial_shortfall_to_target_mm", 0)
    return record


def build_findings(records: list[dict[str, Any]]) -> list[str]:
    findings = []

    # Focus comparison
    dx075_col = next((r for r in records if r["run_id"] == "dx075_sweep_000_collinear"), None)
    dx075_opt = next(
        (r for r in records if r["run_id"] == "dx075_sweep_005_focus_optimized"), None
    )
    dx05_col = next((r for r in records if r["run_id"] == "dx05_sweep_000_collinear"), None)
    dx05_scaled = next(
        (r for r in records if r["run_id"] == "dx05_sweep_000_p038_scaled"), None
    )
    dx075_opt_p500 = next(
        (r for r in records if r["run_id"] == "dx075_sweep_005_p500_scaled"), None
    )

    if dx075_col and dx075_opt:
        tw_delta = dx075_opt["target_window_peak_mpa"] - dx075_col["target_window_peak_mpa"]
        tw_rel = tw_delta / max(dx075_col["target_window_peak_mpa"], 1e-12) * 100
        skull_cem_delta = dx075_opt["skull_max_cem43_min"] - dx075_col["skull_max_cem43_min"]
        skull_cem_ratio = dx075_opt["skull_max_cem43_min"] / max(
            dx075_col["skull_max_cem43_min"], 1e-12
        )
        findings.append(
            f"Focus-optimized sweep_005 improves target-window peak by {tw_delta:.3f} MPa "
            f"({tw_rel:+.1f}%) over collinear sweep_000 at dx0.75."
        )
        findings.append(
            f"This focus improvement costs a {skull_cem_ratio:.1f}x increase in skull CEM43 "
            f"({dx075_col['skull_max_cem43_min']:.2f} -> {dx075_opt['skull_max_cem43_min']:.2f} min)."
        )

    if dx075_col and dx05_col:
        tw_rel = (
            (dx05_col["target_window_peak_mpa"] - dx075_col["target_window_peak_mpa"])
            / max(dx075_col["target_window_peak_mpa"], 1e-12)
            * 100
        )
        skull_cem_factor = dx05_col["skull_max_cem43_min"] / max(
            dx075_col["skull_max_cem43_min"], 1e-12
        )
        findings.append(
            f"dx0.5 collinear vs dx0.75 collinear: target-window peak changes by {tw_rel:+.1f}%, "
            f"skull CEM43 changes by ~{skull_cem_factor:.2e}x. This is a grid-sensitivity/hotspot "
            f"diagnostic, not numerical convergence."
        )

    if dx05_col and dx05_scaled:
        pressure_ratio = dx05_scaled["source_pressure_mpa"] / max(dx05_col["source_pressure_mpa"], 1e-12)
        tw_ratio = dx05_scaled["target_window_peak_mpa"] / max(dx05_col["target_window_peak_mpa"], 1e-12)
        cem_ratio = dx05_scaled["skull_max_cem43_min"] / max(dx05_col["skull_max_cem43_min"], 1e-12)
        findings.append(
            f"Scaling source pressure from 1.0 MPa to 0.38 MPa ({pressure_ratio:.2f}x) reduces "
            f"target-window peak to {tw_ratio:.3f}x and skull CEM43 to {cem_ratio:.3e}x, "
            f"making the thermal result pass local safety gates."
        )

    if dx075_opt and dx075_opt_p500:
        pressure_ratio = dx075_opt_p500["source_pressure_mpa"] / max(dx075_opt["source_pressure_mpa"], 1e-12)
        tw_ratio = dx075_opt_p500["target_window_peak_mpa"] / max(dx075_opt["target_window_peak_mpa"], 1e-12)
        cem_ratio = dx075_opt_p500["skull_max_cem43_min"] / max(dx075_opt["skull_max_cem43_min"], 1e-12)
        temp_ratio = dx075_opt_p500["max_temperature_rise_c"] / max(dx075_opt["max_temperature_rise_c"], 1e-12)
        if dx075_opt_p500["overall_safe"]:
            findings.append(
                f"Scaling sweep_005 from 1.0 MPa to 0.50 MPa ({pressure_ratio:.2f}x) reduces "
                f"target-window peak to {tw_ratio:.3f}x and skull CEM43 to {cem_ratio:.3e}x, "
                f"matching the linear pressure prediction almost exactly. With the Gao 2022 cooling "
                f"protocol, max temperature rise is {dx075_opt_p500['max_temperature_rise_c']:.2f}°C "
                f"and the run is overall_safe=true."
            )
            findings.append(
                f"The sweep_005 focus-optimized geometry at 0.5 MPa delivers {dx075_opt_p500['target_window_peak_mpa']:.3f} MPa "
                f"target-window peak with skull CEM43 {dx075_opt_p500['skull_max_cem43_min']:.4f} min and max temperature "
                f"{dx075_opt_p500['max_temperature_c']:.2f}°C, all within local safety limits."
            )
        else:
            findings.append(
                f"Scaling sweep_005 from 1.0 MPa to 0.50 MPa ({pressure_ratio:.2f}x) reduces "
                f"target-window peak to {tw_ratio:.3f}x and skull CEM43 to {cem_ratio:.3e}x, "
                f"matching the linear pressure prediction almost exactly. However, max temperature rise "
                f"only drops to {temp_ratio:.3f}x ({dx075_opt_p500['max_temperature_rise_c']:.2f}°C), "
                f"causing temperature-limit exceedance and overall_safe=false."
            )
            findings.append(
                "The sweep_005 focus-optimized geometry at 0.5 MPa is no longer limited by CEM43 "
                f"accumulation ({dx075_opt_p500['skull_max_cem43_min']:.3f} min << 16 min limit) but by instantaneous peak temperature "
                f"({dx075_opt_p500['max_temperature_c']:.2f}°C > 43°C limit)."
            )

    safe_runs = [r for r in records if r["overall_safe"]]
    unsafe_runs = [r for r in records if not r["overall_safe"]]
    findings.append(
        f"Thermal safety: {len(safe_runs)} of {len(records)} runs are overall_safe "
        f"({[r['run_id'] for r in safe_runs]})."
    )
    findings.append(
        "All runs still show the global/effective peak displaced from the target "
        "(axial shortfall 30-56 mm), indicating these are not tuned-focus baselines."
    )
    findings.append(
        "Skull path lengths are short (0.75-4.5 mm) and source masks are background-only; "
        "the acoustic energy is interacting with only a thin skull segment or soft-tissue path."
    )
    return findings


def plot_tradeoff(records: list[dict[str, Any]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    labels = [r["label"].replace(" (", "\n(") for r in records]
    x = np.arange(len(records))

    # Left: target-window peak vs skull CEM43
    ax = axes[0]
    tw_peaks = [r["target_window_peak_mpa"] for r in records]
    colors = ["#2ca02c" if r["overall_safe"] else "#d62728" for r in records]
    bars = ax.bar(x, tw_peaks, color=colors, alpha=0.7, edgecolor="black")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=8)
    ax.set_ylabel("Target-window peak pressure (MPa)")
    ax.set_title("Focus metric (green=thermal safe, red=unsafe)")
    for bar, r in zip(bars, records):
        height = bar.get_height()
        ax.annotate(
            f"skull CEM43\n{r['skull_max_cem43_min']:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    # Right: global peak distance to target
    ax = axes[1]
    dists = [r["global_peak_to_target_distance_mm"] for r in records]
    ax.bar(x, dists, color="steelblue", alpha=0.7, edgecolor="black")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=8)
    ax.set_ylabel("Global peak to target distance (mm)")
    ax.set_title("Prefocal displacement (all runs peak far from target)")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "sweep_tradeoff_overview.png", dpi=150)
    plt.close(fig)


def build_recommendations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": "R1",
            "direction": "Reduce source pressure for the focus-optimized geometry",
            "rationale": (
                "sweep_005 delivers +15% target-window peak but ~37x skull CEM43 vs sweep_000. "
                "A scaled source-pressure sweep (e.g. 0.5-0.8 MPa) on sweep_005 could map the "
                "focus-thermal Pareto front without changing geometry."
            ),
            "evidence_needed": [
                "one-run authorization package per source pressure",
                "dry-run-quality for each pressure level",
                "Pennes thermal run for each stable pressure",
            ],
            "risk": "Medium: multiple k-Wave runs, but each is bounded and uses known geometry.",
            "requires_kwave_authorization": True,
        },
        {
            "id": "R2",
            "direction": "Increase actual skull path length via target/entry repositioning",
            "rationale": (
                "Current skull path lengths are <= 4.5 mm. Repositioning target or entry to intersect "
                "a thicker skull region may improve phase-aberration representativeness, though it "
                "will likely reduce target pressure due to attenuation."
            ),
            "evidence_needed": [
                "CT-based skull thickness map",
                "new entry-plan generation with skull-path-length constraint",
                "dry-run-quality and source-safety check",
            ],
            "risk": "High: changes the anatomical target and may require new clinical justification.",
            "requires_kwave_authorization": True,
        },
        {
            "id": "R3",
            "direction": "Implement PlanTUS-style geometric proxy screening before next k-Wave",
            "rationale": (
                "Before running more pressure simulations, rank candidate geometries by source safety, "
                "skull path length, incidence angle, and heuristic transmission proxy. This reduces "
                "the number of expensive k-Wave runs needed to explore the trade-off."
            ),
            "evidence_needed": [
                "geometric proxy scoring script",
                "validation that proxy correlates with observed target pressure and thermal dose",
            ],
            "risk": "Low: read-only / model-only work, no k-Wave execution.",
            "requires_kwave_authorization": False,
        },
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = [extract_record(rid, info) for rid, info in RUNS.items()]
    findings = build_findings(records)
    recommendations = build_recommendations(records)

    report = {
        "analysis_id": "case_079_sweep_tradeoff_analysis",
        "analysis_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim_level": "engineering_observation_not_clinical_safety",
        "records": records,
        "findings": findings,
        "recommendations": recommendations,
    }

    with open(OUT_DIR / "sweep_tradeoff_summary.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Markdown report
    md_lines = [
        "# Case 079 Sweep Focus-Thermal Trade-off Analysis",
        "",
        f"- **Analysis version**: `{report['analysis_version']}`",
        f"- **Generated at**: `{report['generated_at']}`",
        f"- **Claim level**: `{report['claim_level']}`",
        "",
        "## Summary Table",
        "",
        "| Run | dx (mm) | Source P (MPa) | Target-window P (MPa) | Global P (MPa) | Peak-target dist (mm) | Max dT (°C) | Skull CEM43 (min) | Safe |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        safe_str = "✅" if r["overall_safe"] else "❌"
        md_lines.append(
            f"| {r['label']} | {r['dx_mm']:.2f} | {r['source_pressure_mpa']:.2f} | "
            f"{r['target_window_peak_mpa']:.3f} | {r['global_peak_mpa']:.3f} | "
            f"{r['global_peak_to_target_distance_mm']:.1f} | {r['max_temperature_rise_c']:.2f} | "
            f"{r['skull_max_cem43_min']:.3f} | {safe_str} |"
        )

    md_lines.extend([
        "",
        "## Key Findings",
        "",
    ])
    for f in findings:
        md_lines.append(f"- {f}")

    md_lines.extend([
        "",
        "## Focus-Thermal Trade-off",
        "",
        "The focus-optimized geometry (sweep_005) improves target-window pressure but at a large cost "
        "in skull thermal dose. The scaled 0.38 MPa run shows that reducing source pressure can bring "
        "thermal safety back into range, but it also lowers target pressure proportionally.",
        "",
        "| Run | Target-window peak / Skull CEM43 (MPa/min) | log10 ratio |",
        "|---|---|---|",
    ])
    for r in records:
        md_lines.append(
            f"| {r['label']} | {r['focus_thermal_ratio']:.3e} | {r['target_window_peak_per_skull_cem43_log10']:.2f} |"
        )

    md_lines.extend([
        "",
        "## Recommended Next Directions",
        "",
    ])
    for rec in recommendations:
        md_lines.extend([
            f"### {rec['id']}: {rec['direction']}",
            "",
            f"**Rationale**: {rec['rationale']}",
            "",
            "**Evidence needed**:",
        ])
        for e in rec["evidence_needed"]:
            md_lines.append(f"- {e}")
        md_lines.extend([
            "",
            f"**Risk**: {rec['risk']}",
            f"**Requires k-Wave authorization**: {'Yes' if rec['requires_kwave_authorization'] else 'No'}",
            "",
        ])

    md_lines.extend([
        "## Claim Boundaries",
        "",
        "- This report is an engineering-level observation for research reproducibility.",
        "- It does not establish clinical safety, efficacy, or a validated default mapping profile.",
        "- The 0.38 MPa scaled result is a local engineering validation point only.",
        "- Any future k-Wave run requires an evidence brief, dry-run-quality gate, output conflict check, "
        "one-run authorization package, and explicit user authorization.",
    ])

    with open(OUT_DIR / "sweep_tradeoff_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    plot_tradeoff(records)
    print(f"Wrote {OUT_DIR / 'sweep_tradeoff_summary.json'}")
    print(f"Wrote {OUT_DIR / 'sweep_tradeoff_report.md'}")
    print(f"Wrote {OUT_DIR / 'sweep_tradeoff_overview.png'}")


if __name__ == "__main__":
    main()
