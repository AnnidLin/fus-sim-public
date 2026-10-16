from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from public_case_source_policy import classify_source_materials


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "outputs" / "matched_frequency_method_inventory_20260726"


@dataclass(frozen=True)
class CellSpec:
    case_id: str
    frequency_hz: int
    method: str
    summary_path: str | None
    model_path: str
    entry_plan_path: str

    @property
    def cell_id(self) -> str:
        return f"{self.case_id}_{self.frequency_hz // 1000}khz_{self.method}"


CASE_INPUTS = {
    "nlm_72m": {
        "model": "outputs/nlm_ct_acoustic_model_affine_simple_hu300_dx0p75_20260723/acoustic_model_3d.npz",
        "entry": "outputs/nlm_ct_entry_plan_left_x_20260723/entry_plan.json",
    },
    "case079": {
        "model": "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/acoustic_model_3d.npz",
        "entry": "outputs/entry_plan_079_offset_y+5_z0/entry_plan.json",
    },
}

SUMMARY_PATHS = {
    ("nlm_72m", 250_000, "baseline"): "outputs/nlm_kwave_quick_250khz_20260724/summary.json",
    ("nlm_72m", 250_000, "tr"): "outputs/nlm_tr_72m_250khz_20260724/summary.json",
    ("nlm_72m", 500_000, "baseline"): "outputs/nlm_kwave_quick_20260724/summary.json",
    ("nlm_72m", 500_000, "tr"): "outputs/nlm_tr_72m_20260724/summary.json",
    ("case079", 250_000, "baseline"): "outputs/case079_kwave_quick_250khz_20260724/summary.json",
    ("case079", 250_000, "tr"): "outputs/case079_tr_250khz_20260724/summary.json",
    ("case079", 500_000, "baseline"): None,
    ("case079", 500_000, "tr"): None,
}

REFERENCE_ONLY = {
    "case079_500khz_baseline_ap30_r35_standard": (
        "outputs/thick_skull_candidate_runs/"
        "079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_pressure_20260710/"
        "summary.json"
    ),
    "case079_500khz_tr_ap30_r35_standard": "outputs/time_reversal_079_y+5_z0/summary.json",
}


def normalize_path(value: str | None) -> str:
    return "" if value is None else value.replace("\\", "/").lower()


def expected_config(spec: CellSpec) -> dict[str, Any]:
    return {
        "frequency_hz": spec.frequency_hz,
        "aperture_diameter_m": 0.015,
        "transducer_radius_m": 0.03,
        "preset": "quick",
        "pml_size": 8,
        "cfl": 0.2,
        "source_pressure_pa": 1_000_000.0,
        "tone_burst_cycles": 6 if spec.method == "baseline" else 2,
        "model_path": spec.model_path,
        "entry_plan_path": spec.entry_plan_path,
    }


def compare_config(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    numeric_fields = (
        "frequency_hz",
        "aperture_diameter_m",
        "transducer_radius_m",
        "pml_size",
        "cfl",
        "source_pressure_pa",
        "tone_burst_cycles",
    )
    for field in numeric_fields:
        actual_value = actual.get(field)
        if actual_value is None or abs(float(actual_value) - float(expected[field])) > 1e-9:
            mismatches.append(field)
    if actual.get("preset") != expected["preset"]:
        mismatches.append("preset")
    for field in ("model_path", "entry_plan_path"):
        if normalize_path(actual.get(field)) != normalize_path(expected[field]):
            mismatches.append(field)
    return mismatches


def load_summary(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: summary root must be an object")
    if not isinstance(value.get("config"), dict):
        raise ValueError(f"{path}: config is missing")
    if not isinstance(value.get("source"), dict):
        raise ValueError(f"{path}: source is missing")
    return value


def audit_cell(spec: CellSpec, root: Path = ROOT) -> dict[str, Any]:
    expected = expected_config(spec)
    if spec.summary_path is None:
        return {
            "cell_id": spec.cell_id,
            "case_id": spec.case_id,
            "frequency_hz": spec.frequency_hz,
            "method": spec.method,
            "status": "missing",
            "summary_path": None,
            "mismatched_fields": [],
            "expected_config": expected,
        }

    path = root / spec.summary_path
    if not path.is_file():
        result = audit_cell(
            CellSpec(
                spec.case_id,
                spec.frequency_hz,
                spec.method,
                None,
                spec.model_path,
                spec.entry_plan_path,
            ),
            root,
        )
        result["summary_path"] = spec.summary_path
        return result

    summary = load_summary(path)
    mismatches = compare_config(summary["config"], expected)
    source_counts = summary["source"].get("source_label_counts")
    if not isinstance(source_counts, dict):
        raise ValueError(f"{path}: source_label_counts are missing")
    pressure = summary.get("pressure", {})
    quality = summary.get("simulation_quality", {})
    return {
        "cell_id": spec.cell_id,
        "case_id": spec.case_id,
        "frequency_hz": spec.frequency_hz,
        "method": spec.method,
        "status": "present_match" if not mismatches else "present_mismatch",
        "summary_path": spec.summary_path,
        "mismatched_fields": mismatches,
        "expected_config": expected,
        "actual_config": {
            field: summary["config"].get(field)
            for field in expected
        },
        "simulation_time_s": summary["config"].get("simulation_time_s"),
        "source_material_semantics": classify_source_materials(source_counts),
        "source_label_counts": source_counts,
        "screening_only": quality.get("screening_only"),
        "paper_grade": quality.get("is_paper_grade"),
        "runtime_s": quality.get("runtime_s"),
        "metrics": {
            "global_peak_mpa": pressure.get("global_peak_mpa"),
            "target_window_peak_mpa": pressure.get("target_window_peak_mpa"),
            "target_to_global_peak_ratio": pressure.get("target_to_global_peak_ratio"),
        },
    }


def cell_specs() -> list[CellSpec]:
    specs: list[CellSpec] = []
    for case_id in ("nlm_72m", "case079"):
        for frequency_hz in (250_000, 500_000):
            for method in ("baseline", "tr"):
                inputs = CASE_INPUTS[case_id]
                specs.append(
                    CellSpec(
                        case_id=case_id,
                        frequency_hz=frequency_hz,
                        method=method,
                        summary_path=SUMMARY_PATHS[(case_id, frequency_hz, method)],
                        model_path=inputs["model"],
                        entry_plan_path=inputs["entry"],
                    )
                )
    return specs


def audit_reference(name: str, relative: str, root: Path = ROOT) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        return {"reference_id": name, "status": "missing", "summary_path": relative}
    summary = load_summary(path)
    config = summary["config"]
    return {
        "reference_id": name,
        "status": "reference_only_incompatible_geometry",
        "summary_path": relative,
        "frequency_hz": config.get("frequency_hz"),
        "aperture_diameter_m": config.get("aperture_diameter_m"),
        "transducer_radius_m": config.get("transducer_radius_m"),
        "preset": config.get("preset"),
        "pml_size": config.get("pml_size"),
        "tone_burst_cycles": config.get("tone_burst_cycles"),
        "exclusion_reason": [
            "aperture_mismatch",
            "radius_mismatch",
            "preset_mismatch",
            "pml_mismatch",
        ],
    }


def build_inventory(root: Path = ROOT) -> dict[str, Any]:
    cells = [audit_cell(spec, root) for spec in cell_specs()]
    status_counts = {
        status: sum(cell["status"] == status for cell in cells)
        for status in ("present_match", "present_mismatch", "missing")
    }
    missing = [cell["cell_id"] for cell in cells if cell["status"] == "missing"]
    references = [
        audit_reference(name, relative, root)
        for name, relative in REFERENCE_ONLY.items()
    ]
    return {
        "inventory_version": "1.0.0",
        "scope": "2 cases x 2 frequencies x 2 methods; read-only quick-screening inventory",
        "frozen_geometry": {
            "aperture_diameter_m": 0.015,
            "transducer_radius_m": 0.03,
            "preset": "quick",
            "pml_size": 8,
            "cfl": 0.2,
            "source_pressure_pa": 1_000_000.0,
            "baseline_cycles": 6,
            "tr_cycles": 2,
        },
        "cells": cells,
        "status_counts": status_counts,
        "missing_cells": missing,
        "matched_matrix_complete": not missing and status_counts["present_mismatch"] == 0,
        "cross_method_absolute_pressure_strictly_matched": False,
        "cross_method_limitation": (
            "Baseline uses 6 cycles and TR uses 2-cycle calibration/refocus; "
            "method comparisons remain screening-level."
        ),
        "reference_only_outputs": references,
        "new_pressure_execution_authorized": False,
        "recommended_next_action": (
            "Preregister and dry-run the two missing Case 079 500 kHz ap15/r30 "
            "quick cells before considering execution."
        ),
        "claim_boundary": "matched-design inventory only; no new pressure, dose, clinical, or paper-grade claim",
    }


def write_report(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "matched_frequency_method_inventory.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Matched Frequency × Method Inventory",
        "",
        f"- Present/matched: `{result['status_counts']['present_match']}`",
        f"- Present/mismatched: `{result['status_counts']['present_mismatch']}`",
        f"- Missing: `{result['status_counts']['missing']}`",
        f"- Matrix complete: `{str(result['matched_matrix_complete']).lower()}`",
        "- New pressure execution authorized: `false`",
        "",
        "## Cells",
        "",
        "| Case | Frequency | Method | Status | Source semantics |",
        "|---|---:|---|---|---|",
    ]
    for cell in result["cells"]:
        lines.append(
            f"| {cell['case_id']} | {cell['frequency_hz'] // 1000} kHz | "
            f"{cell['method']} | {cell['status']} | "
            f"{cell.get('source_material_semantics', 'n/a')} |"
        )
    lines.extend([
        "",
        "## Missing cells",
        "",
        *[f"- `{cell_id}`" for cell_id in result["missing_cells"]],
        "",
        "## Interpretation",
        "",
        f"- {result['cross_method_limitation']}",
        "- Existing Case 079 500 kHz ap30/r35 outputs are reference-only and do not fill the matrix.",
        f"- Next: {result['recommended_next_action']}",
        "",
        result["claim_boundary"],
    ])
    (output_dir / "matched_frequency_method_inventory.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the matched frequency-method experiment matrix.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_inventory()
    write_report(result, args.output_dir)
    print(json.dumps({
        "status": "pass",
        "present_match": result["status_counts"]["present_match"],
        "present_mismatch": result["status_counts"]["present_mismatch"],
        "missing": result["status_counts"]["missing"],
        "missing_cells": result["missing_cells"],
        "new_pressure_execution_authorized": False,
        "output_dir": str(args.output_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
