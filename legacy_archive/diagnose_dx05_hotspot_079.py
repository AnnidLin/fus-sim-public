"""
Case 079 dx0.5 collinear hotspot root-cause diagnosis.

Read-only comparison between dx0.5 sweep_000 and dx0.75 sweep_000,
using their summaries, entry plans, and the existing dx0.5 hotspot audit.
No k-Wave execution.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs/dx05_hotspot_diagnosis_079"

CASES = {
    "dx075": {
        "summary": "outputs/ct_sweep_scan_079_dx0p75/sweep_000/summary.json",
        "entry_plan": "outputs/ct_sweep_scan_079_dx0p75/sweep_000/entry_plan.json",
        "thermal": "outputs/ct_sweep_scan_079_dx0p75/sweep_000/pennes_thermal/pennes_summary.json",
    },
    "dx05": {
        "summary": "outputs/ct_sweep_scan_079_dx0p5/sweep_000/summary.json",
        "entry_plan": "outputs/ct_sweep_scan_079_dx0p5/sweep_000/entry_plan.json",
        "thermal": "outputs/ct_sweep_scan_079_dx0p5/sweep_000/pennes_thermal/pennes_summary.json",
        "hotspot_audit": "outputs/ct_sweep_hotspot_audit/079_sweep_000_dx0p5/hotspot_audit.json",
    },
}


def load_json(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def thermal_safe_status(t: dict[str, Any]) -> dict[str, Any]:
    safety = t.get("thermal_dose_safety", {})
    return {
        "overall_safe": safety.get("overall_safe"),
        "brain_status": safety.get("brain_safety", {}).get("status"),
        "skull_status": safety.get("skull_safety", {}).get("status"),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data = {k: {kk: load_json(vv) for kk, vv in paths.items()} for k, paths in CASES.items()}

    # Build comparison record
    comparison = {}
    for case, d in data.items():
        cfg = d["summary"].get("config", {})
        src = d["summary"].get("source", {})
        pm = d["summary"].get("pressure", {})
        t = d["thermal"]
        entry = d["entry_plan"]
        rt = d["summary"].get("runtime", {})
        sq = d["summary"].get("simulation_quality", {})

        comparison[case] = {
            "dx_mm": round(d["summary"].get("dx_m", 0) * 1000, 3),
            "model_shape_cropped": d["summary"].get("model_shape", []),
            "source_model_shape": d["summary"].get("source_model_shape", []),
            "frequency_hz": cfg.get("frequency_hz"),
            "source_pressure_pa": cfg.get("source_pressure_pa"),
            "transducer_radius_m": cfg.get("transducer_radius_m"),
            "aperture_diameter_m": cfg.get("aperture_diameter_m"),
            "tone_burst_cycles": cfg.get("tone_burst_cycles"),
            "cfl": cfg.get("cfl"),
            "pml_size": cfg.get("pml_size"),
            "pml_thickness_mm": cfg.get("pml_size", 0) * d["summary"].get("dx_m", 0) * 1000,
            "simulation_time_s": cfg.get("simulation_time_s"),
            "nt": rt.get("nt"),
            "dt_s": rt.get("dt_s"),
            "runtime_s": rt.get("runtime_s"),
            "ppw_min": sq.get("ppw_min_sound_speed"),
            "source_points": src.get("source_points"),
            "radius_grid_points": src.get("radius_grid_points"),
            "diameter_grid_points": src.get("diameter_grid_points"),
            "source_center_index_ijk": src.get("source_center_index_ijk"),
            "entry_index_ijk": src.get("entry_index_ijk"),
            "source_standoff_mm": entry.get("source_standoff_mm"),
            "source_to_target_distance_mm": entry.get("source_to_target_distance_mm"),
            "skull_path_length_mm": entry.get("skull_path_length_mm"),
            "entry_direction": entry.get("entry_direction"),
            "global_peak_mpa": pm.get("global_peak_mpa"),
            "target_window_peak_mpa": pm.get("target_window_peak_mpa"),
            "target_pressure_mpa": pm.get("target_pressure_mpa"),
            "global_peak_to_target_distance_mm": pm.get("global_peak_to_target_distance_mm"),
            "max_temperature_rise_c": t.get("max_temperature_rise_c"),
            "skull_max_cem43_min": t.get("skull_max_cem43_min"),
            "brain_max_cem43_min": t.get("brain_max_cem43_min"),
            **thermal_safe_status(t),
        }

    # Extract hotspot info for dx0.5
    hotspot = data["dx05"].get("hotspot_audit", {}).get("hotspots", [])
    hotspot_summary = {}
    for h in hotspot:
        if h["name"] == "pressure_global_peak":
            hotspot_summary = {
                "crop_index_ijk": h["crop_index_ijk"],
                "model_index_ijk": h["model_index_ijk"],
                "material": h["material"],
                "pressure_mpa": h["pressure_mpa"],
                "temperature_rise_c": h["temperature_rise_c"],
                "cem43_min": h["cem43_min"],
                "distance_to_source_mm": h["distance_to_source_mm"],
                "distance_to_entry_mm": h["distance_to_entry_mm"],
                "axial_from_source_mm": h["axial_from_source_mm"],
                "axial_shortfall_to_target_mm": h["axial_shortfall_to_target_mm"],
                "hu": h["hu"],
                "sound_speed_m_s": h["sound_speed_m_s"],
                "alpha_db_mhz_cm": h["alpha_db_mhz_cm"],
            }
            break

    # Root-cause hypotheses with evidence
    dx05 = comparison["dx05"]
    dx75 = comparison["dx075"]

    hypotheses = [
        {
            "id": "H1",
            "hypothesis": "dx0.5 source standoff is too short, placing the high-intensity near-field directly inside the skull bone",
            "evidence_for": [
                f"dx0.5 standoff = {dx05['source_standoff_mm']:.2f} mm vs dx0.75 standoff = {dx75['source_standoff_mm']:.2f} mm",
                f"dx0.5 hotspot is only {hotspot_summary.get('distance_to_source_mm', 0):.2f} mm from source center",
                f"dx0.5 entry_index is {dx05['entry_index_ijk']}, only {(dx05['entry_index_ijk'][0] - dx05['source_center_index_ijk'][0]) * dx05['dx_mm']:.2f} mm from source center",
            ],
            "evidence_against": [],
            "diagnostic_action": "Increase standoff to >=12 mm in a new dx0.5 entry plan and run dry-run-quality only; do not run pressure until geometry is reviewed.",
            "likelihood": "high",
        },
        {
            "id": "H2",
            "hypothesis": "dx0.5 longer source-to-target distance (70 mm) increases focal gain and hotspot intensity before the target",
            "evidence_for": [
                f"dx0.5 S2T = {dx05['source_to_target_distance_mm']:.1f} mm vs dx0.75 S2T = {dx75['source_to_target_distance_mm']:.1f} mm",
                "Global peak in dx0.5 is 55.5 mm from target, near the skull segment, not at the geometric focus.",
            ],
            "evidence_against": [
                "Longer S2T usually reduces target pressure due to attenuation, not increase it; the hotspot is more likely a near-source effect.",
            ],
            "diagnostic_action": "Compare axial pressure profiles along beam axis for both grids to see where peak forms.",
            "likelihood": "medium",
        },
        {
            "id": "H3",
            "hypothesis": "Higher grid resolution in dx0.5 resolves a sharper skull hotspot that was smeared out in dx0.75",
            "evidence_for": [
                f"dx0.5 PPW = {dx05['ppw_min']:.1f} vs dx0.75 PPW = {dx75['ppw_min']:.1f}",
                f"dx0.5 source has {dx05['source_points']} points vs dx0.75 {dx75['source_points']} points",
                "Hotspot peak pressure 9.64 MPa in dx0.5 vs 11.89 MPa in dx0.75, but dx0.5 temperature rise is much larger (9.55°C vs 2.15°C).",
            ],
            "evidence_against": [
                "Higher resolution should improve accuracy, not create a non-physical 10^8-fold CEM43 increase unless the coarse result missed a real hotspot.",
            ],
            "diagnostic_action": "Run dx0.75 with the same standoff/S2T as dx0.5 (if anatomically feasible) to isolate resolution effect.",
            "likelihood": "medium",
        },
        {
            "id": "H4",
            "hypothesis": "dx0.5 skull_path_length (4.5 mm) is longer than dx0.75 (0.75 mm), depositing more energy in skull bone",
            "evidence_for": [
                f"dx0.5 skull_path_length_mm = {dx05['skull_path_length_mm']:.2f} vs dx0.75 = {dx75['skull_path_length_mm']:.2f}",
                "Hotspot is located inside the first skull segment along the beam axis.",
            ],
            "evidence_against": [
                "4.5 mm is within the 'ideal' geometric range; the real issue is the hotspot location relative to the source, not the absolute path length.",
            ],
            "diagnostic_action": "Compute heat deposition per unit skull volume along the beam axis for both cases.",
            "likelihood": "low",
        },
    ]

    # Summary JSON
    summary = {
        "analysis_id": "case_079_dx05_hotspot_diagnosis",
        "analysis_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim_level": "engineering_diagnostic_not_root_cause_validation",
        "comparison": comparison,
        "hotspot_summary": hotspot_summary,
        "hypotheses": hypotheses,
        "primary_recommendation": {
            "root_cause": "Most likely H1 (short source standoff) compounded by H3 (higher grid resolution resolving a sharper hotspot)",
            "immediate_action": "Do not run more dx0.5 candidates with 8 mm standoff. Generate a new dx0.5 entry plan with standoff >=12 mm and review dry-run-quality before any pressure execution.",
            "validation_required": "A single dx0.5 pressure run with increased standoff, followed by Pennes, to test H1.",
        },
    }

    with open(OUT_DIR / "dx05_hotspot_diagnosis_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Markdown report
    md = [
        "# Case 079 dx0.5 Collinear Hotspot Root-Cause Diagnosis",
        "",
        f"- **Version**: `{summary['analysis_version']}`",
        f"- **Generated**: `{summary['generated_at']}`",
        f"- **Claim level**: `{summary['claim_level']}`",
        "",
        "## Parameter comparison: dx0.5 vs dx0.75 collinear",
        "",
        "| Parameter | dx0.75 sweep_000 | dx0.5 sweep_000 | Delta |",
        "|---|---|---|---|",
    ]

    keys = [
        ("dx_mm", "%.2f"),
        ("model_shape_cropped", "%s"),
        ("source_model_shape", "%s"),
        ("source_points", "%d"),
        ("radius_grid_points", "%d"),
        ("diameter_grid_points", "%d"),
        ("ppw_min", "%.1f"),
        ("nt", "%d"),
        ("runtime_s", "%.0f"),
        ("source_standoff_mm", "%.2f"),
        ("source_to_target_distance_mm", "%.1f"),
        ("skull_path_length_mm", "%.2f"),
        ("pml_size", "%d"),
        ("pml_thickness_mm", "%.2f"),
        ("global_peak_mpa", "%.3f"),
        ("target_window_peak_mpa", "%.3f"),
        ("global_peak_to_target_distance_mm", "%.1f"),
        ("max_temperature_rise_c", "%.2f"),
        ("skull_max_cem43_min", "%.3f"),
        ("overall_safe", "%s"),
    ]

    for key, fmt in keys:
        v75 = dx75[key]
        v05 = dx05[key]
        if isinstance(v75, list):
            s75 = str(v75)
            s05 = str(v05)
            delta = "-"
        elif isinstance(v75, bool) or v75 is None:
            s75 = str(v75)
            s05 = str(v05)
            delta = "-"
        else:
            s75 = fmt % v75
            s05 = fmt % v05
            try:
                delta = fmt % (v05 - v75)
            except Exception:
                delta = "-"
        md.append(f"| {key} | {s75} | {s05} | {delta} |")

    md.extend([
        "",
        "## dx0.5 hotspot location",
        "",
        "| Quantity | Value |",
        "|---|---|",
    ])
    for k, v in hotspot_summary.items():
        if isinstance(v, float):
            md.append(f"| {k} | {v:.3f} |")
        else:
            md.append(f"| {k} | {v} |")

    md.extend([
        "",
        "## Root-cause hypotheses",
        "",
    ])
    for h in hypotheses:
        md.extend([
            f"### {h['id']}: {h['hypothesis']}",
            "",
            f"**Likelihood**: {h['likelihood']}",
            "",
            "**Evidence for**:",
        ])
        for e in h["evidence_for"]:
            md.append(f"- {e}")
        if h["evidence_against"]:
            md.append("\n**Evidence against**:")
            for e in h["evidence_against"]:
                md.append(f"- {e}")
        md.extend([
            "",
            f"**Diagnostic action**: {h['diagnostic_action']}",
            "",
        ])

    md.extend([
        "## Primary conclusion",
        "",
        f"**Most likely root cause**: {summary['primary_recommendation']['root_cause']}.",
        "",
        f"**Immediate action**: {summary['primary_recommendation']['immediate_action']}",
        "",
        f"**Validation required**: {summary['primary_recommendation']['validation_required']}",
        "",
        "## Claim boundaries",
        "",
        "- This diagnosis is read-only and based on existing summaries and hotspot audit.",
        "- It does not prove the root cause; only a new controlled k-Wave run can validate H1.",
        "- Any follow-up k-Wave run requires an evidence brief, dry-run-quality gate, and explicit user authorization.",
    ])

    with open(OUT_DIR / "dx05_hotspot_diagnosis_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"Wrote {OUT_DIR / 'dx05_hotspot_diagnosis_summary.json'}")
    print(f"Wrote {OUT_DIR / 'dx05_hotspot_diagnosis_report.md'}")


if __name__ == "__main__":
    main()
