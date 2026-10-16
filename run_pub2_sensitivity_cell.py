"""Parameterized PUB.2 one-variable sensitivity cell runner.

Runs a single frozen sensitivity cell (baseline OR time-reversal pair) from the
already-passed dry-run matrix. This is the generic counterpart of the cell-specific
runners already used for PML16 and CFL0.1, so the remaining dx0.5-grid, TR-CFL and
expanded-domain cells can be launched with one command each.

A cell is launched by ``--cell-id`` + ``--method`` (baseline | tr). Every cell
configuration, frozen command, expected grid/time/source and output root are taken
from the passed dry-run matrix plan/report; nothing is hard-coded per cell except
the high-level factors (dx/pml/cfl) used for the single-variable assertion.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_pub2_250khz_reference_pair as pair
from windows_process_tree_guard import (
    GuardThresholds,
    ProcessTreeSampler,
    breach_reasons,
    set_below_normal_priority,
    terminate_process_tree,
)

ROOT = Path(__file__).resolve().parent
MATRIX_PLAN = ROOT / "outputs" / "pub2_250khz_dry_run_matrix_refined_retry1_20260807" / "dry_run_matrix_plan.json"
MATRIX_REPORT = ROOT / "outputs" / "pub2_250khz_dry_run_matrix_refined_retry1_20260807" / "dry_run_matrix_report.json"
REFERENCE_COMPLETION = ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807" / "reference_completion_status.json"

DEFAULT_DEPENDENCIES = {
    "completion": REFERENCE_COMPLETION,
    "matrix_plan": MATRIX_PLAN,
    "matrix_report": MATRIX_REPORT,
}

MAXIMUM_MINUTES = 240.0
WORKING_SET_GIB = 16.0


@dataclass(frozen=True)
class Cell:
    cell_id: str
    changed_factor: str
    dx_mm: float
    pml_size: int
    cfl: float
    grid: tuple[int, int, int]
    nt: int
    source_points: int
    baseline_root: Path
    tr_root: Path


_CELLS = {
    "dx0p5_grid": Cell(
        "dx0p5_grid", "dx_mm", 0.5, 12, 0.2, (192, 146, 151), 2800, 11094,
        ROOT / "outputs" / "pub2_250khz_dx0p5_grid_20260814",
        ROOT / "outputs" / "pub2_250khz_dx0p5_grid_tr_20260814",
    ),
    "dx0p75_cfl0p1": Cell(
        "dx0p75_cfl0p1", "cfl", 0.75, 12, 0.1, (133, 98, 101), 3734, 4971,
        ROOT / "outputs" / "pub2_250khz_cfl0p1_baseline_20260812",  # already run
        ROOT / "outputs" / "pub2_250khz_cfl0p1_tr_20260814",
    ),
    "dx0p75_domain_lat34_post20": Cell(
        "dx0p75_domain_lat34_post20", "domain_extent", 0.75, 12, 0.2, (139, 108, 111), 1867, 4971,
        ROOT / "outputs" / "pub2_250khz_domain_lat34_post20_20260814",
        ROOT / "outputs" / "pub2_250khz_domain_lat34_post20_tr_20260814",
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def cell_for(cell_id: str) -> Cell:
    if cell_id not in _CELLS:
        raise ValueError(f"Unknown cell_id {cell_id!r}; choose from {sorted(_CELLS)}")
    return _CELLS[cell_id]


def stages_for(method: str) -> tuple[pair.Stage, ...]:
    if method == "baseline":
        return (pair.STAGES[0],)
    if method == "tr":
        return (pair.STAGES[1], pair.STAGES[2])
    raise ValueError(f"method must be 'baseline' or 'tr', got {method!r}")


def output_dir_for(cell: Cell, method: str) -> Path:
    # 实际压力/校准产物输出目录；TR 校准与重聚焦共用 tr/ 子目录。
    return (cell.baseline_root if method == "baseline" else cell.tr_root / "tr").resolve()


def status_root_for(cell: Cell, method: str) -> Path:
    # execution/device/history 等状态文件目录。
    return (cell.baseline_root if method == "baseline" else cell.tr_root).resolve()


def frozen_entry(cell: Cell, method: str, plan_path: Path | None = None) -> dict[str, Any]:
    plan = pair.load_json(plan_path or MATRIX_PLAN)
    matches = [
        item for item in plan.get("entries", [])
        if item.get("cell_id") == cell.cell_id and item.get("method") == method
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one frozen {cell.cell_id}/{method} entry, found {len(matches)}")
    return matches[0]


def child_command(cell: Cell, method: str, stage: pair.Stage, output_dir: Path, *, dry_run: bool, entry: dict[str, Any] | None = None) -> list[str]:
    entry = entry if entry is not None else frozen_entry(cell, method)
    command = [str(value) for value in entry["command"]]
    command[0] = sys.executable
    command[command.index("--output-dir") + 1] = str(output_dir.resolve())
    if method == "tr":
        command[command.index("--stage") + 1] = str(stage.tr_stage)
    if dry_run:
        if "--dry-run-quality" not in command:
            command.append("--dry-run-quality")
    else:
        if "--dry-run-quality" in command:
            command.remove("--dry-run-quality")
    if stage.stage_id == "tr_refocus" and "--no-record-target-waveform" not in command:
        command.append("--no-record-target-waveform")
    return command


def monitor_command(cell: Cell, method: str, stage: pair.Stage, output_dir: Path) -> list[str]:
    return [
        sys.executable, "-m", "monitor_kwave_process",
        "--output-dir", str(output_dir.resolve()),
        "--checkpoint-sec", "120", "--poll-sec", "5",
        "--stall-stop-min", "20", "--emergency-ceiling-min", "210",
        "--maximum-ceiling-min", f"{MAXIMUM_MINUTES:.3f}", "--",
        *child_command(cell, method, stage, output_dir, dry_run=False),
    ]


def preflight(cell: Cell, method: str, *, deps: dict[str, Path] | None = None, output_dir: Path | None = None) -> dict[str, Any]:
    paths = DEFAULT_DEPENDENCIES if deps is None else deps
    completion = pair.load_json(paths["completion"])
    plan = pair.load_json(paths["matrix_plan"])
    report = pair.load_json(paths["matrix_report"])
    entry = frozen_entry(cell, method, paths["matrix_plan"])
    results = [item for item in report.get("results", []) if item.get("cell_id") == cell.cell_id and item.get("method") == method]
    result = results[0] if len(results) == 1 else {}
    matched = [item for item in report.get("matched_pairs", []) if item.get("cell_id") == cell.cell_id]
    match = matched[0] if len(matched) == 1 else {}
    config = entry.get("configuration", {})
    quality = result.get("simulation_quality", {})
    source = result.get("source", {})
    output_dir = output_dir_for(cell, method) if output_dir is None else output_dir
    checks = {
        "reference_completion_passed": completion.get("status") == "completed",
        "matrix_report_passed": report.get("status") == "passed" and result.get("status") == "passed",
        "baseline_tr_matrix_pair_matched": match.get("matched") is True and not match.get("baseline_tr_drift"),
        "single_variable_configuration": (
            float(config.get("dx_mm", -1)) == cell.dx_mm
            and int(config.get("pml_size", -1)) == cell.pml_size
            and float(config.get("cfl", -1)) == cell.cfl
        ),
        "dry_run_grid_and_time_frozen": (
            quality.get("grid_size") == list(cell.grid) and int(quality.get("nt", -1)) == cell.nt
            and int(quality.get("pml_size", -1)) == cell.pml_size and float(quality.get("cfl", -1)) == cell.cfl
        ),
        "source_background_only": (
            int(source.get("source_points", -1)) == cell.source_points
            and source.get("source_label_counts") == {"0": cell.source_points}
        ),
        "no_existing_core_outputs": not any(
            (output_dir / name).exists()
            for name in ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json", "element_signals.npz")
        ),
    }
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "cell_id": cell.cell_id, "method": method, "checks": checks, "frozen_entry": entry,
        "output_dir": str(output_dir),
        "device_policy": {"thread_environment_limit": 6, "priority": "BelowNormal",
                          "maximum_equivalent_cores": 6.5, "maximum_working_set_gib": WORKING_SET_GIB,
                          "minimum_free_memory_gib": 4.0},
    }


def run_stage(cell: Cell, method: str, stage: pair.Stage, output_dir: Path, status_root: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    root = status_root
    prefix = stage.stage_id if method == "tr" else "baseline"
    status_path = root / f"{prefix}_execution_status.json"
    device_path = root / f"{prefix}_device_status.json"
    history_path = root / f"{prefix}_device_history.jsonl"
    stdout_path = root / f"{prefix}_launcher_stdout.txt"
    stderr_path = root / f"{prefix}_launcher_stderr.txt"
    command = monitor_command(cell, method, stage, output_dir)
    environment = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        environment[key] = "6"
    creation_flags = 0x00004000 | 0x08000000 if os.name == "nt" else 0
    pair.atomic_json(status_path, {"status": "running", "at_utc": utc_now(), "command": command})
    stopped_reason: str | None = None
    with stdout_path.open("wb") as out_h, stderr_path.open("wb") as err_h:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=out_h, stderr=err_h, creationflags=creation_flags)
        set_below_normal_priority(process.pid)
        sampler = ProcessTreeSampler(process.pid)
        thresholds = GuardThresholds(maximum_working_set_gib=WORKING_SET_GIB)
        cpu_streak = 0
        while process.poll() is None:
            sample = sampler.sample()
            sample["at_utc"] = utc_now()
            reasons = breach_reasons(sample, thresholds)
            cpu_streak = cpu_streak + 1 if "equivalent_cpu_cores" in reasons else 0
            immediate = [r for r in reasons if r != "equivalent_cpu_cores"]
            if cpu_streak >= 3:
                immediate.append("sustained_equivalent_cpu_cores")
            sample["cpu_breach_streak"] = cpu_streak
            sample["breach_reasons"] = immediate
            with history_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
            pair.atomic_json(device_path, {"status": "stopping" if immediate else "running",
                                           "cell_id": cell.cell_id, "stage_id": stage.stage_id, "latest_sample": sample})
            if immediate:
                stopped_reason = ",".join(immediate)
                terminate_process_tree(process.pid)
                break
            time.sleep(10.0)
        return_code = process.wait()
    validation = pair.validate_stage_outputs(stage, output_dir)
    result = {"stage_id": stage.stage_id, "return_code": return_code, "stopped_reason": stopped_reason,
              "output_validation": validation,
              "status": "completed" if return_code == 0 and stopped_reason is None and validation["status"] == "passed" else "failed",
              "finished_at_utc": utc_now()}
    pair.atomic_json(root / f"{prefix}_stage_result.json", result)
    pair.atomic_json(status_path, {"status": result["status"], "result": result})
    return result


def run(cell: Cell, method: str) -> dict[str, Any]:
    gate = preflight(cell, method)
    if gate["status"] != "passed":
        raise RuntimeError(f"{cell.cell_id}/{method} preflight failed: {gate['checks']}")
    output_dir = output_dir_for(cell, method)
    status_root = status_root_for(cell, method)
    output_dir.mkdir(parents=True, exist_ok=True)
    status_root.mkdir(parents=True, exist_ok=True)
    chain_path = status_root / ("chain_status.json" if method == "tr" else "stage_result.json")
    pair.atomic_json(chain_path, {"status": "running", "at_utc": utc_now(), "preflight": gate})
    results = []
    for stage in stages_for(method):
        result = run_stage(cell, method, stage, output_dir, status_root)
        results.append(result)
        if result["status"] != "completed":
            break
    status = "completed" if results and all(item["status"] == "completed" for item in results) else "failed"
    pair.atomic_json(chain_path, {"status": status, "finished_at_utc": utc_now(), "automatic_rerun": False, "results": results})
    return {"status": status, "cell_id": cell.cell_id, "method": method, "results": results}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cell-id", required=True, choices=sorted(_CELLS))
    parser.add_argument("--method", required=True, choices=["baseline", "tr"])
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cell = cell_for(args.cell_id)
    try:
        if args.execute:
            value = run(cell, args.method)
        else:
            value = {"status": "planned_not_executed", "preflight": preflight(cell, args.method),
                     "commands": [child_command(cell, args.method, stage, output_dir_for(cell, args.method), dry_run=False) for stage in stages_for(args.method)],
                     "maximum_minutes_per_stage": MAXIMUM_MINUTES}
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, ensure_ascii=False))
    return 0 if value.get("status") in {"passed", "completed", "planned_not_executed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
