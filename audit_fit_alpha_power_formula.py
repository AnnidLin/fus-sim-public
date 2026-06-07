from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from build_ct_acoustic_model import fit_power_law_params_multi


PROJECT_ROOT = Path(__file__).resolve().parent


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def source_contains_formula(source_text: str) -> dict[str, bool]:
    required_fragments = {
        "rad_s_frequency": "w = 2 * pi * f_ref",
        "db2neper": "a0_np = db2neper(a0, y)",
        "desired_absorption": "desired_absorption = a0_np .* w.^y",
        "second_order_denominator": "desired_absorption .* (y_ref + 1) .* c0 .* tan(pi .* y_ref ./ 2)",
        "neper2db": "a0_fit = neper2db(a0_fit_np, y_ref)",
    }
    compact = " ".join(source_text.split())
    return {
        key: " ".join(fragment.split()) in compact
        for key, fragment in required_fragments.items()
    }


def sample_fit_table() -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    alpha_at_500_values = [4.0, 6.35, 8.7]
    c0_values = [1500.0, 2200.0, 3360.0]
    f_ref = 500_000.0
    y_original = 1.0
    y_ref = 2.0
    for alpha_at_500 in alpha_at_500_values:
        original_alpha0 = alpha_at_500 / (0.5 ** y_original)
        naive_y2_alpha0 = alpha_at_500 / (0.5 ** y_ref)
        for c0 in c0_values:
            fitted = float(
                fit_power_law_params_multi(
                    np.array([original_alpha0], dtype=np.float64),
                    np.array([y_original], dtype=np.float64),
                    np.array([c0], dtype=np.float64),
                    f_ref,
                    y_ref,
                )[0]
            )
            rows.append(
                {
                    "alpha_at_500khz_db_cm": alpha_at_500,
                    "original_alpha_power": y_original,
                    "original_alpha0_db_mhz_cm": original_alpha0,
                    "target_alpha_power": y_ref,
                    "sound_speed_m_s": c0,
                    "fitted_alpha0_db_mhz2_cm": fitted,
                    "naive_match_alpha0_db_mhz2_cm": naive_y2_alpha0,
                    "relative_difference_vs_naive": (
                        (fitted - naive_y2_alpha0) / naive_y2_alpha0 if naive_y2_alpha0 else 0.0
                    ),
                }
            )
    return rows


def audit(args: argparse.Namespace) -> dict[str, Any]:
    source_path = Path(args.prestus_source)
    profile_path = Path(args.profile)
    model_summary_path = Path(args.model_summary)

    source_text = source_path.read_text(encoding="utf-8", errors="replace")
    profile = read_json(profile_path)
    model_summary = read_json(model_summary_path)
    alpha_semantics = profile.get("alpha_semantics", {})
    model_mapping = model_summary.get("mapping_profile", {})

    formula_checks = source_contains_formula(source_text)
    rows = sample_fit_table()
    max_abs_rel_diff = max(abs(row["relative_difference_vs_naive"]) for row in rows)

    pressure_allowed = bool(alpha_semantics.get("pressure_allowed", False))
    model_pressure_allowed = bool(
        model_mapping.get("alpha_semantics", {}).get("pressure_allowed", False)
    )

    status = "formula_migration_consistent_model_build_only"
    if not all(formula_checks.values()):
        status = "source_formula_fragments_missing_review_required"
    elif pressure_allowed or model_pressure_allowed:
        status = "pressure_guard_failed_review_required"

    return {
        "audit_type": "fit_alpha_power_formula_unit_audit",
        "status": status,
        "source_files": {
            "prestus_fitPowerLawParamsMulti": str(source_path),
            "profile": str(profile_path),
            "model_summary": str(model_summary_path),
        },
        "formula_checks": formula_checks,
        "profile_alpha_semantics": alpha_semantics,
        "model_alpha_semantics": model_mapping.get("alpha_semantics", {}),
        "unit_interpretation": {
            "input_original_alpha0": "dB/(MHz^y cm), y from original PRESTUS attenuation route",
            "reference_frequency_hz": float(alpha_semantics.get("reference_frequency_hz", 500_000.0)),
            "target_alpha_power": float(alpha_semantics.get("alpha_power", 2.0)),
            "output_fitted_alpha0": "dB/(MHz^2 cm) for kWaveMedium.alpha_power=2",
            "important_boundary": "Fitted alpha0 prefactor is not directly comparable to dB/cm at 500 kHz.",
        },
        "numeric_sanity": {
            "sample_count": len(rows),
            "max_abs_relative_difference_vs_naive_y2_match": max_abs_rel_diff,
            "interpretation": (
                "For y_ref=2, tan(pi*y_ref/2)=tan(pi) is approximately zero, so the second-order term is negligible; "
                "the fitted prefactor nearly equals alpha_at_500kHz / 0.5^2."
            ),
        },
        "model_build_result": {
            "profile_id": model_mapping.get("profile_id"),
            "review_status": model_mapping.get("review_status"),
            "alpha_range_db_mhz_power_cm": model_summary.get("alpha_range_db_mhz_cm"),
            "grid_shape": model_summary.get("grid_shape"),
            "target_index_ijk": model_summary.get("target_index_ijk"),
        },
        "pressure_decision": {
            "pressure_allowed": False,
            "reason": "Formula audit supports implementation consistency only; pressure remains blocked until separate authorization and validation.",
        },
        "recommended_next_step": (
            "先为 prestus_fit_alpha_power_2 生成 entry-path property profile，或做 MATLAB/Python 单元交叉检查；"
            "在此之前不要进入 pressure sanity run。"
        ),
        "sample_rows": rows,
    }


def write_csv(path: Path, rows: list[dict[str, float]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report: dict[str, Any]) -> str:
    formula_checks = report["formula_checks"]
    sample = report["sample_rows"]
    lines = [
        "# PRESTUS fitPowerLawParamsMulti 公式与单位审计",
        "",
        "## 结论",
        "",
        f"- 状态：`{report['status']}`",
        "- 本报告只审计公式迁移和单位语义，不运行 k-Wave，不生成 pressure field。",
        "- 当前 `prestus_fit_alpha_power_2` 仍保持 `pressure_allowed=false`，不能作为 validated pressure baseline。",
        "",
        "## 源码片段检查",
        "",
    ]
    for key, ok in formula_checks.items():
        lines.append(f"- `{key}`：{'通过' if ok else '需要复核'}")
    lines.extend(
        [
            "",
            "## 单位解释",
            "",
            "- PRESTUS 输入 `a0`：`dB/(MHz^y cm)`。",
            "- `fitPowerLawParamsMulti` 先用 `db2neper` 转为 `Np/((rad/s)^y m)`。",
            "- 在参考频率 `f_ref=500 kHz` 处计算 desired absorption。",
            "- 输出 `a0_fit`：用于 `medium.alpha_coeff` 的 `dB/(MHz^y_ref cm)` prefactor。",
            "- 因此 `dB/(MHz^2 cm)` prefactor 不能直接和 500 kHz 下的 `dB/cm` absorption 数值比较。",
            "",
            "## y_ref=2 数值行为",
            "",
            "当 `y_ref=2` 时，`tan(pi*y_ref/2)=tan(pi)` 理论上为 0，所以二阶项几乎消失。",
            "这解释了当前模型中 skull alpha prefactor 约为原 500 kHz absorption 的 4 倍：",
            "`alpha0_y2 ~= alpha_at_500kHz / 0.5^2`。",
            "",
            "| alpha@500kHz dB/cm | c0 m/s | fitted alpha0 dB/(MHz^2 cm) | naive match | rel diff |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in sample:
        lines.append(
            f"| {row['alpha_at_500khz_db_cm']:.3f} | {row['sound_speed_m_s']:.1f} | "
            f"{row['fitted_alpha0_db_mhz2_cm']:.6f} | {row['naive_match_alpha0_db_mhz2_cm']:.6f} | "
            f"{row['relative_difference_vs_naive']:.3e} |"
        )
    lines.extend(
        [
            "",
            "## 当前模型状态",
            "",
            f"- profile：`{report['model_build_result']['profile_id']}`",
            f"- review status：`{report['model_build_result']['review_status']}`",
            f"- alpha range：`{report['model_build_result']['alpha_range_db_mhz_power_cm']}`",
            f"- target：`{report['model_build_result']['target_index_ijk']}`",
            "",
            "## 风险和停止条件",
            "",
            "- 该审计不能解除 pressure block。",
            "- 若后续要进入 pressure sanity run，必须另开 evidence brief/runner 授权，并先复核 entry-path 上的 alpha/c/rho 分布。",
            "- 如果 MATLAB/Python 单元交叉测试与本报告不一致，应停止使用该 profile。",
            "",
            "## 建议下一步",
            "",
            f"{report['recommended_next_step']}",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit PRESTUS fitPowerLawParamsMulti formula migration.")
    parser.add_argument(
        "--prestus-source",
        default="data/source_code_refs/PRESTUS_source/functions/medium/fitPowerLawParamsMulti.m",
    )
    parser.add_argument(
        "--profile",
        default="acoustic_mapping_profiles/prestus_fit_alpha_power_2.json",
    )
    parser.add_argument(
        "--model-summary",
        default="outputs/ct_acoustic_model_3d_profile_prestus_fit_alpha_power_2/summary.json",
    )
    parser.add_argument("--output-dir", default="outputs/fit_alpha_power_formula_audit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = audit(args)
    write_json(output_dir / "formula_audit_report.json", report)
    (output_dir / "formula_audit_report.md").write_text(build_markdown(report), encoding="utf-8-sig")
    write_csv(output_dir / "sample_fit_table.csv", report["sample_rows"])


if __name__ == "__main__":
    main()
