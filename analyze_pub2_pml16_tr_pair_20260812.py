"""Analyze the matched PML12/PML16 baseline and time-reversal fields."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from analyze_pub2_pml16_baseline_20260810 import (
    METRIC_KEYS,
    common_views,
    compare_configs,
    load_field,
    load_json,
    sha256,
)

ROOT = Path(__file__).resolve().parent
PML12_ROOT = ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807"
PML16_BASELINE = ROOT / "outputs" / "pub2_250khz_pml16_baseline_20260810"
PML16_TR_ROOT = ROOT / "outputs" / "pub2_250khz_pml16_tr_20260811"
PML16_TR = PML16_TR_ROOT / "tr"
OUTPUT = ROOT / "outputs" / "pub2_250khz_pml16_tr_analysis_20260812"


def metric_comparison(left: dict[str, Any], right: dict[str, Any], left_name: str, right_name: str) -> dict[str, Any]:
    result = {}
    for key in METRIC_KEYS:
        a, b = float(left[key]), float(right[key])
        delta = b - a
        result[key] = {left_name: a, right_name: b, "difference": delta, "relative_difference": None if a == 0 else delta / abs(a)}
    return result


def pml_comparison(pml12_dir: Path, pml16_dir: Path) -> dict[str, Any]:
    summary12, summary16 = load_json(pml12_dir / "summary.json"), load_json(pml16_dir / "summary.json")
    metrics12, metrics16 = load_json(pml12_dir / "focus_metrics.json"), load_json(pml16_dir / "focus_metrics.json")
    field12, field16 = load_field(pml12_dir / "pressure_max_mpa.npz"), load_field(pml16_dir / "pressure_max_mpa.npz")
    view12, view16, alignment = common_views(field12, field16)
    difference = view16.astype(np.float64) - view12.astype(np.float64)
    norm12 = float(np.linalg.norm(view12.astype(np.float64).ravel()))
    max12 = float(np.max(np.abs(view12)))
    target12 = (field12["origin"] + field12["target"]).tolist()
    target16 = (field16["origin"] + field16["target"]).tolist()
    config = compare_configs(summary12["config"], summary16["config"])
    checks = {
        "only_pml_size_changed": config["only_pml_size_changed"],
        "dx_equal": field12["dx_m"] == field16["dx_m"],
        "target_equal": target12 == target16,
        "source_points_equal_4971": field12["source_points"] == field16["source_points"] == 4971,
        "pml12_domain_fully_covered": alignment["shape"] == list(field12["field"].shape),
        "finite_nonzero": bool(np.isfinite(view12).all() and np.isfinite(view16).all() and np.max(view16) > 0),
    }
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "configuration": config,
        "coordinate_alignment": alignment,
        "field_difference": {
            "relative_l2": None if norm12 == 0 else float(np.linalg.norm(difference.ravel())) / norm12,
            "relative_linf": None if max12 == 0 else float(np.max(np.abs(difference))) / max12,
            "max_absolute_difference_mpa": float(np.max(np.abs(difference))),
            "mean_absolute_difference_mpa": float(np.mean(np.abs(difference))),
        },
        "scalar_metrics": metric_comparison(metrics12, metrics16, "pml12", "pml16"),
        "artifacts": {
            "pml12_sha256": sha256(pml12_dir / "pressure_max_mpa.npz"),
            "pml16_sha256": sha256(pml16_dir / "pressure_max_mpa.npz"),
        },
    }


def build_report() -> dict[str, Any]:
    chain = load_json(PML16_TR_ROOT / "chain_status.json")
    baseline = pml_comparison(PML12_ROOT / "baseline", PML16_BASELINE)
    tr = pml_comparison(PML12_ROOT / "tr", PML16_TR)
    baseline16_metrics = load_json(PML16_BASELINE / "focus_metrics.json")
    tr16_metrics = load_json(PML16_TR / "focus_metrics.json")
    contrast16 = metric_comparison(baseline16_metrics, tr16_metrics, "baseline", "tr")
    checks = {
        "pml16_chain_completed": chain.get("status") == "completed" and len(chain.get("results", [])) == 2,
        "pml16_stages_valid": all(item.get("status") == "completed" and item.get("output_validation", {}).get("status") == "passed" for item in chain.get("results", [])),
        "baseline_pml_comparison_passed": baseline["status"] == "passed",
        "tr_pml_comparison_passed": tr["status"] == "passed",
    }
    return {
        "schema_version": "1.0",
        "report_id": "pub2_250khz_pml16_tr_analysis_20260812",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "claim_level": "single_case_paired_single_variable_boundary_sensitivity_observation",
        "checks": checks,
        "pml12_vs_pml16": {"baseline": baseline, "tr": tr},
        "pml16_baseline_vs_tr": {"scalar_metrics": contrast16},
        "decision": {"matched_pml16_pair_complete": all(checks.values()), "formal_convergence_established": False, "efficacy_or_safety_established": False},
        "claim_boundary": "One Case079 paired PML12-versus-PML16 observation for baseline and TR; engineering evidence only, not formal convergence, efficacy or safety evidence.",
    }


def main() -> int:
    report = build_report()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "paired_pml_analysis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    base = report["pml12_vs_pml16"]["baseline"]["field_difference"]
    tr = report["pml12_vs_pml16"]["tr"]["field_difference"]
    contrast = report["pml16_baseline_vs_tr"]["scalar_metrics"]
    lines = [
        "# PUB.2 paired PML sensitivity analysis", "",
        f"- Status: **{report['status']}**",
        f"- Baseline PML12→16 relative L2: `{base['relative_l2']:.8g}`",
        f"- TR PML12→16 relative L2: `{tr['relative_l2']:.8g}`",
        f"- PML16 target/global ratio, baseline→TR: `{contrast['target_to_global_peak_ratio']['baseline']:.8g}` → `{contrast['target_to_global_peak_ratio']['tr']:.8g}`",
        f"- PML16 peak-to-target distance, baseline→TR: `{contrast['global_peak_to_target_distance_mm']['baseline']:.8g}` → `{contrast['global_peak_to_target_distance_mm']['tr']:.8g}` mm",
        "", report["claim_boundary"], "",
    ]
    (OUTPUT / "paired_pml_analysis.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "json": str(OUTPUT / "paired_pml_analysis.json")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
