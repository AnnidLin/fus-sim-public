from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
BASELINE_DIR = (
    ROOT / "outputs" / "factorial_250khz_trajectory_transducer_20260729"
    / "h3_large"
)
TR_DIR = ROOT / "outputs" / "case079_h3_tr_250khz_20260728"
OUTPUT_DIR = ROOT / "outputs" / "h3_large_matched_baseline_tr_20260730"

SHARED_CONFIG_FIELDS = (
    "model_path",
    "entry_plan_path",
    "frequency_hz",
    "source_pressure_pa",
    "transducer_radius_m",
    "aperture_diameter_m",
    "tone_burst_cycles",
    "cfl",
    "simulation_time_s",
    "pml_size",
    "preset",
    "backend",
    "device",
    "quick_mode",
    "quick_lateral_half_width_m",
    "quick_post_target_margin_m",
    "alpha_power",
    "nearfield_exclusion_m",
    "allow_entry_plan_resolution_mismatch",
)
TR_SHARED_CONFIG_FIELDS = ("calibration_pressure_pa", "normalize_source")
MODEL_FIELDS = ("model_shape", "crop_origin_ijk", "target_index_ijk")
SOURCE_FIELDS = ("source_points", "source_label_counts")
BASELINE_ARTIFACTS = ("summary.json", "pressure_max_mpa.npz", "focus_metrics.json")
TR_ARTIFACTS = (
    "summary_calibrate.json",
    "element_signals.npz",
    "summary.json",
    "pressure_max_mpa.npz",
    "focus_metrics.json",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_recorded_path(root: Path, recorded: str) -> Path:
    normalized = recorded.replace("\\", "/")
    path = Path(normalized)
    return path if path.is_absolute() else root / path


def model_metadata(summary: dict[str, Any]) -> dict[str, Any]:
    nested = summary.get("model")
    source = nested if isinstance(nested, dict) else summary
    return {field: source.get(field) for field in MODEL_FIELDS}


def compare_values(
    prefix: str,
    fields: tuple[str, ...],
    baseline: dict[str, Any],
    calibration: dict[str, Any],
    refocus: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    drift: dict[str, dict[str, Any]] = {}
    for field in fields:
        values = (
            baseline.get(field),
            calibration.get(field),
            refocus.get(field),
        )
        if not (values[0] == values[1] == values[2]):
            drift[f"{prefix}.{field}"] = {
                "baseline": values[0],
                "tr_calibration": values[1],
                "tr_refocus": values[2],
            }
    return drift


def artifact_manifest(
    baseline_dir: Path, tr_dir: Path
) -> tuple[bool, dict[str, dict[str, Any]]]:
    manifest: dict[str, dict[str, Any]] = {}
    for arm, directory, names in (
        ("baseline", baseline_dir, BASELINE_ARTIFACTS),
        ("tr", tr_dir, TR_ARTIFACTS),
    ):
        for name in names:
            path = directory / name
            key = f"{arm}/{name}"
            exists = path.is_file()
            manifest[key] = {
                "path": str(path),
                "exists": exists,
                "size_bytes": path.stat().st_size if exists else None,
                "sha256": sha256_file(path) if exists else None,
            }
    return all(item["exists"] for item in manifest.values()), manifest


def ordinary_change(baseline: float, tr: float) -> dict[str, float]:
    return {
        "baseline": baseline,
        "tr": tr,
        "absolute_change": tr - baseline,
        "relative_change": tr / baseline - 1.0,
        "factor": tr / baseline,
    }


def distance_change(baseline: float, tr: float) -> dict[str, float]:
    return {
        "baseline": baseline,
        "tr": tr,
        "absolute_change": tr - baseline,
        "reduction": baseline - tr,
        "relative_reduction": 1.0 - tr / baseline,
    }


def build_report(
    root: Path = ROOT,
    baseline_dir: Path = BASELINE_DIR,
    tr_dir: Path = TR_DIR,
    module: str = "freq250_h3_large_matched_baseline_tr_20260730",
    claim_level: str = "matched_quick_engineering_reuse",
    expected_model_shape: list[int] | None = None,
    expected_source_points: int | None = None,
    require_tr_normalize: bool = False,
    historical_pressure_reuse: bool = True,
) -> dict[str, Any]:
    baseline = load_json(baseline_dir / "summary.json")
    calibration = load_json(tr_dir / "summary_calibrate.json")
    refocus = load_json(tr_dir / "summary.json")

    drift = compare_values(
        "config",
        SHARED_CONFIG_FIELDS,
        baseline["config"],
        calibration["config"],
        refocus["config"],
    )
    drift.update(
        compare_values(
            "model",
            MODEL_FIELDS,
            model_metadata(baseline),
            model_metadata(calibration),
            model_metadata(refocus),
        )
    )
    for field in TR_SHARED_CONFIG_FIELDS:
        values = (calibration["config"].get(field), refocus["config"].get(field))
        if values[0] != values[1]:
            drift[f"tr_config.{field}"] = {
                "tr_calibration": values[0],
                "tr_refocus": values[1],
            }
    if require_tr_normalize and not (
        calibration["config"].get("normalize_source") is True
        and refocus["config"].get("normalize_source") is True
    ):
        drift["tr_config.normalize_source_required"] = {
            "tr_calibration": calibration["config"].get("normalize_source"),
            "tr_refocus": refocus["config"].get("normalize_source"),
            "expected": True,
        }
    drift.update(
        compare_values(
            "source",
            SOURCE_FIELDS,
            baseline["source"],
            calibration["source"],
            refocus["source"],
        )
    )

    label_counts = baseline["source"].get("source_label_counts")
    background_only = all(
        isinstance(summary["source"].get("source_label_counts"), dict)
        and set(summary["source"]["source_label_counts"]) == {"0"}
        and int(summary["source"]["source_label_counts"]["0"])
        == int(summary["source"]["source_points"])
        for summary in (baseline, calibration, refocus)
    )
    if not background_only:
        drift["source.background_only"] = {
            "baseline": label_counts,
            "expected": "only label 0 with count equal to source_points",
        }
    actual_model_shape = model_metadata(baseline)["model_shape"]
    if (
        expected_model_shape is not None
        and actual_model_shape != expected_model_shape
    ):
        drift["model.expected_shape"] = {
            "actual": actual_model_shape,
            "expected": expected_model_shape,
        }
    actual_source_points = baseline["source"].get("source_points")
    if (
        expected_source_points is not None
        and actual_source_points != expected_source_points
    ):
        drift["source.expected_points"] = {
            "actual": actual_source_points,
            "expected": expected_source_points,
        }

    complete, manifest = artifact_manifest(baseline_dir, tr_dir)
    config = baseline["config"]
    input_manifest: dict[str, dict[str, Any]] = {}
    for name, field in (("model", "model_path"), ("entry_plan", "entry_plan_path")):
        path = resolve_recorded_path(root, str(config[field]))
        exists = path.is_file()
        input_manifest[name] = {
            "recorded_path": config[field],
            "resolved_path": str(path),
            "exists": exists,
            "size_bytes": path.stat().st_size if exists else None,
            "sha256": sha256_file(path) if exists else None,
        }
        if not exists:
            drift[f"input.{name}"] = {
                "recorded_path": config[field],
                "error": "missing",
            }

    baseline_pressure = baseline["pressure"]
    tr_pressure = refocus["pressure"]
    comparison = {
        "target_to_global_peak_ratio": ordinary_change(
            float(baseline_pressure["target_to_global_peak_ratio"]),
            float(tr_pressure["target_to_global_peak_ratio"]),
        ),
        "target_window_peak_mpa": ordinary_change(
            float(baseline_pressure["target_window_peak_mpa"]),
            float(tr_pressure["target_window_peak_mpa"]),
        ),
        "global_peak_mpa": ordinary_change(
            float(baseline_pressure["global_peak_mpa"]),
            float(tr_pressure["global_peak_mpa"]),
        ),
        "global_peak_to_target_distance_mm": distance_change(
            float(baseline_pressure["global_peak_to_target_distance_mm"]),
            float(tr_pressure["global_peak_to_target_distance_mm"]),
        ),
    }
    equivalent = not drift
    reusable = equivalent and complete
    reused_historical_pressure = reusable and historical_pressure_reuse
    return {
        "report_version": "1.0.0",
        "module": module,
        "claim_level": claim_level,
        "inputs": input_manifest,
        "equivalence": {
            "valid": equivalent,
            "shared_config_fields_checked": list(SHARED_CONFIG_FIELDS),
            "model_fields_checked": list(MODEL_FIELDS),
            "source_fields_checked": list(SOURCE_FIELDS),
            "tr_config_fields_checked": list(TR_SHARED_CONFIG_FIELDS),
            "background_only_source": background_only,
            "expected_model_shape": expected_model_shape,
            "expected_source_points": expected_source_points,
            "tr_normalize_required": require_tr_normalize,
            "drift": drift,
        },
        "artifacts": {"complete": complete, "files": manifest},
        "comparison": comparison,
        "decision": {
            "reuse_historical_pressure": reused_historical_pressure,
            "new_pressure_execution_required": not reusable,
            "reason": (
                "Strict equivalence and artifact completeness passed; "
                + (
                    "historical pressure reuse is valid."
                    if historical_pressure_reuse
                    else "the completed fresh pressure execution is valid."
                )
                if reusable
                else "Equivalence or completeness failed; do not compare as matched."
            ),
        },
        "blocked_claims": [
            "paper-grade numerical convergence",
            "clinical efficacy or safety",
            "thermal or dosing conclusions",
            "multi-case generalization",
        ],
    }


def report_markdown(report: dict[str, Any]) -> str:
    comparison = report["comparison"]
    ratio = comparison["target_to_global_peak_ratio"]
    target = comparison["target_window_peak_mpa"]
    global_peak = comparison["global_peak_mpa"]
    distance = comparison["global_peak_to_target_distance_mm"]
    claim_level = str(report["claim_level"])
    if claim_level == "matched_standard_intermediate_domain_engineering_evidence":
        result_heading = "## Matched standard intermediate-domain result"
        boundary = (
            "This is a matched standard-preset, full-bowl intermediate-domain "
            "engineering analysis from a fresh pressure execution. It is not "
            "full-domain or paper-grade convergence, clinical efficacy/safety, "
            "thermal evidence, or multi-case generalization."
        )
    else:
        result_heading = "## Matched quick-preset result"
        boundary = (
            "This is a matched quick-preset engineering reuse analysis. It is not "
            "paper-grade convergence, clinical efficacy/safety, thermal evidence, "
            "or multi-case generalization."
        )
    return "\n".join(
        [
            "# H3-large 250 kHz matched baseline–TR comparison",
            "",
            f"- Claim level: `{claim_level}`",
            f"- Strict equivalence: `{report['equivalence']['valid']}`",
            f"- Core artifacts complete: `{report['artifacts']['complete']}`",
            f"- Historical pressure reused: `{report['decision']['reuse_historical_pressure']}`",
            f"- New pressure execution required: `{report['decision']['new_pressure_execution_required']}`",
            "",
            result_heading,
            "",
            (
                f"- Target/global ratio: {ratio['baseline']:.6f} → "
                f"{ratio['tr']:.6f} ({ratio['factor']:.3f}×)"
            ),
            (
                f"- Target-window peak: {target['baseline']:.6f} → "
                f"{target['tr']:.6f} MPa ({target['relative_change']:+.1%})"
            ),
            (
                f"- Global peak: {global_peak['baseline']:.6f} → "
                f"{global_peak['tr']:.6f} MPa ({global_peak['relative_change']:+.1%})"
            ),
            (
                f"- Global-peak distance to target: {distance['baseline']:.3f} → "
                f"{distance['tr']:.3f} mm "
                f"(reduction {distance['reduction']:.3f} mm)"
            ),
            "",
            "## Boundary",
            "",
            boundary,
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a strict matched H3-large baseline–TR comparison."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE_DIR)
    parser.add_argument("--tr-dir", type=Path, default=TR_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--module",
        default="freq250_h3_large_matched_baseline_tr_20260730",
    )
    parser.add_argument(
        "--claim-level",
        default="matched_quick_engineering_reuse",
    )
    parser.add_argument("--expected-grid", type=int, nargs=3)
    parser.add_argument("--expected-source-points", type=int)
    parser.add_argument("--require-tr-normalize", action="store_true")
    parser.add_argument("--fresh-pressure-execution", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        root=args.root,
        baseline_dir=args.baseline_dir,
        tr_dir=args.tr_dir,
        module=args.module,
        claim_level=args.claim_level,
        expected_model_shape=args.expected_grid,
        expected_source_points=args.expected_source_points,
        require_tr_normalize=args.require_tr_normalize,
        historical_pressure_reuse=not args.fresh_pressure_execution,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "matched_comparison.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "matched_comparison.md").write_text(
        report_markdown(report), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "equivalence_valid": report["equivalence"]["valid"],
                "artifacts_complete": report["artifacts"]["complete"],
                "reuse_historical_pressure": report["decision"][
                    "reuse_historical_pressure"
                ],
                "new_pressure_execution_required": report["decision"][
                    "new_pressure_execution_required"
                ],
            }
        )
    )
    return 0 if (
        report["equivalence"]["valid"] and report["artifacts"]["complete"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
