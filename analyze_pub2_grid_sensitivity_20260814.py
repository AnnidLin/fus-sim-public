"""Compare frozen dx0.75 reference vs dx0.5 grid sensitivity (baseline + TR).

Grid sensitivity is evaluated on scalar localization endpoints (target pressure,
peak-to-target distance, target/global ratio) because the two grids have
different voxel counts and cannot be field-differenced directly. The −6 dB focal
volume is reported as pending when absent from the stored metrics.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REF_BASE = ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807" / "baseline"
REF_TR = ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807" / "tr"
CAND_BASE = ROOT / "outputs" / "pub2_250khz_dx0p5_grid_20260814"
CAND_TR = ROOT / "outputs" / "pub2_250khz_dx0p5_grid_tr_20260814" / "tr"
OUTPUT = ROOT / "outputs" / "pub2_250khz_grid_sensitivity_analysis_20260814"
CONTRACT = ROOT / "paper" / "PUB2_VERIFICATION_CONTRACT_20260812.json"

METRICS = ("target_pressure_mpa", "global_peak_mpa", "target_to_global_peak_ratio", "global_peak_to_target_distance_mm")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(ref_metrics: dict[str, Any], cand_metrics: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in METRICS:
        left = float(ref_metrics[key])
        right = float(cand_metrics[key])
        out[key] = {
            "dx0p75": left,
            "dx0p5": right,
            "difference": right - left,
            "relative_difference_percent": None if left == 0 else 100 * (right - left) / abs(left),
        }
    return out


def build() -> dict[str, Any]:
    limits = load(CONTRACT)["acceptance_criteria"]["grid_sensitivity"]["limits"]
    checks: dict[str, bool] = {}
    results: dict[str, Any] = {}
    for method, ref_dir, cand_dir in (("baseline", REF_BASE, CAND_BASE), ("tr", REF_TR, CAND_TR)):
        rm = load(ref_dir / "focus_metrics.json")
        cm = load(cand_dir / "focus_metrics.json")
        cmp = compare(rm, cm)
        results[method] = cmp
        checks[f"{method}_target_pressure_within"] = (
            abs(cmp["target_pressure_mpa"]["relative_difference_percent"]) <= limits["target_pressure_relative_change_percent_max"]
        )
        checks[f"{method}_peak_distance_within"] = (
            abs(cmp["global_peak_to_target_distance_mm"]["difference"]) <= limits["peak_to_target_distance_change_mm_max"]
        )
        checks[f"{method}_ratio_within"] = (
            abs(cmp["target_to_global_peak_ratio"]["difference"]) <= limits["target_to_global_ratio_absolute_change_max"]
        )
    checks["minus6db_volume_compared"] = False  # 标量指标未含 −6 dB 体积；需从场单独计算
    return {
        "schema_version": "1.0",
        "report_id": "pub2_250khz_grid_sensitivity_analysis_20260814",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "claim_level": "single_case_grid_sensitivity_observation",
        "checks": checks,
        "scalar_metrics": results,
        "limits": limits,
        "claim_boundary": "One dx0.75-to-dx0.5 grid perturbation for baseline and TR; does not establish formal convergence, absolute-pressure accuracy, efficacy or safety.",
    }


def main() -> int:
    result = build()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "grid_sensitivity_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = result["scalar_metrics"]
    lines = ["# PUB.2 dx0.75→dx0.5 grid sensitivity", "", f"- Status: **{result['status']}**"]
    for method in ("baseline", "tr"):
        m = s[method]
        lines.append(
            f"- {method}: target pressure {m['target_pressure_mpa']['relative_difference_percent']:+.6g}%, "
            f"peak distance {m['global_peak_to_target_distance_mm']['difference']:+.6g} mm, "
            f"ratio {m['target_to_global_peak_ratio']['difference']:+.6g}"
        )
    lines += ["", result["claim_boundary"], ""]
    (OUTPUT / "grid_sensitivity_analysis.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(OUTPUT)}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
