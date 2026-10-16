from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from windows_process_tree_guard import (
    GuardThresholds,
    ProcessTreeSampler,
    breach_reasons,
    set_below_normal_priority,
    terminate_process_tree,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = (
    ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807"
)
MODEL = (
    "outputs/pub2_case079_simple_hu300_dx0p75_semantics_20260807/"
    "acoustic_model_3d.npz"
)
ENTRY_PLAN = (
    "outputs/pub2_entry_plan_resolution_family_refined_20260807/"
    "dx0p75/entry_plan.json"
)
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
DRY_RUN_MATRIX = (
    ROOT
    / "outputs"
    / "pub2_250khz_dry_run_matrix_refined_retry1_20260807"
    / "dry_run_matrix_report.json"
)


@dataclass(frozen=True)
class Stage:
    stage_id: str
    method: str
    tr_stage: str | None
    output_subdir: str
    maximum_minutes: float
    projected_minutes: float
    required_files: tuple[str, ...]


STAGES = (
    Stage(
        "baseline",
        "baseline",
        None,
        "baseline",
        240.0,
        180.0,
        (
            "pressure_max_mpa.npz",
            "summary.json",
            "focus_metrics.json",
        ),
    ),
    Stage(
        "tr_calibrate",
        "tr",
        "calibrate",
        "tr",
        240.0,
        180.0,
        ("element_signals.npz", "summary_calibrate.json"),
    ),
    Stage(
        "tr_refocus",
        "tr",
        "refocus",
        "tr",
        210.0,
        150.0,
        (
            "pressure_max_mpa.npz",
            "summary.json",
            "focus_metrics.json",
        ),
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def preflight() -> dict[str, Any]:
    equivalence = load_json(MODEL_EQUIVALENCE)
    entry_family = load_json(ENTRY_FAMILY)
    dry_matrix = load_json(DRY_RUN_MATRIX)
    reference_results = [
        item
        for item in dry_matrix["results"]
        if item["cell_id"] == "dx0p75_reference"
    ]
    reference_pair = next(
        item
        for item in dry_matrix["matched_pairs"]
        if item["cell_id"] == "dx0p75_reference"
    )
    checks = {
        "model_equivalence_passed": (
            equivalence.get("status") == "passed"
            and equivalence.get("physical_arrays_equal") is True
            and equivalence.get("candidate_alpha_metadata_matches") is True
        ),
        "entry_family_passed": entry_family.get("status") == "passed",
        "dry_run_matrix_passed": dry_matrix.get("status") == "passed",
        "reference_has_two_methods": (
            {item["method"] for item in reference_results}
            == {"baseline", "tr"}
        ),
        "reference_methods_passed": all(
            item.get("status") == "passed" for item in reference_results
        ),
        "reference_pair_matched": (
            reference_pair.get("matched") is True
            and not reference_pair.get("baseline_tr_drift")
        ),
        "reference_sources_background_only": all(
            item["source"]["source_label_counts"] == {"0": 4971}
            for item in reference_results
        ),
        "no_preexisting_authoritative_output": True,
    }
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "reports": {
            "model_equivalence": str(MODEL_EQUIVALENCE),
            "entry_family": str(ENTRY_FAMILY),
            "dry_run_matrix": str(DRY_RUN_MATRIX),
        },
    }


def common_arguments(output_dir: Path) -> list[str]:
    return [
        "--preset",
        "standard",
        "--output-dir",
        str(output_dir),
        "--model",
        MODEL,
        "--entry-plan",
        ENTRY_PLAN,
        "--frequency-hz",
        "250000",
        "--source-pressure-pa",
        "1000000",
        "--cycles",
        "2",
        "--sim-time-us",
        "100",
        "--pml-size",
        "12",
        "--cfl",
        "0.2",
        "--quick-lateral-mm",
        "30",
        "--quick-post-target-mm",
        "16",
        "--aperture-mm",
        "60",
        "--radius-mm",
        "74.435",
        "--backend",
        "python",
        "--device",
        "cpu",
    ]


def child_command(stage: Stage, output_dir: Path) -> list[str]:
    common = common_arguments(output_dir)
    if stage.method == "baseline":
        return [sys.executable, "simulate_kwave_3d_focus.py", *common]
    return [
        sys.executable,
        "simulate_time_reversal_focus.py",
        "--stage",
        str(stage.tr_stage),
        "--calibration-pressure-pa",
        "1000000",
        "--normalize",
        *common,
    ]


def monitor_command(
    stage: Stage,
    output_dir: Path,
    maximum_minutes: float,
) -> list[str]:
    emergency = min(maximum_minutes, stage.projected_minutes + 30.0)
    return [
        sys.executable,
        "-m",
        "monitor_kwave_process",
        "--output-dir",
        str(output_dir),
        "--checkpoint-sec",
        "120",
        "--poll-sec",
        "5",
        "--stall-stop-min",
        "20",
        "--emergency-ceiling-min",
        f"{emergency:.3f}",
        "--maximum-ceiling-min",
        f"{maximum_minutes:.3f}",
        "--",
        *child_command(stage, output_dir),
    ]


def plan(output_root: Path, global_budget_minutes: float) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "status": "planned_not_executed",
        "preflight": preflight(),
        "output_root": str(output_root),
        "global_budget_minutes": global_budget_minutes,
        "device_policy": {
            "thread_environment_limit": 6,
            "priority": "BelowNormal",
            "maximum_sustained_equivalent_cores": 6.5,
            "cpu_breach_consecutive_samples": 3,
            "maximum_process_tree_working_set_gib": 12.0,
            "minimum_system_free_memory_gib": 4.0,
            "sample_interval_seconds": 10.0,
        },
        "stages": [
            {
                "stage_id": stage.stage_id,
                "output_dir": str(output_root / stage.output_subdir),
                "projected_minutes": stage.projected_minutes,
                "maximum_minutes": stage.maximum_minutes,
                "required_files": list(stage.required_files),
                "command": child_command(
                    stage, output_root / stage.output_subdir
                ),
            }
            for stage in STAGES
        ],
        "pressure_execution_authorized": [
            stage.stage_id for stage in STAGES
        ],
        "automatic_follow_on_sensitivity_cells_authorized": False,
    }


def numeric_npz_is_finite_nonzero(
    path: Path, *, required_nonzero_array: str | None = None
) -> bool:
    with np.load(path, allow_pickle=False) as archive:
        arrays = {
            key: np.asarray(archive[key])
            for key in archive.files
            if np.issubdtype(np.asarray(archive[key]).dtype, np.number)
        }
        if (
            required_nonzero_array is not None
            and required_nonzero_array not in arrays
        ):
            return False
        core = (
            arrays.get(required_nonzero_array)
            if required_nonzero_array is not None
            else None
        )
    return bool(
        arrays
        and all(np.all(np.isfinite(array)) for array in arrays.values())
        and (
            np.any(np.abs(core) > 0)
            if core is not None
            else any(
                np.any(np.abs(array) > 0)
                for array in arrays.values()
            )
        )
    )


def validate_stage_outputs(
    stage: Stage, output_dir: Path
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    for name in stage.required_files:
        path = output_dir / name
        checks[f"{name}.exists"] = path.is_file()
        if not path.is_file():
            continue
        if path.suffix == ".json":
            try:
                load_json(path)
                checks[f"{name}.json_valid"] = True
            except (ValueError, json.JSONDecodeError):
                checks[f"{name}.json_valid"] = False
        elif path.suffix == ".npz":
            try:
                required_array = {
                    "pressure_max_mpa.npz": "pressure_max_mpa",
                    "element_signals.npz": "signals",
                }.get(name)
                checks[f"{name}.finite_nonzero"] = (
                    numeric_npz_is_finite_nonzero(
                        path,
                        required_nonzero_array=required_array,
                    )
                )
            except (ValueError, OSError):
                checks[f"{name}.finite_nonzero"] = False
    return {
        "status": "passed" if checks and all(checks.values()) else "failed",
        "checks": checks,
    }


def copy_monitor_snapshot(
    stage: Stage, output_dir: Path, snapshot_root: Path
) -> None:
    stage_root = snapshot_root / stage.stage_id
    stage_root.mkdir(parents=True, exist_ok=False)
    for name in (
        "monitor_status.json",
        "monitor_history.jsonl",
        "monitor_attention.json",
        "monitored_stdout.txt",
        "monitored_stderr.txt",
    ):
        source = output_dir / name
        if source.exists():
            shutil.copy2(source, stage_root / name)


def run_monitored_stage(
    stage: Stage,
    output_dir: Path,
    *,
    maximum_minutes: float,
    global_deadline: float,
    output_root: Path,
) -> dict[str, Any]:
    allow_existing_stage_dir = stage.stage_id == "tr_refocus"
    output_dir.mkdir(
        parents=True, exist_ok=allow_existing_stage_dir
    )
    if allow_existing_stage_dir:
        calibration_requirements = (
            output_dir / "element_signals.npz",
            output_dir / "summary_calibrate.json",
        )
        if not all(path.is_file() for path in calibration_requirements):
            raise FileNotFoundError(
                "TR refocus requires completed calibration artifacts."
            )
    environment = os.environ.copy()
    for key in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        environment[key] = "6"
    command = monitor_command(stage, output_dir, maximum_minutes)
    launcher_stdout = (
        output_root / f"{stage.stage_id}_launcher_stdout.txt"
    )
    launcher_stderr = (
        output_root / f"{stage.stage_id}_launcher_stderr.txt"
    )
    creation_flags = (
        0x00004000 | 0x08000000 if os.name == "nt" else 0
    )
    with launcher_stdout.open("wb") as stdout_handle, launcher_stderr.open(
        "wb"
    ) as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=creation_flags,
        )
        set_below_normal_priority(process.pid)
        sampler = ProcessTreeSampler(process.pid)
        thresholds = GuardThresholds()
        history_path = (
            output_root / f"{stage.stage_id}_device_history.jsonl"
        )
        status_path = (
            output_root / f"{stage.stage_id}_device_status.json"
        )
        cpu_breach_streak = 0
        stopped_reason: str | None = None
        while process.poll() is None:
            sample = sampler.sample()
            sample["at_utc"] = utc_now()
            reasons = breach_reasons(sample, thresholds)
            if "equivalent_cpu_cores" in reasons:
                cpu_breach_streak += 1
            else:
                cpu_breach_streak = 0
            immediate = [
                reason
                for reason in reasons
                if reason != "equivalent_cpu_cores"
            ]
            if cpu_breach_streak >= 3:
                immediate.append("sustained_equivalent_cpu_cores")
            if time.monotonic() >= global_deadline:
                immediate.append("global_chain_budget")
            sample["cpu_breach_streak"] = cpu_breach_streak
            sample["breach_reasons"] = immediate
            append_jsonl(history_path, sample)
            atomic_json(
                status_path,
                {
                    "status": (
                        "stopping" if immediate else "running"
                    ),
                    "stage": stage.stage_id,
                    "latest_sample": sample,
                },
            )
            if immediate:
                stopped_reason = ",".join(immediate)
                terminate_process_tree(process.pid)
                break
            time.sleep(10.0)
        return_code = process.wait()
    validation = validate_stage_outputs(stage, output_dir)
    result = {
        "stage_id": stage.stage_id,
        "return_code": return_code,
        "stopped_reason": stopped_reason,
        "output_validation": validation,
        "status": (
            "completed"
            if return_code == 0
            and stopped_reason is None
            and validation["status"] == "passed"
            else "failed"
        ),
    }
    atomic_json(
        output_root / f"{stage.stage_id}_stage_result.json",
        result,
    )
    return result


def execute(
    output_root: Path, global_budget_minutes: float
) -> dict[str, Any]:
    preflight_result = preflight()
    if preflight_result["status"] != "passed":
        raise RuntimeError(f"Preflight failed: {preflight_result}")
    if output_root.exists():
        raise FileExistsError(
            f"Refusing existing output root: {output_root}"
        )
    output_root.mkdir(parents=True)
    plan_value = plan(output_root, global_budget_minutes)
    atomic_json(output_root / "execution_plan.json", plan_value)
    started = time.monotonic()
    global_deadline = started + global_budget_minutes * 60.0
    chain_status: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "running",
        "started_at_utc": utc_now(),
        "preflight": preflight_result,
        "stages": [],
        "pressure_scope": [stage.stage_id for stage in STAGES],
        "automatic_follow_on_sensitivity_cells_authorized": False,
    }
    atomic_json(output_root / "chain_status.json", chain_status)
    snapshot_root = output_root / "monitor_snapshots"
    for stage in STAGES:
        remaining_minutes = (
            global_deadline - time.monotonic()
        ) / 60.0
        if remaining_minutes < stage.projected_minutes + 15.0:
            chain_status["status"] = "stopped_before_stage"
            chain_status["stop_reason"] = (
                f"Insufficient global budget for {stage.stage_id}: "
                f"{remaining_minutes:.1f} min remaining."
            )
            atomic_json(output_root / "chain_status.json", chain_status)
            return chain_status
        output_dir = output_root / stage.output_subdir
        maximum_minutes = min(
            stage.maximum_minutes, remaining_minutes
        )
        result = run_monitored_stage(
            stage,
            output_dir,
            maximum_minutes=maximum_minutes,
            global_deadline=global_deadline,
            output_root=output_root,
        )
        copy_monitor_snapshot(
            stage, output_dir, snapshot_root
        )
        chain_status["stages"].append(result)
        chain_status["updated_at_utc"] = utc_now()
        atomic_json(output_root / "chain_status.json", chain_status)
        if result["status"] != "completed":
            chain_status["status"] = "failed"
            chain_status["stop_reason"] = (
                f"Stage {stage.stage_id} did not complete."
            )
            atomic_json(output_root / "chain_status.json", chain_status)
            return chain_status
    chain_status["status"] = "completed"
    chain_status["finished_at_utc"] = utc_now()
    chain_status["elapsed_s"] = time.monotonic() - started
    atomic_json(output_root / "chain_status.json", chain_status)
    return chain_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the exact evidence-gated PUB.2 dx0.75 reference pair."
        )
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    parser.add_argument(
        "--global-budget-min", type=float, default=525.0
    )
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_dir.resolve()
    if not args.execute:
        value = plan(output_root, args.global_budget_min)
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return 0 if value["preflight"]["status"] == "passed" else 1
    result = execute(output_root, args.global_budget_min)
    print(
        json.dumps(
            {
                "status": result["status"],
                "output_root": str(output_root),
                "completed_stages": len(result["stages"]),
            }
        )
    )
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
