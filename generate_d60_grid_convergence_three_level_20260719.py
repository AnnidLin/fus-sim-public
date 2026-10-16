"""Three-level grid convergence report for the D60 free-field chain.

Chain: dx0.75 -> dx0.5 -> dx0.375 (R78.330, 500 kHz, point-wave runs).

- Pending state: if the dx0.375 run has no summary.json yet, write a
  two-level (dx0.75 -> dx0.5) report with status ``pending_dx0p375`` and
  exit 0.
- Complete state: compute field metrics for all three levels, three
  pairwise comparisons, Gate-B-consistent acceptance checks, and
  convergence-ratio observations (observation only, not pass/fail).

Metrics are reused from generate_d60_grid_convergence_report (no copied
implementations).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from generate_d60_grid_convergence_report import field_metrics, percent_change

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DX075 = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run"
DEFAULT_DX05 = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p5_pointwave_20260716/run"
DEFAULT_DX0375 = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p375_pointwave_20260718/run"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_grid_convergence_three_level_20260719"

REPORT_JSON_NAME = "report.json"
REPORT_MD_NAME = "report.md"

METRIC_SEMANTICS = {
    "percent_change_reference": "absolute change divided by the finer-level value",
    "focal_displacement": "Euclidean displacement of the subvoxel-refined global peak relative to the source center",
    "minus6db": "continuous half-amplitude width through the global peak using trilinear interpolation at 0.25 voxel spacing",
    "convergence_ratio": "observed ratio of refined_focus_error_percent between adjacent levels; observation only, not a pass/fail gate",
}

DISCIPLINE_NOTE = (
    "本报告为 engineering observation 级别，不构成 paper-grade 收敛结论，"
    "也不构成任何临床安全暗示。CT 声压仍未授权（ct_pressure_authorized=false）。"
)


def rel_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def compare_pair(coarse: dict[str, object], fine: dict[str, object]) -> dict[str, float]:
    """Pairwise comparison, same semantics as build_report."""
    return {
        "global_peak_change_percent": percent_change(
            float(coarse["global_peak_mpa"]), float(fine["global_peak_mpa"])
        ),
        "lateral_width_change_percent": percent_change(
            float(coarse["minus6db_lateral_equivalent_mm"]),
            float(fine["minus6db_lateral_equivalent_mm"]),
        ),
        "axial_width_change_percent": percent_change(
            float(coarse["minus6db_axial_width_mm"]), float(fine["minus6db_axial_width_mm"])
        ),
        "focal_displacement_mm": float(
            np.linalg.norm(
                np.asarray(coarse["refined_peak_relative_to_source_mm"])
                - np.asarray(fine["refined_peak_relative_to_source_mm"])
            )
        ),
    }


def gate_b_pair_acceptance(
    coarse: dict[str, object], fine: dict[str, object], comparison: dict[str, float]
) -> dict[str, bool]:
    """Gate B acceptance checks for the dx0.75 -> dx0.5 pair (unchanged names/thresholds)."""
    return {
        "dx075_focus_error_pass": float(coarse["refined_focus_error_percent"]) <= 5.0,
        "dx05_focus_error_pass": float(fine["refined_focus_error_percent"]) <= 5.0,
        "global_peak_change_pass": comparison["global_peak_change_percent"] <= 5.0,
        "lateral_width_change_pass": comparison["lateral_width_change_percent"] <= 10.0,
        "focal_displacement_pass": comparison["focal_displacement_mm"] <= 1.0,
        "target_to_global_pass": min(
            float(coarse["target_to_global_peak_ratio"]), float(fine["target_to_global_peak_ratio"])
        )
        >= 0.9,
        "finite_fields_pass": bool(coarse["all_arrays_finite"] and fine["all_arrays_finite"]),
        "boundary_distance_pass": bool(
            int(coarse["global_boundary_distance_voxels"]) >= 12
            and int(fine["global_boundary_distance_voxels"]) >= 12
        ),
    }


def three_level_acceptance(
    dx075: dict[str, object],
    dx05: dict[str, object],
    dx0375: dict[str, object],
    comparisons: dict[str, dict[str, float]],
) -> dict[str, bool]:
    """Gate B semantics extended to the three-level chain.

    Adjacent-pair thresholds mirror build_report: refined focus error <= 5%
    per level, global peak change <= 5%, lateral width change <= 10%,
    focal displacement <= 1.0 mm. Axial width change stays an observation
    (no gate), as in build_report.
    """
    pair_ab = comparisons["dx075_to_dx05"]
    pair_bc = comparisons["dx05_to_dx0375"]
    return {
        "dx075_focus_error_pass": float(dx075["refined_focus_error_percent"]) <= 5.0,
        "dx05_focus_error_pass": float(dx05["refined_focus_error_percent"]) <= 5.0,
        "dx0375_focus_error_pass": float(dx0375["refined_focus_error_percent"]) <= 5.0,
        "global_peak_change_pass": pair_ab["global_peak_change_percent"] <= 5.0,
        "lateral_width_change_pass": pair_ab["lateral_width_change_percent"] <= 10.0,
        "focal_displacement_pass": pair_ab["focal_displacement_mm"] <= 1.0,
        "global_peak_change_dx05_dx0375_pass": pair_bc["global_peak_change_percent"] <= 5.0,
        "lateral_width_change_dx05_dx0375_pass": pair_bc["lateral_width_change_percent"] <= 10.0,
        "focal_displacement_dx05_dx0375_pass": pair_bc["focal_displacement_mm"] <= 1.0,
        "target_to_global_pass": min(
            float(dx075["target_to_global_peak_ratio"]),
            float(dx05["target_to_global_peak_ratio"]),
            float(dx0375["target_to_global_peak_ratio"]),
        )
        >= 0.9,
        "finite_fields_pass": bool(
            dx075["all_arrays_finite"] and dx05["all_arrays_finite"] and dx0375["all_arrays_finite"]
        ),
        "boundary_distance_pass": bool(
            int(dx075["global_boundary_distance_voxels"]) >= 12
            and int(dx05["global_boundary_distance_voxels"]) >= 12
            and int(dx0375["global_boundary_distance_voxels"]) >= 12
        ),
    }


def _error_ratio(coarse_error: float, fine_error: float) -> float | None:
    if fine_error == 0.0:
        return None
    return coarse_error / fine_error


def convergence_observation(
    dx075: dict[str, object], dx05: dict[str, object], dx0375: dict[str, object]
) -> dict[str, object]:
    """Observed error ratios vs ideal 2x-refinement ratios (observation only)."""
    factor_ab = float(dx075["dx_mm"]) / float(dx05["dx_mm"])
    factor_bc = float(dx05["dx_mm"]) / float(dx0375["dx_mm"])
    return {
        "metric": "refined_focus_error_percent",
        "observed_error_ratio_dx075_over_dx05": _error_ratio(
            float(dx075["refined_focus_error_percent"]),
            float(dx05["refined_focus_error_percent"]),
        ),
        "observed_error_ratio_dx05_over_dx0375": _error_ratio(
            float(dx05["refined_focus_error_percent"]),
            float(dx0375["refined_focus_error_percent"]),
        ),
        "grid_refinement_factor_dx075_to_dx05": factor_ab,
        "grid_refinement_factor_dx05_to_dx0375": factor_bc,
        "ideal_ratio_for_2x_refinement_first_order": 2.0,
        "ideal_ratio_for_2x_refinement_second_order": 4.0,
        "ideal_ratio_first_order_at_actual_factor_dx075_to_dx05": factor_ab,
        "ideal_ratio_second_order_at_actual_factor_dx075_to_dx05": factor_ab**2,
        "ideal_ratio_first_order_at_actual_factor_dx05_to_dx0375": factor_bc,
        "ideal_ratio_second_order_at_actual_factor_dx05_to_dx0375": factor_bc**2,
        "note": "observation only, not a pass/fail gate",
    }


def _base_report(status: str) -> dict[str, object]:
    return {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": Path(__file__).name,
        "metric_semantics": METRIC_SEMANTICS,
        "ct_pressure_authorized": False,
    }


def build_pending_report(
    dx075_dir: Path, dx05_dir: Path, dx0375_dir: Path
) -> dict[str, object]:
    dx075 = field_metrics(dx075_dir)
    dx05 = field_metrics(dx05_dir)
    comparison = compare_pair(dx075, dx05)
    acceptance = gate_b_pair_acceptance(dx075, dx05, comparison)
    report = _base_report("pending_dx0p375")
    report.update(
        {
            "data_provenance": {
                "dx075_run_dir": rel_to_root(dx075_dir),
                "dx05_run_dir": rel_to_root(dx05_dir),
                "dx0375_run_dir": rel_to_root(dx0375_dir),
                "dx0375_summary_json": "missing",
            },
            "dx0p75": dx075,
            "dx0p5": dx05,
            "comparisons": {"dx075_to_dx05": comparison},
            "acceptance": acceptance,
            "field_checks_pass_dx075_dx05": all(acceptance.values()),
            "remaining_gaps": [
                "dx0.375 summary.json not yet available; three-level comparison pending",
                "PML16 sensitivity not run",
                "CFL0.1 sensitivity not run",
            ],
            "note": "dx0.375 run still in progress; re-run this generator after summary.json lands to produce the three-level report.",
        }
    )
    return report


def build_complete_report(
    dx075_dir: Path, dx05_dir: Path, dx0375_dir: Path
) -> dict[str, object]:
    dx075 = field_metrics(dx075_dir)
    dx05 = field_metrics(dx05_dir)
    dx0375 = field_metrics(dx0375_dir)
    comparisons = {
        "dx075_to_dx05": compare_pair(dx075, dx05),
        "dx05_to_dx0375": compare_pair(dx05, dx0375),
        "dx075_to_dx0375": compare_pair(dx075, dx0375),
    }
    acceptance = three_level_acceptance(dx075, dx05, dx0375, comparisons)
    field_checks_pass = all(acceptance.values())
    flag_reasons = [name for name, ok in acceptance.items() if not ok]
    status = "three_level_convergence_pass" if field_checks_pass else "three_level_convergence_flag"
    report = _base_report(status)
    report.update(
        {
            "data_provenance": {
                "dx075_run_dir": rel_to_root(dx075_dir),
                "dx05_run_dir": rel_to_root(dx05_dir),
                "dx0375_run_dir": rel_to_root(dx0375_dir),
            },
            "dx0p75": dx075,
            "dx0p5": dx05,
            "dx0p375": dx0375,
            "comparisons": comparisons,
            "acceptance": acceptance,
            "field_checks_pass": field_checks_pass,
            "flag_reasons": flag_reasons,
            "convergence_observation": convergence_observation(dx075, dx05, dx0375),
            "waveform_recorded": {
                "dx0p75": bool(dx075["target_waveform_recorded"]),
                "dx0p5": bool(dx05["target_waveform_recorded"]),
                "dx0p375": bool(dx0375["target_waveform_recorded"]),
            },
            "remaining_gaps": [
                gap
                for gap, present in (
                    (
                        "target waveform not recorded on all levels",
                        bool(
                            dx075["target_waveform_recorded"]
                            and dx05["target_waveform_recorded"]
                            and dx0375["target_waveform_recorded"]
                        ),
                    ),
                    ("PML16 sensitivity not run", False),
                    ("CFL0.1 sensitivity not run", False),
                )
                if not present
            ],
        }
    )
    return report


def _fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def _pair_md(title: str, coarse: dict[str, object], fine: dict[str, object], comparison: dict[str, float]) -> list[str]:
    return [
        f"### {title}",
        "",
        f"- global peak：{coarse['global_peak_mpa']:.4f} → {fine['global_peak_mpa']:.4f} MPa；变化 {comparison['global_peak_change_percent']:.3f}%（门槛 ≤5%）",
        f"- refined focus error：{coarse['refined_focus_error_percent']:.3f}% → {fine['refined_focus_error_percent']:.3f}%（每级门槛 ≤5%）",
        f"- focal displacement：{comparison['focal_displacement_mm']:.3f} mm（门槛 ≤1.0 mm）",
        f"- lateral -6 dB equivalent width：{coarse['minus6db_lateral_equivalent_mm']:.3f} → {fine['minus6db_lateral_equivalent_mm']:.3f} mm；变化 {comparison['lateral_width_change_percent']:.3f}%（门槛 ≤10%）",
        f"- axial -6 dB width：{coarse['minus6db_axial_width_mm']:.3f} → {fine['minus6db_axial_width_mm']:.3f} mm；变化 {comparison['axial_width_change_percent']:.3f}%（观察项，不设门槛）",
        "",
    ]


def _acceptance_md(acceptance: dict[str, bool]) -> list[str]:
    lines = ["## Acceptance 细项（Gate B 语义）", ""]
    for name, ok in acceptance.items():
        lines.append(f"- `{name}`: {'PASS' if ok else 'FLAG'}")
    lines.append("")
    return lines


def write_report(report: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / REPORT_JSON_NAME).write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    status = report["status"]
    dx075 = report["dx0p75"]
    dx05 = report["dx0p5"]
    lines: list[str] = [
        "# D60 自由场三级网格收敛对比（dx0.75 → dx0.5 → dx0.375）",
        "",
        f"- 状态：`{status}`",
        f"- 生成时间（UTC）：{report['generated_at']}",
        "",
        "## 数据溯源",
        "",
        f"- dx0.75 run：`{report['data_provenance']['dx075_run_dir']}`",
        f"- dx0.5 run：`{report['data_provenance']['dx05_run_dir']}`",
        f"- dx0.375 run：`{report['data_provenance']['dx0375_run_dir']}`",
        "",
    ]
    if status == "pending_dx0p375":
        lines += [
            "## Pending 说明",
            "",
            "dx0.375 运行目录下尚无 `summary.json`（仿真仍在进行中）。当前仅输出 "
            "dx0.75 → dx0.5 两级对比（Gate B 同口径）；待 dx0.375 落地后重新运行本脚本"
            "即可生成三级完整对比。",
            "",
            "## dx0.75 → dx0.5 两级对比",
            "",
        ]
        lines += _pair_md(
            "dx0.75 → dx0.5", dx075, dx05, report["comparisons"]["dx075_to_dx05"]
        )[2:]
        lines += _acceptance_md(report["acceptance"])
    else:
        dx0375 = report["dx0p375"]
        lines += [
            "## 三级 refined focus error 概览",
            "",
            f"- dx0.75：{dx075['refined_focus_error_percent']:.3f}%",
            f"- dx0.5：{dx05['refined_focus_error_percent']:.3f}%",
            f"- dx0.375：{dx0375['refined_focus_error_percent']:.3f}%",
            "",
            "## 两两对比",
            "",
        ]
        lines += _pair_md("dx0.75 → dx0.5", dx075, dx05, report["comparisons"]["dx075_to_dx05"])
        lines += _pair_md("dx0.5 → dx0.375", dx05, dx0375, report["comparisons"]["dx05_to_dx0375"])
        lines += _pair_md(
            "dx0.75 → dx0.375（跨度）", dx075, dx0375, report["comparisons"]["dx075_to_dx0375"]
        )
        conv = report["convergence_observation"]
        lines += [
            "## 收敛比观察项（observation，非 pass/fail）",
            "",
            f"- observed error ratio dx0.75/dx0.5：{_fmt(conv['observed_error_ratio_dx075_over_dx05'])}"
            f"（细化因子 {conv['grid_refinement_factor_dx075_to_dx05']:.3f}×）",
            f"- observed error ratio dx0.5/dx0.375：{_fmt(conv['observed_error_ratio_dx05_over_dx0375'])}"
            f"（细化因子 {conv['grid_refinement_factor_dx05_to_dx0375']:.3f}×）",
            "- 2× 细化理想比：一阶 2.0 / 二阶 4.0（仅供参考；本链实际细化因子约 1.5× 与 1.333×）",
            "",
        ]
        lines += _acceptance_md(report["acceptance"])
        if report["flag_reasons"]:
            lines += ["## Flag 原因", ""]
            for name in report["flag_reasons"]:
                lines.append(f"- `{name}`")
            lines.append("")
    if report["remaining_gaps"]:
        lines += ["## Remaining gaps", ""]
        for gap in report["remaining_gaps"]:
            lines.append(f"- {gap}")
        lines.append("")
    lines += ["## 措辞纪律", "", DISCIPLINE_NOTE, ""]
    (output_dir / REPORT_MD_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dx075-dir", type=Path, default=DEFAULT_DX075)
    parser.add_argument("--dx05-dir", type=Path, default=DEFAULT_DX05)
    parser.add_argument("--dx0375-dir", type=Path, default=DEFAULT_DX0375)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    dx075_dir = args.dx075_dir.resolve()
    dx05_dir = args.dx05_dir.resolve()
    dx0375_dir = args.dx0375_dir.resolve()
    output_dir = args.output_dir.resolve()

    dx0375_ready = (dx0375_dir / "summary.json").is_file()
    if dx0375_ready:
        report = build_complete_report(dx075_dir, dx05_dir, dx0375_dir)
    else:
        report = build_pending_report(dx075_dir, dx05_dir, dx0375_dir)
    write_report(report, output_dir)
    print(json.dumps({"status": report["status"], "output_dir": rel_to_root(output_dir)}))


if __name__ == "__main__":
    main()
