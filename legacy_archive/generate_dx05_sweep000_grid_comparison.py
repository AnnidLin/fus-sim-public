from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs" / "ct_sweep_grid_convergence_analysis" / "079_sweep_000_dx075_vs_dx05"
OUT_JSON = OUT_DIR / "grid_comparison.json"
OUT_MD = OUT_DIR / "grid_comparison.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def pct_delta(new: float | None, old: float | None) -> float | None:
    if old in (None, 0) or new is None:
        return None
    return (new - old) / old * 100.0


def build_case(label: str, pressure_dir: Path) -> dict[str, Any]:
    summary = read_json(pressure_dir / "summary.json")
    pennes = read_json(pressure_dir / "pennes_thermal" / "pennes_summary.json")
    return {
        "label": label,
        "pressure_dir": rel(pressure_dir),
        "dx_mm": nested(summary, ["simulation_quality", "dx_mm"]),
        "grid_size": nested(summary, ["simulation_quality", "grid_size"]),
        "nt": nested(summary, ["simulation_quality", "nt"]),
        "runtime_s": nested(summary, ["runtime", "runtime_s"]),
        "global_peak_mpa": nested(summary, ["pressure", "global_peak_mpa"]),
        "target_pressure_mpa": nested(summary, ["pressure", "target_pressure_mpa"]),
        "target_window_peak_mpa": nested(summary, ["pressure", "target_window_peak_mpa"]),
        "target_to_global_peak_ratio": nested(summary, ["pressure", "target_to_global_peak_ratio"]),
        "global_peak_to_target_distance_mm": nested(summary, ["pressure", "global_peak_to_target_distance_mm"]),
        "target_window_peak_axial_shortfall_to_target_mm": nested(
            summary,
            ["pressure", "target_window_peak_axial_shortfall_to_target_mm"],
        ),
        "max_temperature_rise_c": pennes.get("max_temperature_rise_c"),
        "target_temperature_rise_c": pennes.get("target_temperature_rise_c"),
        "brain_max_cem43_min": pennes.get("brain_max_cem43_min"),
        "skull_max_cem43_min": pennes.get("skull_max_cem43_min"),
        "overall_safe": nested(pennes, ["thermal_dose_safety", "overall_safe"]),
    }


def build_report(result: dict[str, Any]) -> str:
    coarse = result["cases"]["dx0p75"]
    fine = result["cases"]["dx0p5"]
    deltas = result["deltas_dx0p5_vs_dx0p75_percent"]
    lines = [
        "# dx0.75 vs dx0.5 Sweep 000 Grid Comparison",
        "",
        f"- generated_at: `{result['generated_at']}`",
        f"- claim_level: `{result['claim_level']}`",
        "",
        "## Key Metrics",
        "",
        "| Metric | dx0.75 sweep_000 | dx0.5 sweep_000 | dx0.5 vs dx0.75 |",
        "|---|---:|---:|---:|",
        f"| target-window peak (MPa) | {coarse['target_window_peak_mpa']:.6g} | {fine['target_window_peak_mpa']:.6g} | {deltas['target_window_peak_mpa']:.3f}% |",
        f"| target pressure (MPa) | {coarse['target_pressure_mpa']:.6g} | {fine['target_pressure_mpa']:.6g} | {deltas['target_pressure_mpa']:.3f}% |",
        f"| global peak (MPa) | {coarse['global_peak_mpa']:.6g} | {fine['global_peak_mpa']:.6g} | {deltas['global_peak_mpa']:.3f}% |",
        f"| target/global ratio | {coarse['target_to_global_peak_ratio']:.6g} | {fine['target_to_global_peak_ratio']:.6g} | {deltas['target_to_global_peak_ratio']:.3f}% |",
        f"| global peak distance to target (mm) | {coarse['global_peak_to_target_distance_mm']:.6g} | {fine['global_peak_to_target_distance_mm']:.6g} | {deltas['global_peak_to_target_distance_mm']:.3f}% |",
        f"| max temperature rise (C) | {coarse['max_temperature_rise_c']:.6g} | {fine['max_temperature_rise_c']:.6g} | {deltas['max_temperature_rise_c']:.3f}% |",
        f"| skull max CEM43 (min) | {coarse['skull_max_cem43_min']:.6g} | {fine['skull_max_cem43_min']:.6g} | {deltas['skull_max_cem43_min']:.3f}% |",
        f"| runtime (s) | {coarse['runtime_s']:.6g} | {fine['runtime_s']:.6g} | {deltas['runtime_s']:.3f}% |",
        "",
        "## Interpretation",
        "",
        "- The finer dx0.5 run does not support a simple convergence claim: target-window pressure decreases while the near-skull/global hotspot remains dominant.",
        "- The dx0.5 thermal result is unsafe under the same approximate Pennes protocol, with a much larger localized skull dose.",
        "- Treat this as a grid-sensitivity and hotspot-diagnostics observation, not as paper-grade numerical convergence or clinical safety evidence.",
        "",
        "## Blocked Claims",
        "",
    ]
    lines.extend(f"- {item}" for item in result["blocked_claims"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    dx075_dir = PROJECT_ROOT / "outputs" / "ct_sweep_scan_079_dx0p75" / "sweep_000"
    dx05_dir = PROJECT_ROOT / "outputs" / "ct_sweep_scan_079_dx0p5" / "sweep_000"
    coarse = build_case("dx0p75_sweep_000", dx075_dir)
    fine = build_case("dx0p5_sweep_000", dx05_dir)
    metrics = [
        "target_window_peak_mpa",
        "target_pressure_mpa",
        "global_peak_mpa",
        "target_to_global_peak_ratio",
        "global_peak_to_target_distance_mm",
        "target_window_peak_axial_shortfall_to_target_mm",
        "max_temperature_rise_c",
        "target_temperature_rise_c",
        "brain_max_cem43_min",
        "skull_max_cem43_min",
        "runtime_s",
    ]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_id": "079_sweep_000_dx075_vs_dx05_grid_sensitivity",
        "claim_level": "grid_sensitivity_hotspot_diagnostic_not_convergence",
        "cases": {"dx0p75": coarse, "dx0p5": fine},
        "deltas_dx0p5_vs_dx0p75_percent": {
            metric: pct_delta(fine.get(metric), coarse.get(metric)) for metric in metrics
        },
        "decision": {
            "numerical_convergence_demonstrated": False,
            "thermal_safety_consistent_across_grid": False,
            "recommended_next": "Audit material/pressure hotspot localization and consider source-pressure scaling before any paper-grade grid convergence claim.",
        },
        "blocked_claims": [
            "numerical convergence",
            "paper-grade pressure baseline",
            "clinical or medical safety conclusion",
            "default mapping profile promotion",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(build_report(result), encoding="utf-8")
    print(json.dumps({"analysis_valid": True, "output": rel(OUT_JSON)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
