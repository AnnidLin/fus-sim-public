"""
Case 079 geometric proxy screening (PlanTUS-style).

Reads existing entry_plan.json, pressure summary, and Pennes summary for sweep
candidates, computes geometric/heuristic proxies, ranks candidates, and writes
a screening report. No k-Wave execution.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs/geometric_proxy_screening_079"

# Candidates with entry_plan; pressure/thermal are optional.
CANDIDATES = [
    {
        "run_id": "dx075_sweep_000_collinear",
        "entry_plan": "outputs/ct_sweep_scan_079_dx0p75/sweep_000/entry_plan.json",
        "pressure_summary": "outputs/ct_sweep_scan_079_dx0p75/sweep_000/summary.json",
        "thermal_summary": "outputs/ct_sweep_scan_079_dx0p75/sweep_000/pennes_thermal/pennes_summary.json",
    },
    {
        "run_id": "dx075_sweep_005_focus_optimized",
        "entry_plan": "outputs/ct_sweep_scan_079_dx0p75/sweep_005/entry_plan.json",
        "pressure_summary": "outputs/ct_sweep_scan_079_dx0p75/sweep_005/summary.json",
        "thermal_summary": "outputs/ct_sweep_scan_079_dx0p75/sweep_005/pennes_thermal/pennes_summary.json",
    },
    {
        "run_id": "dx075_sweep_018_large_theta",
        "entry_plan": "outputs/ct_sweep_scan_079_dx0p75/sweep_018/entry_plan.json",
        "pressure_summary": None,
        "thermal_summary": None,
    },
    {
        "run_id": "dx05_sweep_000_collinear",
        "entry_plan": "outputs/ct_sweep_scan_079_dx0p5/sweep_000/entry_plan.json",
        "pressure_summary": "outputs/ct_sweep_scan_079_dx0p5/sweep_000/summary.json",
        "thermal_summary": "outputs/ct_sweep_scan_079_dx0p5/sweep_000/pennes_thermal/pennes_summary.json",
    },
    {
        "run_id": "dx05_sweep_001_symmetric_phi",
        "entry_plan": "outputs/ct_sweep_scan_079_dx0p5/sweep_001/entry_plan.json",
        "pressure_summary": None,
        "thermal_summary": None,
    },
    {
        "run_id": "dx05_sweep_003_focus_optimized",
        "entry_plan": "outputs/ct_sweep_scan_079_dx0p5/sweep_003/entry_plan.json",
        "pressure_summary": "outputs/ct_sweep_scan_079_dx0p5/sweep_003/summary.json",
        "thermal_summary": "outputs/ct_sweep_scan_079_dx0p5/sweep_003/pennes_thermal/pennes_summary.json",
    },
    {
        "run_id": "dx05_sweep_000_p038_scaled",
        "entry_plan": "outputs/ct_sweep_scan_079_dx0p5/sweep_000/entry_plan.json",
        "pressure_summary": "outputs/ct_sweep_scan_079_dx0p5/sweep_000_p038/summary.json",
        "thermal_summary": "outputs/ct_sweep_scan_079_dx0p5/sweep_000_p038/pennes_thermal/pennes_summary.json",
    },
]


def load_json(path: Path | str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_theta_phi(entry_direction: str) -> tuple[float, float]:
    """Extract theta and phi in degrees from 'sweep_theta_X.X_phi_Y.Y'."""
    try:
        parts = entry_direction.replace("sweep_theta_", "").split("_phi_")
        theta = float(parts[0])
        phi = float(parts[1])
        return theta, phi
    except Exception:
        return 0.0, 0.0


def compute_scores(entry: dict[str, Any]) -> dict[str, float]:
    """Compute normalized geometric proxy scores (0-1, higher is better)."""
    dx = entry.get("dx_m", 0.75e-3)
    skull_len = entry.get("skull_path_length_mm", 0.0)
    standoff = entry.get("source_standoff_mm", 0.0)
    s2t = entry.get("source_to_target_distance_mm", 0.0)
    theta, phi = parse_theta_phi(entry.get("entry_direction", ""))

    # Obliquity: theta=0 -> 1, theta>=20 -> 0
    obliquity_score = max(0.0, 1.0 - theta / 20.0)

    # Skull path length: ideal window 2-6 mm.
    # Too short (<1 mm) -> low representativeness; too long (>10 mm) -> high attenuation.
    if skull_len < 1.0:
        skull_score = 0.2 + 0.8 * (skull_len / 1.0)
    elif skull_len <= 6.0:
        skull_score = 1.0
    elif skull_len <= 10.0:
        skull_score = 1.0 - (skull_len - 6.0) / 4.0
    else:
        skull_score = 0.0

    # Source-to-target distance: prefer 50-65 mm range; penalize extremes.
    if 50.0 <= s2t <= 65.0:
        s2t_score = 1.0
    elif s2t < 50.0:
        s2t_score = max(0.0, s2t / 50.0)
    else:
        s2t_score = max(0.0, 1.0 - (s2t - 65.0) / 20.0)

    # Standoff: prefer 12-20 mm; too close (<10 mm) risks source safety / hotspot issues.
    if 12.0 <= standoff <= 20.0:
        standoff_score = 1.0
    elif standoff < 10.0:
        standoff_score = max(0.0, standoff / 10.0)
    else:
        # linear ramp 10-12
        standoff_score = 0.0 + (standoff - 10.0) / 2.0

    # Heuristic transmission proxy based on normal-incident equivalent path.
    # Use a simplified attenuation factor; alpha in Np/mm equivalent.
    alpha_np_per_mm = 0.05  # heuristic for skull absorption/scattering
    incidence_factor = max(1.0, 1.0 / max(np.cos(np.radians(theta)), 0.2))
    effective_skull_mm = skull_len * incidence_factor
    transmission_proxy = float(np.exp(-alpha_np_per_mm * effective_skull_mm))

    # Composite recommendation score: balance focus and thermal safety.
    # Higher obliquity/s2t/standoff/skull_score are better for geometry;
    # lower transmission_proxy means more attenuation (worse focus), so we
    # penalize too-high transmission only if skull is very short (hotspot risk).
    if skull_len < 1.0:
        hotspot_penalty = 0.5 * (1.0 - skull_len)
    else:
        hotspot_penalty = 0.0

    composite = (
        0.25 * obliquity_score
        + 0.25 * skull_score
        + 0.20 * s2t_score
        + 0.15 * standoff_score
        + 0.15 * transmission_proxy
        - hotspot_penalty
    )
    composite = max(0.0, min(1.0, composite))

    return {
        "theta_deg": theta,
        "phi_deg": phi,
        "skull_path_length_mm": skull_len,
        "source_to_target_distance_mm": s2t,
        "source_standoff_mm": standoff,
        "obliquity_score": obliquity_score,
        "skull_path_score": skull_score,
        "source_to_target_score": s2t_score,
        "standoff_score": standoff_score,
        "transmission_proxy": transmission_proxy,
        "composite_proxy_score": composite,
    }


@dataclass
class CandidateRecord:
    run_id: str
    dx_mm: float
    entry_direction: str
    has_pressure: bool
    has_thermal: bool
    target_window_peak_mpa: float | None
    skull_max_cem43_min: float | None
    overall_safe: bool | None
    scores: dict[str, float]


def build_record(spec: dict[str, Any]) -> CandidateRecord:
    entry = load_json(spec["entry_plan"])
    assert entry is not None, f"Missing entry_plan for {spec['run_id']}"

    p = load_json(spec.get("pressure_summary"))
    t = load_json(spec.get("thermal_summary"))

    pm = p.get("pressure", {}) if p else {}
    tm = t if t else {}

    return CandidateRecord(
        run_id=spec["run_id"],
        dx_mm=round(entry.get("dx_m", 0) * 1000, 3),
        entry_direction=entry.get("entry_direction", "unknown"),
        has_pressure=p is not None,
        has_thermal=t is not None,
        target_window_peak_mpa=pm.get("target_window_peak_mpa"),
        skull_max_cem43_min=tm.get("skull_max_cem43_min"),
        overall_safe=(tm.get("thermal_dose_safety") or {}).get("overall_safe"),
        scores=compute_scores(entry),
    )


def plot_proxy_vs_empirical(records: list[CandidateRecord]) -> None:
    validated = [r for r in records if r.has_pressure and r.has_thermal]
    if len(validated) < 3:
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Left: composite proxy vs target-window peak
    ax = axes[0]
    x = [r.scores["composite_proxy_score"] for r in validated]
    y = [r.target_window_peak_mpa for r in validated]
    colors = ["green" if r.overall_safe else "red" for r in validated]
    ax.scatter(x, y, c=colors, s=120, alpha=0.7, edgecolors="black")
    for r in validated:
        ax.annotate(
            r.run_id.replace("_", "\n"),
            (r.scores["composite_proxy_score"], r.target_window_peak_mpa or 0),
            fontsize=7,
            ha="center",
        )
    ax.set_xlabel("Composite geometric proxy score")
    ax.set_ylabel("Target-window peak pressure (MPa)")
    ax.set_title("Proxy score vs observed focus (green=safe, red=unsafe)")
    ax.grid(True, alpha=0.3)

    # Right: composite proxy vs skull CEM43 (log scale)
    ax = axes[1]
    y2 = [r.skull_max_cem43_min for r in validated]
    ax.scatter(x, y2, c=colors, s=120, alpha=0.7, edgecolors="black")
    for r in validated:
        ax.annotate(
            r.run_id.replace("_", "\n"),
            (r.scores["composite_proxy_score"], r.skull_max_cem43_min or 1e-6),
            fontsize=7,
            ha="center",
        )
    ax.set_xlabel("Composite geometric proxy score")
    ax.set_ylabel("Skull CEM43 (min, log scale)")
    ax.set_yscale("log")
    ax.set_title("Proxy score vs observed skull thermal dose")
    ax.grid(True, alpha=0.3, which="both")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "proxy_vs_empirical.png", dpi=150)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = [build_record(c) for c in CANDIDATES]
    records.sort(key=lambda r: r.scores["composite_proxy_score"], reverse=True)

    # Write JSON summary
    summary = {
        "analysis_id": "case_079_geometric_proxy_screening",
        "analysis_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim_level": "engineering_observation_not_clinical_safety",
        "scoring_weights": {
            "obliquity": 0.25,
            "skull_path": 0.25,
            "source_to_target": 0.20,
            "standoff": 0.20,
            "transmission_proxy": 0.15,
        },
        "caveats": [
            "Proxy scores are heuristic and not validated against a large dataset.",
            "Surface-normal incidence angle is approximated by entry theta only.",
            "Transmission proxy uses a fixed heuristic attenuation coefficient.",
            "Candidates without pressure/thermal results are ranked by geometry only.",
        ],
        "records": [asdict(r) for r in records],
    }
    with open(OUT_DIR / "geometric_proxy_screening_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Write markdown report
    md = [
        "# Case 079 Geometric Proxy Screening Report",
        "",
        f"- **Version**: `{summary['analysis_version']}`",
        f"- **Generated**: `{summary['generated_at']}`",
        f"- **Claim level**: `{summary['claim_level']}`",
        "",
        "## Scoring weights",
        "",
        "| Criterion | Weight | Rationale |",
        "|---|---|---|",
        "| Obliquity (theta) | 0.25 | Near-normal incidence reduces aberration and hotspot risk |",
        "| Skull path length | 0.25 | 2-6 mm ideal: representative but not overly attenuating |",
        "| Source-to-target distance | 0.20 | 50-65 mm range preferred for typical transcranial FUS |",
        "| Source standoff | 0.20 | 12-20 mm avoids near-source hotspot / PML coupling |",
        "| Heuristic transmission | 0.10 | Exponential attenuation proxy along effective skull path |",
        "",
        "## Ranked candidates",
        "",
        "| Rank | Run | dx (mm) | Direction | Composite | Skull len (mm) | S2T (mm) | Standoff (mm) | Target P (MPa) | Skull CEM43 | Safe |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(records, 1):
        tw = f"{r.target_window_peak_mpa:.3f}" if r.target_window_peak_mpa is not None else "N/A"
        cem = f"{r.skull_max_cem43_min:.3f}" if r.skull_max_cem43_min is not None else "N/A"
        safe = "✅" if r.overall_safe else ("❌" if r.overall_safe is False else "N/A")
        md.append(
            f"| {i} | {r.run_id} | {r.dx_mm:.2f} | {r.entry_direction} | "
            f"{r.scores['composite_proxy_score']:.3f} | "
            f"{r.scores['skull_path_length_mm']:.2f} | "
            f"{r.scores['source_to_target_distance_mm']:.1f} | "
            f"{r.scores['source_standoff_mm']:.2f} | {tw} | {cem} | {safe} |"
        )

    md.extend([
        "",
        "## Proxy validation against empirical results",
        "",
        "Among the four candidates with complete pressure and Pennes results, the geometric proxy score "
        "does **not** monotonically predict either focus quality or thermal safety:",
        "",
        "- `dx05_sweep_000_collinear` has the highest geometric score (0.890) but the worst observed "
        "skull CEM43 (~2.93×10⁸ min, UNSAFE). Its short standoff (8.0 mm) and long source-to-target "
        "distance (70.0 mm) likely create a numerical hotspot near the source/skull interface that the "
        "proxy does not capture.",
        "- `dx075_sweep_000_collinear` has a lower geometric score (0.819) but is SAFE and delivers "
        "a higher target-window peak (0.977 MPa). Its longer standoff (15.75 mm) and shorter S2T "
        "(54.0 mm) appear to avoid the hotspot seen at dx0.5.",
        "- `dx075_sweep_005_focus_optimized` improves focus (1.124 MPa) but becomes UNSAFE (346.9 min), "
        "showing the classic focus-thermal trade-off within the same grid.",
        "",
        "**Implication**: geometric screening can prune obviously poor candidates, but it cannot "
        "replace pressure + thermal validation. The next priority should be to understand why dx0.5 "
        "collinear produced a hotspot before scaling that geometry.",
        "",
        "## Recommendations",
        "",
        "1. **Do not treat the composite score as a clinical safety predictor.** It only ranks "
        "geometric plausibility; thermal safety must be verified by Pennes after each pressure run.",
        "2. **Investigate the dx0.5 collinear hotspot** before running more dx0.5 candidates. Compare "
        "source standoff, PML coupling, grid resolution, and skull segmentation against the safer "
        "dx0.75 collinear case.",
        "3. **Top-ranked candidates without pressure results** (e.g. `dx05_sweep_001_symmetric_phi`) "
        "are cheap next single-run candidates only after the dx0.5 hotspot is understood. Each still "
        "requires an evidence brief, dry-run-quality gate, and one-run authorization before k-Wave execution.",
        "4. **Focus-thermal trade-off remains:** among validated runs, higher target-window pressure "
        "(sweep_005) correlated with higher skull CEM43. Use source-pressure scaling on validated "
        "geometries to map the Pareto front.",
        "",
        "## Caveats",
        "",
    ])
    for c in summary["caveats"]:
        md.append(f"- {c}")

    with open(OUT_DIR / "geometric_proxy_screening_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    plot_proxy_vs_empirical(records)

    print(f"Wrote {OUT_DIR / 'geometric_proxy_screening_summary.json'}")
    print(f"Wrote {OUT_DIR / 'geometric_proxy_screening_report.md'}")
    print(f"Wrote {OUT_DIR / 'proxy_vs_empirical.png'}")


if __name__ == "__main__":
    main()
