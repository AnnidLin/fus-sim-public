from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/ct_grid_convergence_analysis/079_candidate_006"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pct_change(new: float, old: float) -> float:
    if old == 0:
        return 0.0
    return (new - old) / old * 100.0


def metrics(summary: dict[str, Any]) -> dict[str, Any]:
    pressure = summary["pressure"]
    quality = summary["simulation_quality"]
    runtime = summary["runtime"]
    return {
        "dx_mm": quality["dx_mm"],
        "pml_size": quality["pml_size"],
        "cfl": quality["cfl"],
        "grid_size": quality["grid_size"],
        "nt": quality["nt"],
        "ppw_min_sound_speed": quality["ppw_min_sound_speed"],
        "runtime_s": runtime["runtime_s"],
        "global_peak_mpa": pressure["global_peak_mpa"],
        "target_window_peak_mpa": pressure["target_window_peak_mpa"],
        "target_pressure_mpa": pressure["target_pressure_mpa"],
        "effective_peak_to_target_distance_mm": pressure["effective_peak_to_target_distance_mm"],
        "target_to_effective_peak_ratio": pressure["target_to_effective_peak_ratio"],
    }


def resolution_status(summary: dict[str, Any]) -> dict[str, Any]:
    entry_plan = summary.get("entry_plan") or {}
    model_shape = summary.get("source_model_shape")
    entry_dx = entry_plan.get("dx_m")
    entry_shape = entry_plan.get("model_shape")
    model_dx = summary.get("dx_m")
    dx_matches = entry_dx is not None and model_dx is not None and abs(float(entry_dx) - float(model_dx)) <= 1e-9
    shape_matches = entry_shape is not None and model_shape is not None and list(entry_shape) == list(model_shape)
    return {
        "entry_plan_dx_m": entry_dx,
        "model_dx_m": model_dx,
        "entry_plan_model_shape": entry_shape,
        "model_shape": model_shape,
        "dx_matches": dx_matches,
        "shape_matches": shape_matches,
        "compatible": dx_matches and shape_matches,
    }


def build_report() -> dict[str, Any]:
    dx075_path = PROJECT_ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/summary.json"
    dx05_path = PROJECT_ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p5_pml12_cfl0p2_standard/summary.json"
    dx075 = metrics(read_json(dx075_path))
    dx075_summary = read_json(dx075_path)
    dx05_summary = read_json(dx05_path)
    dx075 = metrics(dx075_summary)
    dx05 = metrics(dx05_summary)
    dx075_resolution = resolution_status(dx075_summary)
    dx05_resolution = resolution_status(dx05_summary)
    resolution_compatible = dx075_resolution["compatible"] and dx05_resolution["compatible"]
    comparison = {
        "global_peak_pct_change_dx0p5_vs_dx0p75": pct_change(dx05["global_peak_mpa"], dx075["global_peak_mpa"]),
        "target_window_peak_pct_change_dx0p5_vs_dx0p75": pct_change(
            dx05["target_window_peak_mpa"], dx075["target_window_peak_mpa"]
        ),
        "target_pressure_pct_change_dx0p5_vs_dx0p75": pct_change(dx05["target_pressure_mpa"], dx075["target_pressure_mpa"]),
        "effective_peak_distance_delta_mm": dx05["effective_peak_to_target_distance_mm"]
        - dx075["effective_peak_to_target_distance_mm"],
        "runtime_pct_change_dx0p5_vs_dx0p75": pct_change(dx05["runtime_s"], dx075["runtime_s"]),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "ct_grid_convergence_analysis",
        "case_id": "079",
        "candidate_id": "candidate_006",
        "profile": "simple_hu300",
        "claim_level": (
            "engineering_grid_convergence_observation"
            if resolution_compatible
            else "coordinate_mapping_diagnostic_not_grid_convergence"
        ),
        "inputs": {
            "dx0p75_summary": rel(dx075_path),
            "dx0p5_summary": rel(dx05_path),
        },
        "dx0p75": dx075,
        "dx0p5": dx05,
        "entry_plan_resolution_gate": {
            "compatible": resolution_compatible,
            "dx0p75": dx075_resolution,
            "dx0p5": dx05_resolution,
            "decision": (
                "comparison_allowed"
                if resolution_compatible
                else "comparison_blocked_entry_plan_resolution_mismatch"
            ),
        },
        "comparison": comparison,
        "interpretation": (
            [
                "The finer dx0.5 cropped-domain run changes pressure metrics materially versus dx0.75.",
                "This is an engineering grid-convergence observation, not paper-grade evidence by itself.",
                "Paper-grade, medical/safety, and profile-promotion claims remain blocked.",
            ]
            if resolution_compatible
            else [
                "The entry plan was generated at a different dx/model_shape than the compared acoustic models.",
                "The dx0.5 cropped-domain run contains no skull material in its material ranges, so the pressure deltas cannot be interpreted as grid convergence.",
                "Treat this output as a coordinate-mapping diagnostic finding only.",
                "Regenerate or transform the entry plan for each target acoustic model resolution before any further grid-convergence pressure run.",
            ]
        ),
        "not_executed": [
            "thermal simulation",
            "paper-grade run",
            "profile/default promotion",
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    dx075 = report["dx0p75"]
    dx05 = report["dx0p5"]
    comp = report["comparison"]
    lines = [
        "# CT Grid-Convergence Analysis - Case 079 / Candidate 006",
        "",
        "- profile: `simple_hu300`",
        f"- claim level: `{report['claim_level']}`",
        f"- entry-plan resolution gate: `{report['entry_plan_resolution_gate']['decision']}`",
        "",
        "## Run Metrics",
        "",
        "| Run | dx mm | PML | CFL | Grid | nt | PPW | Runtime s | Global MPa | Target-window MPa | Target MPa | Peak-target distance mm |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| dx0.75 baseline | {dx075['dx_mm']:.3f} | {dx075['pml_size']} | {dx075['cfl']} | "
            f"{'x'.join(str(v) for v in dx075['grid_size'])} | {dx075['nt']} | "
            f"{dx075['ppw_min_sound_speed']:.3f} | {dx075['runtime_s']:.1f} | "
            f"{dx075['global_peak_mpa']:.4f} | {dx075['target_window_peak_mpa']:.4f} | "
            f"{dx075['target_pressure_mpa']:.4f} | {dx075['effective_peak_to_target_distance_mm']:.3f} |"
        ),
        (
            f"| dx0.5 finer-grid | {dx05['dx_mm']:.3f} | {dx05['pml_size']} | {dx05['cfl']} | "
            f"{'x'.join(str(v) for v in dx05['grid_size'])} | {dx05['nt']} | "
            f"{dx05['ppw_min_sound_speed']:.3f} | {dx05['runtime_s']:.1f} | "
            f"{dx05['global_peak_mpa']:.4f} | {dx05['target_window_peak_mpa']:.4f} | "
            f"{dx05['target_pressure_mpa']:.4f} | {dx05['effective_peak_to_target_distance_mm']:.3f} |"
        ),
        "",
        "## Relative Change",
        "",
        f"- global peak: `{comp['global_peak_pct_change_dx0p5_vs_dx0p75']:.2f}%`",
        f"- target-window peak: `{comp['target_window_peak_pct_change_dx0p5_vs_dx0p75']:.2f}%`",
        f"- target pressure: `{comp['target_pressure_pct_change_dx0p5_vs_dx0p75']:.2f}%`",
        f"- effective peak distance delta: `{comp['effective_peak_distance_delta_mm']:.3f} mm`",
        f"- runtime change: `{comp['runtime_pct_change_dx0p5_vs_dx0p75']:.2f}%`",
        "",
        "## Interpretation Boundary",
        "",
    ]
    lines.extend(f"- {item}" for item in report["interpretation"])
    lines.extend(["", "## Entry-Plan Resolution Gate", ""])
    gate = report["entry_plan_resolution_gate"]
    for run_id in ("dx0p75", "dx0p5"):
        item = gate[run_id]
        lines.append(
            f"- {run_id}: entry dx `{item['entry_plan_dx_m']}`, model dx `{item['model_dx_m']}`, "
            f"entry shape `{item['entry_plan_model_shape']}`, model shape `{item['model_shape']}`, "
            f"compatible `{item['compatible']}`"
        )
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in report["not_executed"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    json_path = OUT_DIR / "ct_grid_convergence_analysis.json"
    md_path = OUT_DIR / "ct_grid_convergence_analysis.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {rel(json_path)}")
    print(f"Wrote {rel(md_path)}")


if __name__ == "__main__":
    main()
