from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = (
    ROOT
    / "outputs"
    / "pub2_250khz_dry_run_matrix_refined_retry1_20260807"
)


@dataclass(frozen=True)
class Cell:
    cell_id: str
    changed_factor: str
    model: str
    entry_plan: str
    dx_mm: float
    pml_size: int
    cfl: float
    lateral_mm: float
    post_target_mm: float


CELLS = (
    Cell(
        "dx0p625_grid",
        "dx_mm",
        "outputs/pub2_case079_simple_hu300_dx0p625_semantics_20260807/acoustic_model_3d.npz",
        "outputs/pub2_entry_plan_source_refinement_20260807/dx0p625/entry_plan.json",
        0.625,
        12,
        0.2,
        30.0,
        16.0,
    ),
    Cell(
        "dx0p75_reference",
        "reference",
        "outputs/pub2_case079_simple_hu300_dx0p75_semantics_20260807/acoustic_model_3d.npz",
        "outputs/pub2_entry_plan_resolution_family_refined_20260807/dx0p75/entry_plan.json",
        0.75,
        12,
        0.2,
        30.0,
        16.0,
    ),
    Cell(
        "dx0p5_grid",
        "dx_mm",
        "outputs/pub2_case079_simple_hu300_dx0p5_semantics_retry1_20260807/acoustic_model_3d.npz",
        "outputs/pub2_entry_plan_source_refinement_20260807/dx0p5/entry_plan.json",
        0.5,
        12,
        0.2,
        30.0,
        16.0,
    ),
    Cell(
        "dx0p75_pml16",
        "pml_size",
        "outputs/pub2_case079_simple_hu300_dx0p75_semantics_20260807/acoustic_model_3d.npz",
        "outputs/pub2_entry_plan_resolution_family_refined_20260807/dx0p75/entry_plan.json",
        0.75,
        16,
        0.2,
        30.0,
        16.0,
    ),
    Cell(
        "dx0p75_cfl0p1",
        "cfl",
        "outputs/pub2_case079_simple_hu300_dx0p75_semantics_20260807/acoustic_model_3d.npz",
        "outputs/pub2_entry_plan_resolution_family_refined_20260807/dx0p75/entry_plan.json",
        0.75,
        12,
        0.1,
        30.0,
        16.0,
    ),
    Cell(
        "dx0p75_domain_lat34_post20",
        "domain_extent",
        "outputs/pub2_case079_simple_hu300_dx0p75_semantics_20260807/acoustic_model_3d.npz",
        "outputs/pub2_entry_plan_resolution_family_refined_20260807/dx0p75/entry_plan.json",
        0.75,
        12,
        0.2,
        34.0,
        20.0,
    ),
)

METHODS = ("baseline", "tr")
PRESSURE_ARTIFACTS = (
    "pressure_max_mpa.npz",
    "p_amp.npz",
    "element_signals.npz",
)
QUALITY_FIELDS = (
    "preset",
    "dx_m",
    "frequency_hz",
    "cfl",
    "pml_size",
    "grid_size",
    "voxel_count",
    "dt_s",
    "nt",
    "simulation_time_s",
)


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def common_arguments(cell: Cell, output_dir: Path) -> list[str]:
    return [
        "--preset",
        "standard",
        "--output-dir",
        relative(output_dir),
        "--model",
        cell.model,
        "--entry-plan",
        cell.entry_plan,
        "--frequency-hz",
        "250000",
        "--source-pressure-pa",
        "1000000",
        "--cycles",
        "2",
        "--sim-time-us",
        "100",
        "--pml-size",
        str(cell.pml_size),
        "--cfl",
        str(cell.cfl),
        "--quick-lateral-mm",
        str(cell.lateral_mm),
        "--quick-post-target-mm",
        str(cell.post_target_mm),
        "--aperture-mm",
        "60",
        "--radius-mm",
        "74.435",
        "--backend",
        "python",
        "--device",
        "cpu",
        "--dry-run-quality",
    ]


def command_for(cell: Cell, method: str, output_dir: Path) -> list[str]:
    common = common_arguments(cell, output_dir)
    if method == "baseline":
        return [sys.executable, "simulate_kwave_3d_focus.py", *common]
    if method == "tr":
        return [
            sys.executable,
            "simulate_time_reversal_focus.py",
            "--stage",
            "refocus",
            "--calibration-pressure-pa",
            "1000000",
            "--normalize",
            *common,
        ]
    raise ValueError(f"Unknown method: {method}")


def matrix_plan(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for cell in CELLS:
        for method in METHODS:
            output_dir = output_root / cell.cell_id / method
            entries.append(
                {
                    "cell_id": cell.cell_id,
                    "method": method,
                    "changed_factor": cell.changed_factor,
                    "configuration": asdict(cell),
                    "output_dir": relative(output_dir),
                    "command": command_for(cell, method, output_dir),
                }
            )
    return {
        "schema_version": "1.0",
        "status": "planned_dry_run_only",
        "design": "six numerical cells by two matched methods",
        "cell_count": len(CELLS),
        "dry_run_count": len(entries),
        "pressure_execution_authorized": False,
        "entries": entries,
    }


def load_quality(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def validate_result(
    cell: Cell,
    method: str,
    output_dir: Path,
) -> dict[str, Any]:
    quality_path = output_dir / "quality_dry_run_summary.json"
    if not quality_path.is_file():
        raise FileNotFoundError(f"Missing dry-run summary: {quality_path}")
    report = load_quality(quality_path)
    quality = report["simulation_quality"]
    source = report["source"]
    config = report["config"]
    pressure_files = [
        name for name in PRESSURE_ARTIFACTS if (output_dir / name).exists()
    ]
    checks = {
        "dry_run_quality_only": report.get("dry_run_quality_only") is True,
        "no_pressure_artifact": not pressure_files,
        "preset_standard": quality.get("preset") == "standard",
        "frequency_250khz": quality.get("frequency_hz") == 250000.0,
        "alpha_power_1p5": config.get("alpha_power") == 1.5,
        "alpha_semantics_explicit": (
            config.get("alpha_semantics_status")
            == "inferred_from_binary_materials"
        ),
        "source_background_only": (
            source.get("source_points", 0) > 0
            and set(source.get("source_label_counts", {})) == {"0"}
            and int(source["source_label_counts"]["0"])
            == int(source["source_points"])
        ),
        "entry_resolution_gate_not_bypassed": (
            config.get("allow_entry_plan_resolution_mismatch") is False
        ),
        "declared_pml_matches": quality.get("pml_size") == cell.pml_size,
        "declared_cfl_matches": quality.get("cfl") == cell.cfl,
        "declared_dx_matches": (
            abs(float(quality.get("dx_mm")) - cell.dx_mm)
            <= max(1e-6, cell.dx_mm * 1e-6)
        ),
    }
    return {
        "cell_id": cell.cell_id,
        "method": method,
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "pressure_artifacts_found": pressure_files,
        "quality_summary": relative(quality_path),
        "simulation_quality": {
            field: quality.get(field) for field in QUALITY_FIELDS
        },
        "ppw_min_sound_speed": quality.get("ppw_min_sound_speed"),
        "memory_estimate": quality.get("memory_estimate"),
        "source": {
            "source_points": source.get("source_points"),
            "source_label_counts": source.get("source_label_counts"),
        },
    }


def pair_drift(
    baseline: dict[str, Any], tr: dict[str, Any]
) -> dict[str, Any]:
    drift: dict[str, Any] = {}
    for field in QUALITY_FIELDS:
        left = baseline["simulation_quality"].get(field)
        right = tr["simulation_quality"].get(field)
        if left != right:
            drift[field] = {"baseline": left, "tr": right}
    for field in ("source_points", "source_label_counts"):
        left = baseline["source"].get(field)
        right = tr["source"].get(field)
        if left != right:
            drift[f"source.{field}"] = {"baseline": left, "tr": right}
    return drift


def execute_matrix(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    environment = os.environ.copy()
    for key in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        environment[key] = "4"
    results: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    for cell in CELLS:
        method_results: dict[str, dict[str, Any]] = {}
        for method in METHODS:
            output_dir = output_root / cell.cell_id / method
            quality_path = output_dir / "quality_dry_run_summary.json"
            if not quality_path.exists():
                output_dir.mkdir(parents=True, exist_ok=False)
                subprocess.run(
                    command_for(cell, method, output_dir),
                    cwd=ROOT,
                    env=environment,
                    check=True,
                )
            result = validate_result(cell, method, output_dir)
            results.append(result)
            method_results[method] = result
        drift = pair_drift(method_results["baseline"], method_results["tr"])
        pairs.append(
            {
                "cell_id": cell.cell_id,
                "changed_factor": cell.changed_factor,
                "baseline_tr_drift": drift,
                "matched": not drift,
            }
        )
    status = (
        "passed"
        if all(item["status"] == "passed" for item in results)
        and all(item["matched"] for item in pairs)
        else "failed"
    )
    return {
        "schema_version": "1.0",
        "status": status,
        "claim_level": "dry_run_resource_and_comparability_only",
        "results": results,
        "matched_pairs": pairs,
        "pressure_execution_authorized": False,
        "claim_boundary": (
            "Passing establishes dry-run resource and matched-design gates "
            "only; no pressure, convergence, efficacy or safety claim."
        ),
    }


def render_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PUB.2 250 kHz dry-run matrix",
        "",
        f"- Status: **{report['status']}**",
        "- Pressure execution authorized: **no**",
        "",
        "| Cell | Factor | Grid | Voxels | Nt | PPW | PML | CFL | Memory (MB) | Source | Matched |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    pairs = {
        item["cell_id"]: item for item in report["matched_pairs"]
    }
    factors = {cell.cell_id: cell.changed_factor for cell in CELLS}
    for item in report["results"]:
        if item["method"] != "baseline":
            continue
        quality = item["simulation_quality"]
        memory = item["memory_estimate"]
        lines.append(
            f"| `{item['cell_id']}` | `{factors[item['cell_id']]}` | "
            f"{'x'.join(str(value) for value in quality['grid_size'])} | "
            f"{quality['voxel_count']} | {quality['nt']} | "
            f"{item['ppw_min_sound_speed']:.3f} | "
            f"{quality['pml_size']} | {quality['cfl']:.3f} | "
            f"{memory['estimated_mb']:.2f} | "
            f"{item['source']['source_points']} | "
            f"{pairs[item['cell_id']]['matched']} |"
        )
    lines.extend(
        [
            "",
            "Every baseline/TR pair matches on the frozen dry-run quality and source fields. "
            "All source points are label-0 background.",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan or execute the PUB.2 250 kHz dry-run-only matrix."
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    plan = matrix_plan(output_root)
    (output_root / "dry_run_matrix_plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": plan["status"],
                    "dry_run_count": plan["dry_run_count"],
                    "pressure_execution_authorized": False,
                }
            )
        )
        return 0
    report = execute_matrix(output_root)
    report_path = output_root / "dry_run_matrix_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_root / "dry_run_matrix_report.md").write_text(
        render_report_markdown(report),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(report_path),
                "pressure_execution_authorized": False,
            }
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
