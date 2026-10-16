#!/usr/bin/env python3
"""Analyze the fresh PUB.2 baseline/TR reference chain.

This is a pure-analysis command.  It never imports a simulator or launches
k-Wave.  The report separates:

1. execution completeness and preflight provenance;
2. same-method reproducibility against the blocked historical context pair;
3. the fresh baseline-versus-TR engineering contrast.

The historical pair remains context-only because its alpha semantics were not
recorded explicitly.  Agreement with it cannot promote that historical
pressure evidence or establish convergence, efficacy, or safety.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
DEFAULT_FRESH_ROOT = (
    ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807"
)
DEFAULT_HISTORICAL_ROOT = (
    ROOT / "outputs" / "h3_large_full_bowl_matched_standard_20260730"
)
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "pub2_250khz_reference_analysis_20260807"
MODEL_EQUIVALENCE = (
    ROOT
    / "outputs"
    / "pub2_case079_simple_hu300_dx0p75_semantics_20260807"
    / "equivalence"
    / "model_equivalence_audit.json"
)
ENTRY_FAMILY = (
    ROOT
    / "outputs"
    / "pub2_entry_plan_resolution_family_refined_20260807"
    / "entry_plan_resolution_family.json"
)

METHODS = {
    "baseline": ("baseline", "baseline"),
    "time_reversal": ("tr", "tr"),
}
CONFIG_FIELDS = (
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
)
PRESSURE_METRICS = (
    "global_peak_mpa",
    "global_peak_to_target_distance_mm",
    "target_pressure_mpa",
    "target_window_peak_mpa",
    "target_to_global_peak_ratio",
    "effective_peak_mpa",
    "effective_peak_to_target_distance_mm",
    "target_to_effective_peak_ratio",
    "beam_axis_effective_peak_mpa",
    "beam_axis_effective_peak_to_target_distance_mm",
    "target_to_beam_axis_effective_peak_ratio",
    "post_entry_peak_mpa",
    "post_entry_peak_to_target_distance_mm",
    "target_to_post_entry_peak_ratio",
)
INDEX_METRICS = (
    "global_peak_index_ijk",
    "target_window_peak_index_ijk",
    "effective_peak_index_ijk",
    "beam_axis_effective_peak_index_ijk",
    "post_entry_peak_index_ijk",
)
FIELD_METADATA_ARRAYS = (
    "dx_m",
    "target_index_ijk",
    "crop_origin_ijk",
    "source_mask",
    "labels",
    "nearfield_exclusion_m",
    "source_center_index_ijk",
    "beam_axis",
    "entry_index_ijk",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def numeric_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return bool(np.isclose(float(left), float(right), rtol=1e-12, atol=1e-15))
    return left == right


def compare_config(
    fresh: dict[str, Any], historical: dict[str, Any]
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in CONFIG_FIELDS:
        left = fresh.get(key)
        right = historical.get(key)
        fields[key] = {
            "fresh": left,
            "historical": right,
            "equal": numeric_equal(left, right),
        }
    mismatches = [key for key, item in fields.items() if not item["equal"]]
    return {
        "matched": not mismatches,
        "mismatches": mismatches,
        "fields": fields,
        "path_fields_intentionally_compared_by_external_audits": [
            "model_path",
            "entry_plan_path",
        ],
    }


def compare_field_npz(fresh_path: Path, historical_path: Path) -> dict[str, Any]:
    with np.load(fresh_path) as fresh_npz, np.load(historical_path) as old_npz:
        if "pressure_max_mpa" not in fresh_npz or "pressure_max_mpa" not in old_npz:
            raise ValueError("pressure_max_mpa missing from one or both NPZ files")
        fresh = np.asarray(fresh_npz["pressure_max_mpa"], dtype=np.float64)
        old = np.asarray(old_npz["pressure_max_mpa"], dtype=np.float64)
        if fresh.shape != old.shape:
            return {
                "shape_equal": False,
                "fresh_shape": list(fresh.shape),
                "historical_shape": list(old.shape),
                "finite": bool(np.isfinite(fresh).all() and np.isfinite(old).all()),
                "reproducibility_class": "not_comparable_shape_mismatch",
                "metadata_arrays": {},
            }

        finite = bool(np.isfinite(fresh).all() and np.isfinite(old).all())
        delta = fresh - old
        old_l2 = float(np.linalg.norm(old.ravel()))
        old_linf = float(np.max(np.abs(old)))
        abs_l2 = float(np.linalg.norm(delta.ravel()))
        max_abs = float(np.max(np.abs(delta)))
        relative_l2 = abs_l2 / old_l2 if old_l2 > 0 else None
        relative_linf = max_abs / old_linf if old_linf > 0 else None
        bitwise_equal = bool(
            np.array_equal(
                np.asarray(fresh_npz["pressure_max_mpa"]),
                np.asarray(old_npz["pressure_max_mpa"]),
            )
        )
        if not finite:
            reproduction = "invalid_nonfinite"
        elif bitwise_equal:
            reproduction = "bitwise_exact"
        elif (
            relative_l2 is not None
            and relative_linf is not None
            and relative_l2 <= 1e-5
            and relative_linf <= 1e-5
        ):
            reproduction = "numerically_close_1e-5"
        else:
            reproduction = "material_difference_observed"

        metadata: dict[str, Any] = {}
        for key in FIELD_METADATA_ARRAYS:
            fresh_present = key in fresh_npz
            old_present = key in old_npz
            metadata[key] = {
                "fresh_present": fresh_present,
                "historical_present": old_present,
                "equal": (
                    bool(np.array_equal(fresh_npz[key], old_npz[key]))
                    if fresh_present and old_present
                    else False
                ),
            }
        return {
            "shape_equal": True,
            "fresh_shape": list(fresh.shape),
            "historical_shape": list(old.shape),
            "finite": finite,
            "nonzero": bool(np.any(fresh != 0) and np.any(old != 0)),
            "bitwise_equal": bitwise_equal,
            "absolute_l2_mpa": abs_l2,
            "max_absolute_difference_mpa": max_abs,
            "mean_absolute_difference_mpa": float(np.mean(np.abs(delta))),
            "relative_l2": relative_l2,
            "relative_linf": relative_linf,
            "reproducibility_class": reproduction,
            "metadata_arrays": metadata,
            "metadata_arrays_all_equal": all(
                item["equal"] for item in metadata.values()
            ),
        }


def compare_pressure_metrics(
    fresh: dict[str, Any], historical: dict[str, Any]
) -> dict[str, Any]:
    scalar: dict[str, Any] = {}
    for key in PRESSURE_METRICS:
        left = fresh.get(key)
        right = historical.get(key)
        difference = None
        relative_difference = None
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            difference = float(left) - float(right)
            if float(right) != 0:
                relative_difference = difference / float(right)
        scalar[key] = {
            "fresh": left,
            "historical": right,
            "difference": difference,
            "relative_difference": relative_difference,
        }
    indices = {
        key: {
            "fresh": fresh.get(key),
            "historical": historical.get(key),
            "equal": fresh.get(key) == historical.get(key),
        }
        for key in INDEX_METRICS
    }
    return {"scalar": scalar, "indices": indices}


def resolved_chain_status_path(fresh_root: Path) -> Path:
    recovered = fresh_root / "reference_completion_status.json"
    return recovered if recovered.is_file() else fresh_root / "chain_status.json"


def validate_chain(fresh_root: Path) -> dict[str, Any]:
    chain_path = resolved_chain_status_path(fresh_root)
    chain = load_json(chain_path)
    stages = {item.get("stage_id"): item for item in chain.get("stages", [])}
    expected = {"baseline", "tr_calibrate", "tr_refocus"}
    checks = {
        "chain_complete": chain.get("status") == "completed",
        "all_stages_recorded": set(stages) == expected,
        "all_stages_completed": (
            set(stages) == expected
            and all(item.get("status") == "completed" for item in stages.values())
        ),
        "preflight_passed": chain.get("preflight", {}).get("status") == "passed",
        "pressure_scope_exact": set(chain.get("pressure_scope", [])) == expected,
        "no_follow_on_sensitivity_authorized": (
            chain.get("automatic_follow_on_sensitivity_cells_authorized") is False
        ),
    }
    return {
        "path": relative(chain_path),
        "sha256": sha256_file(chain_path),
        "checks": checks,
        "passed": all(checks.values()),
        "stages": stages,
    }


def method_contrast(
    baseline: dict[str, Any], tr: dict[str, Any]
) -> dict[str, Any]:
    keys = (
        "target_to_global_peak_ratio",
        "target_to_effective_peak_ratio",
        "target_to_beam_axis_effective_peak_ratio",
        "global_peak_to_target_distance_mm",
        "effective_peak_to_target_distance_mm",
        "beam_axis_effective_peak_to_target_distance_mm",
    )
    values: dict[str, Any] = {}
    for key in keys:
        base = baseline.get(key)
        refocus = tr.get(key)
        ratio = None
        difference = None
        if isinstance(base, (int, float)) and isinstance(refocus, (int, float)):
            difference = float(refocus) - float(base)
            if float(base) != 0:
                ratio = float(refocus) / float(base)
        values[key] = {
            "baseline": base,
            "time_reversal": refocus,
            "difference": difference,
            "tr_over_baseline": ratio,
        }
    return {
        "normalization_note": (
            "Baseline tone-burst and normalized TR replay have different drive "
            "mechanisms. Cross-method absolute MPa is not treated as directly "
            "comparable; the contrast emphasizes ratios, locations and distances."
        ),
        "metrics": values,
    }


def build_report(
    fresh_root: Path,
    historical_root: Path,
    model_equivalence_path: Path = MODEL_EQUIVALENCE,
    entry_family_path: Path = ENTRY_FAMILY,
) -> dict[str, Any]:
    chain = validate_chain(fresh_root)
    if not chain["passed"]:
        failed = [key for key, value in chain["checks"].items() if not value]
        raise ValueError(f"fresh reference chain is incomplete: {failed}")

    model_equivalence = load_json(model_equivalence_path)
    entry_family = load_json(entry_family_path)
    dx075 = next(
        (
            item
            for item in entry_family.get("candidates", [])
            if item.get("candidate_id") == "dx0p75"
        ),
        None,
    )
    provenance_checks = {
        "model_equivalence_passed": (
            model_equivalence.get("status") == "passed"
            and model_equivalence.get("physical_arrays_equal") is True
            and model_equivalence.get("candidate_alpha_metadata_matches") is True
        ),
        "dx0p75_entry_mapping_exact": (
            dx075 is not None
            and dx075.get("diagnostics", {}).get("passed") is True
            and dx075["diagnostics"].get("source_physical_error_mm") == 0
            and dx075["diagnostics"].get("target_physical_error_mm") == 0
            and dx075["diagnostics"].get("source_target_distance_delta_mm") == 0
            and dx075["diagnostics"].get("beam_angle_delta_deg") == 0
        ),
    }

    methods: dict[str, Any] = {}
    fresh_pressures: dict[str, dict[str, Any]] = {}
    for method, (fresh_subdir, old_subdir) in METHODS.items():
        fresh_dir = fresh_root / fresh_subdir
        old_dir = historical_root / old_subdir
        fresh_summary_path = fresh_dir / "summary.json"
        old_summary_path = old_dir / "summary.json"
        fresh_field_path = fresh_dir / "pressure_max_mpa.npz"
        old_field_path = old_dir / "pressure_max_mpa.npz"
        required = (
            fresh_summary_path,
            old_summary_path,
            fresh_field_path,
            old_field_path,
        )
        missing = [relative(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(f"{method}: missing required inputs: {missing}")
        fresh_summary = load_json(fresh_summary_path)
        old_summary = load_json(old_summary_path)
        fresh_pressure = fresh_summary.get("pressure", {})
        old_pressure = old_summary.get("pressure", {})
        fresh_pressures[method] = fresh_pressure
        methods[method] = {
            "fresh": {
                "summary_path": relative(fresh_summary_path),
                "summary_sha256": sha256_file(fresh_summary_path),
                "field_path": relative(fresh_field_path),
                "field_sha256": sha256_file(fresh_field_path),
            },
            "historical_context_only": {
                "summary_path": relative(old_summary_path),
                "summary_sha256": sha256_file(old_summary_path),
                "field_path": relative(old_field_path),
                "field_sha256": sha256_file(old_field_path),
                "reuse_blocker": "missing_explicit_alpha_semantics",
            },
            "configuration": compare_config(
                fresh_summary.get("config", {}), old_summary.get("config", {})
            ),
            "field_reproducibility": compare_field_npz(
                fresh_field_path, old_field_path
            ),
            "pressure_metrics": compare_pressure_metrics(
                fresh_pressure, old_pressure
            ),
        }

    execution_valid = chain["passed"] and all(provenance_checks.values())
    outputs_valid = all(
        item["field_reproducibility"].get("finite") is True
        and item["field_reproducibility"].get("nonzero") is True
        and item["configuration"].get("matched") is True
        for item in methods.values()
    )
    return {
        "schema_version": "1.0",
        "report_id": "pub2_250khz_reference_analysis_20260807",
        "generated_at_utc": utc_now(),
        "status": "passed" if execution_valid and outputs_valid else "failed",
        "claim_level": "engineering_reference_method_evidence",
        "execution": chain,
        "provenance": {
            "checks": provenance_checks,
            "model_equivalence": {
                "path": relative(model_equivalence_path),
                "sha256": sha256_file(model_equivalence_path),
            },
            "entry_family": {
                "path": relative(entry_family_path),
                "sha256": sha256_file(entry_family_path),
            },
        },
        "same_method_historical_reproducibility": methods,
        "fresh_method_contrast": method_contrast(
            fresh_pressures["baseline"], fresh_pressures["time_reversal"]
        ),
        "decision": {
            "fresh_reference_pair_valid": execution_valid and outputs_valid,
            "historical_pair_promoted": False,
            "automatic_sensitivity_pressure_authorized": False,
            "next_gate": (
                "Review the fresh reference contrast and post-execution gap "
                "feedback before authorizing any single-variable pressure cell."
            ),
        },
        "claim_boundary": (
            "This report establishes execution integrity, same-method numerical "
            "reproducibility and a matched baseline/TR engineering contrast only. "
            "The historical pair remains context-only because its alpha semantics "
            "were not explicit. No result establishes clinical safety, thermal "
            "safety, efficacy, numerical convergence or paper-grade validity."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PUB.2 250 kHz fresh reference-pair analysis",
        "",
        f"- Status: `{report['status']}`",
        f"- Claim level: `{report['claim_level']}`",
        "- Historical pressure evidence remains context-only.",
        "- Automatic follow-on sensitivity pressure is **not authorized**.",
        "",
        "## Same-method historical reproducibility",
        "",
        "| Method | Config matched | Field class | rel L2 | rel Linf | Metadata arrays |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for method, item in report["same_method_historical_reproducibility"].items():
        field = item["field_reproducibility"]
        rel_l2 = field.get("relative_l2")
        rel_linf = field.get("relative_linf")
        lines.append(
            "| "
            + " | ".join(
                [
                    method,
                    str(item["configuration"]["matched"]),
                    str(field.get("reproducibility_class")),
                    "—" if rel_l2 is None else f"{rel_l2:.6e}",
                    "—" if rel_linf is None else f"{rel_linf:.6e}",
                    str(field.get("metadata_arrays_all_equal")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Fresh baseline versus time reversal",
            "",
            "| Metric | Baseline | TR | Difference | TR / baseline |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for key, item in report["fresh_method_contrast"]["metrics"].items():
        values = [
            key,
            item["baseline"],
            item["time_reversal"],
            item["difference"],
            item["tr_over_baseline"],
        ]
        lines.append(
            "| "
            + " | ".join(
                str(value) if value is not None else "—" for value in values
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            report["fresh_method_contrast"]["normalization_note"],
            "",
            report["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-root", type=Path, default=DEFAULT_FRESH_ROOT)
    parser.add_argument(
        "--historical-root", type=Path, default=DEFAULT_HISTORICAL_ROOT
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--model-equivalence", type=Path, default=MODEL_EQUIVALENCE
    )
    parser.add_argument("--entry-family", type=Path, default=ENTRY_FAMILY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_report(
            args.fresh_root,
            args.historical_root,
            args.model_equivalence,
            args.entry_family,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "reference_pair_analysis.json"
    md_path = args.output_dir / "reference_pair_analysis.md"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "json": str(json_path)}))
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
