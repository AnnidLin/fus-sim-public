from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from public_case_source_policy import classify_source_materials


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs" / "target_dominance_diagnostic_20260727"
METRIC_VERSION = "2.0.0"


@dataclass(frozen=True)
class RunSpec:
    case_id: str
    frequency_hz: int
    method: str
    summary_path: str
    focus_path: str

    @property
    def cell_id(self) -> str:
        return f"{self.case_id}_{self.frequency_hz // 1000}khz_{self.method}"


def run_specs() -> list[RunSpec]:
    paths = {
        ("nlm_72m", 250_000, "baseline"): "outputs/nlm_kwave_quick_250khz_20260724",
        ("nlm_72m", 250_000, "tr"): "outputs/nlm_tr_72m_250khz_20260724",
        ("nlm_72m", 500_000, "baseline"): "outputs/nlm_kwave_quick_20260724",
        ("nlm_72m", 500_000, "tr"): "outputs/nlm_tr_72m_20260724",
        ("case079", 250_000, "baseline"): "outputs/case079_kwave_quick_250khz_20260724",
        ("case079", 250_000, "tr"): "outputs/case079_tr_250khz_20260724",
        ("case079", 500_000, "baseline"): (
            "outputs/case079_kwave_quick_500khz_matched_20260726"
        ),
        ("case079", 500_000, "tr"): "outputs/case079_tr_500khz_matched_20260726",
    }
    return [
        RunSpec(case_id, frequency_hz, method, f"{directory}/summary.json", f"{directory}/focus_metrics.json")
        for (case_id, frequency_hz, method), directory in paths.items()
    ]


REQUIRED_FOCUS_FIELDS = (
    "global_peak_mpa",
    "target_window_peak_mpa",
    "target_to_global_peak_ratio",
    "target_to_post_entry_peak_ratio",
    "global_peak_to_target_distance_mm",
    "global_peak_axial_from_source_mm",
    "entry_axial_from_source_mm",
    "global_peak_axial_shortfall_to_target_mm",
    "target_window_peak_axial_shortfall_to_target_mm",
    "target_window_radius_grid_points",
)


def load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: expected a numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label}: expected a finite scalar")
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_fold(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else numerator / denominator


def direction(delta: float, tolerance: float = 1e-12) -> str:
    if delta > tolerance:
        return "increase"
    if delta < -tolerance:
        return "decrease"
    return "unchanged"


def load_cell(spec: RunSpec, root: Path = ROOT) -> dict[str, Any]:
    summary_path = root / spec.summary_path
    focus_path = root / spec.focus_path
    summary = load_object(summary_path)
    focus = load_object(focus_path)
    config = summary.get("config")
    quality = summary.get("simulation_quality")
    source = summary.get("source")
    pressure = summary.get("pressure")
    if not all(isinstance(value, dict) for value in (config, quality, source, pressure)):
        raise ValueError(f"{summary_path}: missing config/quality/source/pressure object")
    if focus.get("metric_semantics_version") != METRIC_VERSION:
        raise ValueError(
            f"{focus_path}: metric semantics {focus.get('metric_semantics_version')!r} "
            f"does not match {METRIC_VERSION!r}"
        )

    metrics = {
        name: finite_number(focus.get(name), f"{focus_path}:{name}")
        for name in REQUIRED_FOCUS_FIELDS
    }
    actual_frequency = finite_number(config.get("frequency_hz"), f"{summary_path}:frequency_hz")
    if actual_frequency != spec.frequency_hz:
        raise ValueError(f"{summary_path}: frequency does not match {spec.cell_id}")
    expected_cycles = 6 if spec.method == "baseline" else 2
    actual_cycles = int(finite_number(config.get("tone_burst_cycles"), f"{summary_path}:cycles"))
    if actual_cycles != expected_cycles:
        raise ValueError(f"{summary_path}: cycles do not match {spec.cell_id}")

    for name in (
        "global_peak_mpa",
        "target_window_peak_mpa",
        "target_to_global_peak_ratio",
    ):
        summary_value = finite_number(pressure.get(name), f"{summary_path}:pressure:{name}")
        if not math.isclose(summary_value, metrics[name], rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(f"{spec.cell_id}: summary/focus mismatch for {name}")

    dx_mm = finite_number(quality.get("dx_mm"), f"{summary_path}:dx_mm")
    target_window_radius_mm = metrics["target_window_radius_grid_points"] * dx_mm
    global_distance_mm = metrics["global_peak_to_target_distance_mm"]
    source_counts = source.get("source_label_counts")
    if not isinstance(source_counts, dict):
        raise ValueError(f"{summary_path}: source_label_counts missing")

    return {
        "cell_id": spec.cell_id,
        "case_id": spec.case_id,
        "frequency_hz": spec.frequency_hz,
        "method": spec.method,
        "summary_path": spec.summary_path,
        "focus_path": spec.focus_path,
        "summary_sha256": sha256(summary_path),
        "focus_sha256": sha256(focus_path),
        "metric_semantics_version": METRIC_VERSION,
        "source_material_semantics": classify_source_materials(source_counts),
        "source_label_counts": source_counts,
        "preset": config.get("preset"),
        "tone_burst_cycles": actual_cycles,
        "ppw_min_sound_speed": finite_number(
            quality.get("ppw_min_sound_speed"), f"{summary_path}:ppw"
        ),
        "screening_only": quality.get("screening_only"),
        "paper_grade": quality.get("is_paper_grade"),
        "global_peak_mpa": metrics["global_peak_mpa"],
        "target_window_peak_mpa": metrics["target_window_peak_mpa"],
        "target_to_global_peak_ratio": metrics["target_to_global_peak_ratio"],
        "target_to_post_entry_peak_ratio": metrics["target_to_post_entry_peak_ratio"],
        "global_peak_to_target_distance_mm": global_distance_mm,
        "global_peak_axial_from_source_mm": metrics["global_peak_axial_from_source_mm"],
        "entry_axial_from_source_mm": metrics["entry_axial_from_source_mm"],
        "global_peak_axial_offset_from_entry_mm": (
            metrics["global_peak_axial_from_source_mm"]
            - metrics["entry_axial_from_source_mm"]
        ),
        "global_peak_axial_shortfall_to_target_mm": metrics[
            "global_peak_axial_shortfall_to_target_mm"
        ],
        "target_window_peak_axial_shortfall_to_target_mm": metrics[
            "target_window_peak_axial_shortfall_to_target_mm"
        ],
        "target_window_radius_mm": target_window_radius_mm,
        "global_peak_inside_target_window": global_distance_mm <= target_window_radius_mm,
    }


def compare_cells(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_ratio = first["target_to_global_peak_ratio"]
    second_ratio = second["target_to_global_peak_ratio"]
    ratio_delta = second_ratio - first_ratio
    return {
        "first_cell": first["cell_id"],
        "second_cell": second["cell_id"],
        "target_to_global_first": first_ratio,
        "target_to_global_second": second_ratio,
        "target_to_global_delta": ratio_delta,
        "target_to_global_fold": safe_fold(second_ratio, first_ratio),
        "target_to_global_direction": direction(ratio_delta),
        "target_window_peak_first_mpa": first["target_window_peak_mpa"],
        "target_window_peak_second_mpa": second["target_window_peak_mpa"],
        "global_peak_distance_first_mm": first["global_peak_to_target_distance_mm"],
        "global_peak_distance_second_mm": second["global_peak_to_target_distance_mm"],
    }


def build_report(root: Path = ROOT) -> dict[str, Any]:
    cells = [load_cell(spec, root) for spec in run_specs()]
    if len(cells) != 8:
        raise ValueError("expected exactly eight cells")
    index = {
        (cell["case_id"], cell["frequency_hz"], cell["method"]): cell
        for cell in cells
    }

    method_pairs = [
        {
            "case_id": case_id,
            "frequency_hz": frequency_hz,
            **compare_cells(
                index[(case_id, frequency_hz, "baseline")],
                index[(case_id, frequency_hz, "tr")],
            ),
        }
        for case_id in ("nlm_72m", "case079")
        for frequency_hz in (250_000, 500_000)
    ]
    frequency_pairs = [
        {
            "case_id": case_id,
            "method": method,
            **compare_cells(
                index[(case_id, 250_000, method)],
                index[(case_id, 500_000, method)],
            ),
        }
        for case_id in ("nlm_72m", "case079")
        for method in ("baseline", "tr")
    ]

    global_distances = [cell["global_peak_to_target_distance_mm"] for cell in cells]
    entry_offsets = [abs(cell["global_peak_axial_offset_from_entry_mm"]) for cell in cells]
    target_shortfalls = [
        abs(cell["target_window_peak_axial_shortfall_to_target_mm"]) for cell in cells
    ]
    all_tr_ratios_increase = all(
        pair["target_to_global_direction"] == "increase" for pair in method_pairs
    )
    baseline_frequency_pairs = [
        pair for pair in frequency_pairs if pair["method"] == "baseline"
    ]
    tr_frequency_pairs = [pair for pair in frequency_pairs if pair["method"] == "tr"]
    frequency_pattern = {
        "500khz_ratio_lower_for_both_baselines": all(
            pair["target_to_global_direction"] == "decrease"
            for pair in baseline_frequency_pairs
        ),
        "500khz_ratio_higher_for_both_tr_runs": all(
            pair["target_to_global_direction"] == "increase"
            for pair in tr_frequency_pairs
        ),
    }
    highest_ratio_cell = max(cells, key=lambda item: item["target_to_global_peak_ratio"])

    findings: list[str] = []
    if all(not cell["global_peak_inside_target_window"] for cell in cells):
        findings.append(
            "All eight global peaks are outside their recorded target windows."
        )
    if all_tr_ratios_increase:
        findings.append(
            "TR increases the target/global ratio in all four matched case-frequency pairs."
        )
    if all(frequency_pattern.values()):
        findings.append(
            "Across both cases, 500 kHz lowers the baseline ratio but raises the TR ratio relative to 250 kHz."
        )

    return {
        "report_version": "1.0.0",
        "scope": "eight-cell read-only target-dominance diagnostic",
        "cells": cells,
        "method_pairs": method_pairs,
        "frequency_pairs": frequency_pairs,
        "aggregate": {
            "cell_count": len(cells),
            "all_metric_semantics_v2": all(
                cell["metric_semantics_version"] == METRIC_VERSION for cell in cells
            ),
            "all_global_peaks_outside_target_window": all(
                not cell["global_peak_inside_target_window"] for cell in cells
            ),
            "global_peak_to_target_distance_range_mm": [
                min(global_distances),
                max(global_distances),
            ],
            "absolute_global_peak_entry_offset_range_mm": [
                min(entry_offsets),
                max(entry_offsets),
            ],
            "target_window_peak_axial_shortfall_range_mm": [
                min(target_shortfalls),
                max(target_shortfalls),
            ],
            "all_four_tr_pairs_increase_target_global_ratio": all_tr_ratios_increase,
            "frequency_pattern": frequency_pattern,
            "highest_target_global_ratio_cell": {
                "cell_id": highest_ratio_cell["cell_id"],
                "value": highest_ratio_cell["target_to_global_peak_ratio"],
            },
        },
        "computed_findings": findings,
        "limitations": [
            "No universal target-dominance pass threshold was introduced.",
            "Baseline and TR absolute pressures are waveform-protocol dependent.",
            "NLM and Case079 source-material semantics differ.",
            "Quick results, including 500 kHz PPW near 4, are not paper-grade convergence evidence.",
        ],
        "legacy_reports_superseded_for_current_matrix": [
            "outputs/cross_case_comparison_20260724",
            "outputs/cross_case_comparison_250khz_20260724",
        ],
        "new_simulation_authorized": False,
        "claim_boundary": (
            "descriptive quick-screening engineering evidence only; no causal, "
            "dose, clinical, anatomical efficacy, or paper-grade claim"
        ),
    }


def write_report(report: dict[str, Any], output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "target_dominance_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Eight-Cell Target-Dominance Diagnostic",
        "",
        f"- Cells: `{report['aggregate']['cell_count']}`",
        (
            "- Global peaks outside target window: "
            f"`{str(report['aggregate']['all_global_peaks_outside_target_window']).lower()}`"
        ),
        (
            "- TR ratio increased in all matched pairs: "
            f"`{str(report['aggregate']['all_four_tr_pairs_increase_target_global_ratio']).lower()}`"
        ),
        "- New simulation authorized: `false`",
        "",
        "## Cell metrics",
        "",
        "| Cell | T/G | Global→target | Global axial offset from entry | Target-window axial shortfall | Source semantics |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for cell in report["cells"]:
        lines.append(
            f"| `{cell['cell_id']}` | {cell['target_to_global_peak_ratio']:.4f} | "
            f"{cell['global_peak_to_target_distance_mm']:.2f} mm | "
            f"{cell['global_peak_axial_offset_from_entry_mm']:+.2f} mm | "
            f"{cell['target_window_peak_axial_shortfall_to_target_mm']:.2f} mm | "
            f"{cell['source_material_semantics']} |"
        )
    lines.extend([
        "",
        "## Baseline → TR",
        "",
        "| Case | Frequency | Baseline T/G | TR T/G | Fold | Direction |",
        "|---|---:|---:|---:|---:|---|",
    ])
    for pair in report["method_pairs"]:
        lines.append(
            f"| {pair['case_id']} | {pair['frequency_hz'] // 1000} kHz | "
            f"{pair['target_to_global_first']:.4f} | "
            f"{pair['target_to_global_second']:.4f} | "
            f"{pair['target_to_global_fold']:.2f}× | "
            f"{pair['target_to_global_direction']} |"
        )
    lines.extend([
        "",
        "## 250 → 500 kHz",
        "",
        "| Case | Method | 250 kHz T/G | 500 kHz T/G | Fold | Direction |",
        "|---|---|---:|---:|---:|---|",
    ])
    for pair in report["frequency_pairs"]:
        lines.append(
            f"| {pair['case_id']} | {pair['method']} | "
            f"{pair['target_to_global_first']:.4f} | "
            f"{pair['target_to_global_second']:.4f} | "
            f"{pair['target_to_global_fold']:.2f}× | "
            f"{pair['target_to_global_direction']} |"
        )
    lines.extend(["", "## Computed findings", ""])
    lines.extend(f"- {finding}" for finding in report["computed_findings"])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.extend(["", report["claim_boundary"]])
    (output_dir / "target_dominance_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    report = build_report()
    write_report(report)
    print(
        json.dumps(
            {
                "status": "pass",
                "cells": report["aggregate"]["cell_count"],
                "all_global_peaks_outside_target_window": report["aggregate"][
                    "all_global_peaks_outside_target_window"
                ],
                "all_four_tr_pairs_increase_target_global_ratio": report["aggregate"][
                    "all_four_tr_pairs_increase_target_global_ratio"
                ],
                "highest_ratio_cell": report["aggregate"][
                    "highest_target_global_ratio_cell"
                ],
                "output_dir": str(OUTPUT_DIR),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
