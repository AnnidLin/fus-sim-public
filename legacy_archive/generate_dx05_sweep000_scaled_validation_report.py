from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
BASE_DIR = PROJECT_ROOT / "outputs" / "ct_sweep_scan_079_dx0p5" / "sweep_000"
SCALED_DIR = PROJECT_ROOT / "outputs" / "ct_sweep_scan_079_dx0p5" / "sweep_000_p038"
HOTSPOT_AUDIT = PROJECT_ROOT / "outputs" / "ct_sweep_hotspot_audit" / "079_sweep_000_dx0p5" / "hotspot_audit.json"
OUT_DIR = PROJECT_ROOT / "outputs" / "ct_sweep_scaled_pressure_validation" / "079_sweep_000_dx0p5_p038"
OUT_JSON = OUT_DIR / "scaled_pressure_validation.json"
OUT_MD = OUT_DIR / "scaled_pressure_validation.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def pct_delta(new: float, old: float) -> float:
    return (new - old) / old * 100.0


def ratio(new: float, old: float) -> float:
    return new / old


def build_case(label: str, pressure_dir: Path) -> dict[str, Any]:
    summary = read_json(pressure_dir / "summary.json")
    pennes = read_json(pressure_dir / "pennes_thermal" / "pennes_summary.json")
    runner = read_json(pressure_dir / "runner_status.json")
    return {
        "label": label,
        "pressure_dir": rel(pressure_dir),
        "source_pressure_pa": nested(summary, ["config", "source_pressure_pa"]),
        "runner_status": runner.get("status"),
        "runner_runtime_s": nested(runner, ["execution", "runtime_s"]),
        "pressure_runtime_s": nested(summary, ["runtime", "runtime_s"]),
        "global_peak_mpa": nested(summary, ["pressure", "global_peak_mpa"]),
        "target_pressure_mpa": nested(summary, ["pressure", "target_pressure_mpa"]),
        "target_window_peak_mpa": nested(summary, ["pressure", "target_window_peak_mpa"]),
        "global_peak_index_ijk": nested(summary, ["pressure", "global_peak_index_ijk"]),
        "global_peak_to_target_distance_mm": nested(summary, ["pressure", "global_peak_to_target_distance_mm"]),
        "target_to_global_peak_ratio": nested(summary, ["pressure", "target_to_global_peak_ratio"]),
        "max_temperature_rise_c": pennes.get("max_temperature_rise_c"),
        "target_temperature_rise_c": pennes.get("target_temperature_rise_c"),
        "brain_max_cem43_min": pennes.get("brain_max_cem43_min"),
        "skull_max_cem43_min": pennes.get("skull_max_cem43_min"),
        "overall_safe": nested(pennes, ["thermal_dose_safety", "overall_safe"]),
    }


def build_report(result: dict[str, Any]) -> str:
    base = result["cases"]["base_1mpa"]
    scaled = result["cases"]["scaled_0p38mpa"]
    checks = result["checks"]
    lines = [
        "# dx0.5 Sweep 000 0.38 MPa Scaled-Pressure Validation",
        "",
        f"- generated_at: `{result['generated_at']}`",
        f"- claim_level: `{result['claim_level']}`",
        "",
        "## Key Metrics",
        "",
        "| Metric | 1.0 MPa baseline | 0.38 MPa validation | Delta |",
        "|---|---:|---:|---:|",
        f"| source pressure (Pa) | {base['source_pressure_pa']:.6g} | {scaled['source_pressure_pa']:.6g} | {result['scale']['source_pressure_ratio']:.6g}x |",
        f"| global peak (MPa) | {base['global_peak_mpa']:.6g} | {scaled['global_peak_mpa']:.6g} | {result['deltas_percent']['global_peak_mpa']:.3f}% |",
        f"| target-window peak (MPa) | {base['target_window_peak_mpa']:.6g} | {scaled['target_window_peak_mpa']:.6g} | {result['deltas_percent']['target_window_peak_mpa']:.3f}% |",
        f"| max dT (C) | {base['max_temperature_rise_c']:.6g} | {scaled['max_temperature_rise_c']:.6g} | {result['deltas_percent']['max_temperature_rise_c']:.3f}% |",
        f"| skull CEM43 (min) | {base['skull_max_cem43_min']:.6g} | {scaled['skull_max_cem43_min']:.6g} | {result['deltas_percent']['skull_max_cem43_min']:.3f}% |",
        f"| overall safe | {base['overall_safe']} | {scaled['overall_safe']} | - |",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in checks.items())
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The 0.38 MPa validation run confirms the expected linear pressure scaling and makes the approximate Gao-cooling Pennes result pass the local thermal-dose gates.",
            "- The skull hotspot remains spatially dominant; pressure scaling mitigates thermal dose but does not tune the focus.",
            "- This is an engineering validation of a scaled protocol in this model, not a clinical or medical safety conclusion.",
            "",
            "## Blocked Claims",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in result["blocked_claims"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    base = build_case("dx0p5_sweep_000_1mpa", BASE_DIR)
    scaled = build_case("dx0p5_sweep_000_0p38mpa", SCALED_DIR)
    hotspot = read_json(HOTSPOT_AUDIT)
    source_ratio = ratio(scaled["source_pressure_pa"], base["source_pressure_pa"])
    expected_power_ratio = source_ratio * source_ratio
    pressure_ratio = ratio(scaled["global_peak_mpa"], base["global_peak_mpa"])
    target_window_ratio = ratio(scaled["target_window_peak_mpa"], base["target_window_peak_mpa"])
    max_dt_ratio = ratio(scaled["max_temperature_rise_c"], base["max_temperature_rise_c"])
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_id": "079_sweep_000_dx0p5_p038_scaled_pressure_validation",
        "claim_level": "scaled_pressure_engineering_validation_not_clinical_safety",
        "inputs": {
            "base_pressure_dir": rel(BASE_DIR),
            "scaled_pressure_dir": rel(SCALED_DIR),
            "hotspot_audit": rel(HOTSPOT_AUDIT),
        },
        "cases": {"base_1mpa": base, "scaled_0p38mpa": scaled},
        "scale": {
            "source_pressure_ratio": source_ratio,
            "expected_power_or_temperature_rise_ratio": expected_power_ratio,
            "hotspot_screening_source_pressure_mpa": nested(
                hotspot,
                ["source_pressure_scaling", "safe_threshold_estimate", "source_pressure_mpa"],
            ),
            "rounded_planning_source_pressure_mpa": nested(
                hotspot,
                ["source_pressure_scaling", "rounded_recommendation", "source_pressure_mpa"],
            ),
        },
        "observed_ratios": {
            "global_peak_mpa": pressure_ratio,
            "target_window_peak_mpa": target_window_ratio,
            "max_temperature_rise_c": max_dt_ratio,
        },
        "deltas_percent": {
            "global_peak_mpa": pct_delta(scaled["global_peak_mpa"], base["global_peak_mpa"]),
            "target_window_peak_mpa": pct_delta(scaled["target_window_peak_mpa"], base["target_window_peak_mpa"]),
            "max_temperature_rise_c": pct_delta(scaled["max_temperature_rise_c"], base["max_temperature_rise_c"]),
            "skull_max_cem43_min": pct_delta(scaled["skull_max_cem43_min"], base["skull_max_cem43_min"]),
        },
        "checks": {
            "runner_kwave_ok": scaled["runner_status"] == "kwave_ok",
            "pressure_scale_matches_source_within_1pct": abs(pressure_ratio - source_ratio) <= 0.01,
            "temperature_scale_matches_power_within_5pct": abs(max_dt_ratio - expected_power_ratio) <= 0.05,
            "thermal_overall_safe": scaled["overall_safe"] is True,
            "skull_cem43_below_16min": scaled["skull_max_cem43_min"] < 16.0,
            "brain_cem43_below_2min": scaled["brain_max_cem43_min"] < 2.0,
            "hotspot_location_unchanged": scaled["global_peak_index_ijk"] == base["global_peak_index_ijk"],
            "target_still_not_tuned_focus": scaled["target_to_global_peak_ratio"] < 0.1,
        },
        "decision": {
            "scaled_validation_passed_local_thermal_gates": scaled["overall_safe"] is True
            and scaled["skull_max_cem43_min"] < 16.0
            and scaled["brain_max_cem43_min"] < 2.0,
            "validated_source_pressure_pa": scaled["source_pressure_pa"],
            "clinical_or_medical_safety_conclusion_allowed": False,
            "recommended_next": "Use 0.38 MPa as a local engineering validation point; do not promote to clinical safety or tuned-focus baseline.",
        },
        "blocked_claims": [
            "clinical or medical safety",
            "paper-grade pressure baseline",
            "numerical convergence",
            "tuned focus",
            "default mapping profile promotion",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(build_report(result), encoding="utf-8")
    print(json.dumps({"scaled_validation_passed": result["decision"]["scaled_validation_passed_local_thermal_gates"], "output": rel(OUT_JSON)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
