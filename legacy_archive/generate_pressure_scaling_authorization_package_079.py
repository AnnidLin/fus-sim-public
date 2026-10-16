"""
Generate one-run authorization package for dx0.75 sweep_005 source-pressure scaling sweep.

Plans single k-Wave pressure runs at 0.5, 0.6, 0.7, 0.8 MPa using the same geometry
and grid as the existing dx0.75 sweep_005 (focus-optimized) run. Each run must be
authorized individually; this package only prepares evidence and commands.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/one_run_authorization_package/079_sweep_005_pressure_scaling"
BRIEF_DIR = PROJECT_ROOT / "outputs/evidence_briefs/pressure_scaling_sweep_079"

HARD_STOP_MIN = 120  # sweep_005 took ~100 min; allow headroom
CHECKPOINT_MIN = 2

PRESSURE_LEVELS_MPA = [0.5, 0.6, 0.7, 0.8]

BASELINE_SUMMARY_PATH = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005/summary.json"
BASELINE_THERMAL_PATH = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005/pennes_thermal/pennes_summary.json"
ENTRY_PLAN_PATH = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005/entry_plan.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pressure_scaling_predictions(baseline_pressure_mpa: float, baseline_tw_mpa: float,
                                  baseline_skull_cem43: float) -> dict[str, Any]:
    """Linear pressure scaling predictions for thermal screening only."""
    predictions = {}
    for p in PRESSURE_LEVELS_MPA:
        scale = p / baseline_pressure_mpa
        power_scale = scale ** 2
        predictions[f"{p:.2f}_MPa"] = {
            "source_pressure_mpa": p,
            "scale_factor": round(scale, 4),
            "power_scale_factor": round(power_scale, 4),
            "predicted_target_window_peak_mpa": round(baseline_tw_mpa * scale, 4),
            "predicted_skull_cem43_min": round(baseline_skull_cem43 * power_scale, 4),
            "predicted_overall_safe_heuristic": bool(baseline_skull_cem43 * power_scale < 16.0),
        }
    return predictions


def build_runner_command(level_mpa: float, baseline_cfg: dict[str, Any]) -> list[str]:
    """Build a runner command for one pressure level by overriding source pressure."""
    cmd = [
        "D:/AIprogram/python-envs/kwave312/Scripts/python.exe",
        "run_kwave_command.py",
        "--execute",
        "--model-path", str(baseline_cfg.get("model_path", "")).replace("\\", "/"),
        "--entry-plan-path", rel(ENTRY_PLAN_PATH),
        "--frequency", str(baseline_cfg.get("frequency_hz", 500000.0)),
        "--source-pressure-pa", str(int(level_mpa * 1e6)),
        "--transducer-radius", str(baseline_cfg.get("transducer_radius_m", 0.03)),
        "--aperture-diameter", str(baseline_cfg.get("aperture_diameter_m", 0.025)),
        "--tone-burst-cycles", str(baseline_cfg.get("tone_burst_cycles", 6)),
        "--cfl", str(baseline_cfg.get("cfl", 0.2)),
        "--simulation-time", str(baseline_cfg.get("simulation_time_s", 8.5e-5)),
        "--pml-size", str(baseline_cfg.get("pml_size", 12)),
        "--preset", str(baseline_cfg.get("preset", "standard")),
        "--backend", str(baseline_cfg.get("backend", "python")),
        "--alpha-power", str(baseline_cfg.get("alpha_power", 1.5)),
        "--nearfield-exclusion", str(baseline_cfg.get("nearfield_exclusion_m", 0.01)),
        "--output-dir", f"outputs/ct_sweep_scan_079_dx0p75/sweep_005_p{int(level_mpa*1000):03d}",
        "--checkpoint-min", str(CHECKPOINT_MIN),
        "--hard-stop-min", str(HARD_STOP_MIN),
    ]
    return cmd


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)

    baseline = read_json(BASELINE_SUMMARY_PATH) or {}
    baseline_thermal = read_json(BASELINE_THERMAL_PATH) or {}
    entry_plan = read_json(ENTRY_PLAN_PATH) or {}

    cfg = baseline.get("config", {})
    pm = baseline.get("pressure", {})
    runtime = baseline.get("runtime", {})
    sq = baseline.get("simulation_quality", {})

    baseline_pressure_mpa = cfg.get("source_pressure_pa", 1e6) / 1e6
    baseline_tw_mpa = pm.get("target_window_peak_mpa", 0.0)
    baseline_skull_cem43 = baseline_thermal.get("skull_max_cem43_min", 0.0)
    baseline_runtime_s = runtime.get("runtime_s", 6041.0)

    predictions = pressure_scaling_predictions(
        baseline_pressure_mpa, baseline_tw_mpa, baseline_skull_cem43
    )

    # Build per-level authorization items
    levels = []
    for p in PRESSURE_LEVELS_MPA:
        pred = predictions[f"{p:.2f}_MPa"]
        output_dir = f"outputs/ct_sweep_scan_079_dx0p75/sweep_005_p{int(p*1000):03d}"
        levels.append({
            "level_id": f"sweep_005_p{int(p*1000):03d}",
            "source_pressure_mpa": p,
            "source_pressure_pa": int(p * 1e6),
            "predicted_target_window_peak_mpa": pred["predicted_target_window_peak_mpa"],
            "predicted_skull_cem43_min": pred["predicted_skull_cem43_min"],
            "predicted_overall_safe_heuristic": pred["predicted_overall_safe_heuristic"],
            "expected_runtime_s": round(baseline_runtime_s, 1),
            "expected_runtime_min": round(baseline_runtime_s / 60.0, 1),
            "hard_stop_min": HARD_STOP_MIN,
            "checkpoint_min": CHECKPOINT_MIN,
            "output_dir": output_dir,
            "runner_command": build_runner_command(p, cfg),
            "pressure_execution_authorized_now": False,
        })

    # Evidence brief
    brief = {
        "brief_type": "evidence_brief_pre_execution",
        "module": "pressure_scaling_sweep_079",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "question": "Can we map the focus-thermal Pareto front for the dx0.75 sweep_005 focus-optimized geometry by scaling source pressure?",
        "context": {
            "baseline_run": "outputs/ct_sweep_scan_079_dx0p75/sweep_005",
            "baseline_source_pressure_mpa": baseline_pressure_mpa,
            "baseline_target_window_peak_mpa": baseline_tw_mpa,
            "baseline_skull_cem43_min": baseline_skull_cem43,
            "baseline_overall_safe": (baseline_thermal.get("thermal_dose_safety") or {}).get("overall_safe"),
            "baseline_runtime_s": baseline_runtime_s,
            "geometry": {
                "entry_direction": entry_plan.get("entry_direction"),
                "source_standoff_mm": entry_plan.get("source_standoff_mm"),
                "source_to_target_distance_mm": entry_plan.get("source_to_target_distance_mm"),
                "skull_path_length_mm": entry_plan.get("skull_path_length_mm"),
                "dx_mm": entry_plan.get("dx_m", 0) * 1000,
            },
            "numerical_quality": {
                "preset": sq.get("preset"),
                "dx_mm": sq.get("dx_mm"),
                "ppw_min": sq.get("ppw_min_sound_speed"),
                "cfl": sq.get("cfl"),
                "pml_size": sq.get("pml_size"),
                "grid_size": sq.get("grid_size"),
                "evidence_level": sq.get("evidence_level"),
                "is_paper_grade": sq.get("is_paper_grade"),
            },
        },
        "proposed_levels": levels,
        "predictions": predictions,
        "evidence_for": [
            "Baseline sweep_005 at 1.0 MPa is the focus-optimized geometry with the highest target-window peak (1.124 MPa).",
            "Scaling source pressure should reduce both target pressure and heat source quadratically, moving along the focus-thermal trade-off curve.",
            "Same grid, entry plan, and material model as baseline minimizes confounding variables.",
        ],
        "evidence_against": [
            "Baseline sweep_005 at 1.0 MPa is already thermally UNSAFE (skull CEM43 346.9 min).",
            "Prediction assumes linear pressure scaling and quadratic thermal scaling; nonlinear acoustics or grid artifacts may deviate.",
            "No grid convergence or paper-grade status; results remain engineering validation only.",
        ],
        "risks": [
            "Each run costs ~100 minutes CPU time and ~same memory as baseline.",
            "Pressure levels >0.6 MPa may still exceed thermal safety limits.",
            "Output directory conflicts if previous partial outputs exist.",
        ],
        "recommendation": "Run the levels sequentially from lowest pressure (0.5 MPa) upward, stopping if a level is thermally safe and focus is acceptable. Do not batch-run all levels simultaneously.",
        "gap_feedback_location": "outputs/evidence_briefs/pressure_scaling_sweep_079/gap_feedback.json",
    }

    with open(BRIEF_DIR / "evidence_brief.json", "w", encoding="utf-8") as f:
        json.dump(brief, f, indent=2, ensure_ascii=False)
    with open(BRIEF_DIR / "evidence_brief.md", "w", encoding="utf-8") as f:
        f.write(f"# Evidence Brief: Pressure Scaling Sweep for 079 sweep_005\n\n")
        f.write(f"**Generated**: {brief['generated_at']}\n\n")
        f.write(f"## Question\n\n{brief['question']}\n\n")
        f.write("## Proposed levels\n\n")
        f.write("| Level | Pressure (MPa) | Predicted target P (MPa) | Predicted skull CEM43 (min) | Heuristic safe | Expected runtime |\n")
        f.write("|---|---|---|---|---|---|\n")
        for lvl in levels:
            safe_str = "Yes" if lvl["predicted_overall_safe_heuristic"] else "No"
            f.write(
                f"| {lvl['level_id']} | {lvl['source_pressure_mpa']:.2f} | "
                f"{lvl['predicted_target_window_peak_mpa']:.3f} | "
                f"{lvl['predicted_skull_cem43_min']:.3f} | {safe_str} | "
                f"{lvl['expected_runtime_min']:.1f} min |\n"
            )
        f.write("\n## Recommendation\n\n" + brief["recommendation"] + "\n")
        f.write("\n## Risks\n\n")
        for r in brief["risks"]:
            f.write(f"- {r}\n")

    # Authorization package
    package = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "one_run_authorization_package",
        "scope": "source-pressure scaling sweep for dx0.75 sweep_005 focus-optimized geometry",
        "baseline_run": rel(BASELINE_SUMMARY_PATH.parent),
        "pressure_execution_allowed_now": False,
        "requires_user_authorization": True,
        "total_levels_planned": len(levels),
        "execution_policy": "sequential_one_by_one",
        "recommended_first_level": levels[0]["level_id"],
        "levels": levels,
        "evidence_brief": rel(BRIEF_DIR / "evidence_brief.json"),
        "notes": [
            "Each level uses the same grid/geometry as sweep_005; only source_pressure_pa changes.",
            "Predictions are heuristic; Pennes thermal must be run after each pressure result.",
            "Do not execute all levels simultaneously; review each result before authorizing the next.",
        ],
    }

    with open(OUT_DIR / "authorization_package.json", "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2, ensure_ascii=False)

    # Simple runner script helper
    with open(OUT_DIR / "run_all_levels.ps1", "w", encoding="utf-8") as f:
        f.write("# Requires explicit user authorization before running each level.\n")
        f.write("# Run sequentially, not in parallel.\n\n")
        for lvl in levels:
            f.write(f"# Level: {lvl['level_id']}\n")
            f.write("$cmd = @(\n")
            for part in lvl["runner_command"]:
                f.write(f"    '{part}'\n")
            f.write(")\n")
            f.write("& $cmd[0] $cmd[1..($cmd.Length-1)]\n\n")

    print(f"Wrote {BRIEF_DIR / 'evidence_brief.json'}")
    print(f"Wrote {BRIEF_DIR / 'evidence_brief.md'}")
    print(f"Wrote {OUT_DIR / 'authorization_package.json'}")
    print(f"Wrote {OUT_DIR / 'run_all_levels.ps1'}")


if __name__ == "__main__":
    main()
