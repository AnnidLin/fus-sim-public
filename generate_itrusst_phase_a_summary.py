#!/usr/bin/env python3
"""Generate a traceable BM1/BM3/BM4 ITRUSST Phase-A summary package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_CASES = {
    "BM1": ROOT / "outputs" / "itrusst_bm1_sc1_axisymmetric_ppw12_20260803",
    "BM3": ROOT
    / "outputs"
    / "itrusst_bm3_sc1_axisymmetric_ppw12_retry1_20260804",
    "BM4": ROOT
    / "outputs"
    / "itrusst_bm4_sc1_axisymmetric_ppw12_throttled_20260807",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_case(benchmark: str, output_dir: Path) -> dict[str, Any]:
    comparison_path = output_dir / "comparison.json"
    summary_path = output_dir / "summary.json"
    monitor_path = output_dir / "monitor_status.json"
    field_path = output_dir / "p_amp.npz"
    required = (comparison_path, summary_path, monitor_path, field_path)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"{benchmark}: missing authoritative artifacts: {missing}"
        )
    comparison = load_json(comparison_path)
    summary = load_json(summary_path)
    monitor = load_json(monitor_path)
    if comparison.get("benchmark") != benchmark:
        raise ValueError(
            f"{benchmark}: comparison benchmark is {comparison.get('benchmark')}"
        )
    if summary.get("benchmark") != benchmark:
        raise ValueError(f"{benchmark}: summary benchmark drift")
    if monitor.get("status") != "completed":
        raise ValueError(f"{benchmark}: monitor is not completed")
    metrics = comparison["metrics"]
    config = summary["config"]
    derived = summary["derived"]
    return {
        "benchmark": benchmark,
        "output_dir": str(output_dir.resolve()),
        "comparison_path": str(comparison_path.resolve()),
        "comparison_sha256": sha256_file(comparison_path),
        "field_sha256": sha256_file(field_path),
        "coordinate_system": config["coordinate_system"],
        "dx_mm": config["dx_mm"],
        "comparison_dx_mm": config["comparison_dx_mm"],
        "ppw": derived["ppw"],
        "points_per_period": derived["points_per_period"],
        "nt": derived["nt"],
        "omp_threads": derived.get("omp_threads"),
        "solver_runtime_s": summary["runtime_s"],
        "monitored_wall_s": monitor.get("elapsed_s"),
        "relative_l2_percent": metrics["relative_l2_percent"],
        "relative_linf_percent": metrics["relative_linf_percent"],
        "peak_difference_percent": metrics["peak_difference_percent"],
        "focal_position_difference_mm": metrics[
            "focal_position_difference_mm"
        ],
        "reference_peak_pa": metrics["reference_peak"],
        "candidate_peak_pa": metrics["candidate_peak"],
        "reference_peak_index": metrics["reference_peak_index"],
        "candidate_peak_index": metrics["candidate_peak_index"],
        "reference_widths": metrics["reference_widths"],
        "candidate_widths_at_reference_peak": metrics[
            "candidate_widths_at_reference_peak"
        ],
    }


def build_summary(case_dirs: dict[str, Path]) -> dict[str, Any]:
    expected = {"BM1", "BM3", "BM4"}
    if set(case_dirs) != expected:
        raise ValueError(f"expected exactly {sorted(expected)}")
    cases = [
        collect_case(benchmark, case_dirs[benchmark])
        for benchmark in ("BM1", "BM3", "BM4")
    ]
    return {
        "schema_version": "1.0",
        "report_id": "itrusst_phase_a_focused_bowl_summary",
        "status": "complete" if len(cases) == 3 else "incomplete",
        "contract": "benchmarking/itrusst_phase1_contract.json",
        "source_scope": "focused_bowl_source_1",
        "cases": cases,
        "interpretation_policy": {
            "pre_registered_project_pass_threshold": None,
            "cross_model_statistics_are_context_only": True,
            "allowed_claim": (
                "Three planned Phase-A engineering benchmark cases were "
                "executed and compared with the frozen official k-Wave fields."
            ),
            "blocked_claims": [
                "paper-grade numerical convergence",
                "whole-skull validation",
                "experimental or clinical validation",
                "thermal or safety validation",
            ],
        },
    }


def write_csv(path: Path, cases: list[dict[str, Any]]) -> None:
    fields = [
        "benchmark",
        "coordinate_system",
        "dx_mm",
        "comparison_dx_mm",
        "ppw",
        "points_per_period",
        "nt",
        "omp_threads",
        "solver_runtime_s",
        "monitored_wall_s",
        "relative_l2_percent",
        "relative_linf_percent",
        "peak_difference_percent",
        "focal_position_difference_mm",
        "reference_peak_pa",
        "candidate_peak_pa",
        "comparison_sha256",
        "field_sha256",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            writer.writerow({field: case.get(field) for field in fields})


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# ITRUSST Phase-A Focused-Bowl Summary",
        "",
        "| Case | L2 (%) | L∞ (%) | Peak diff (%) | Focus diff (mm) | PPW | PPP | Solver (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in report["cases"]:
        lines.append(
            "| {benchmark} | {relative_l2_percent:.4f} | "
            "{relative_linf_percent:.4f} | {peak_difference_percent:.4f} | "
            "{focal_position_difference_mm:.3f} | {ppw:.2f} | "
            "{points_per_period} | {solver_runtime_s:.2f} |".format(**case)
        )
    lines.extend(
        [
            "",
            "All three planned Phase-A cases use focused-bowl source 1 and the "
            "frozen 0.5 mm comparison grid.",
            "",
            "The table reports measured engineering differences only. ITRUSST "
            "cross-model statistics are context, not a post hoc project pass line. "
            "These cases do not establish paper-grade convergence, whole-skull, "
            "experimental, clinical, thermal, or safety validation.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_package(report: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "itrusst_phase_a_summary.json"
    csv_path = output_dir / "itrusst_phase_a_summary.csv"
    markdown_path = output_dir / "itrusst_phase_a_summary.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(csv_path, report["cases"])
    write_markdown(markdown_path, report)
    return {
        "json": str(json_path.resolve()),
        "csv": str(csv_path.resolve()),
        "markdown": str(markdown_path.resolve()),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bm1", type=Path, default=DEFAULT_CASES["BM1"])
    parser.add_argument("--bm3", type=Path, default=DEFAULT_CASES["BM3"])
    parser.add_argument("--bm4", type=Path, default=DEFAULT_CASES["BM4"])
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_summary(
        {
            "BM1": args.bm1.resolve(),
            "BM3": args.bm3.resolve(),
            "BM4": args.bm4.resolve(),
        }
    )
    outputs = write_package(report, args.output_dir.resolve())
    print(json.dumps({"status": report["status"], "outputs": outputs}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
