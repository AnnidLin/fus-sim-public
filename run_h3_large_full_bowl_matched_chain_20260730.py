from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "outputs" / "h3_large_full_bowl_matched_standard_20260730"
MODEL = "outputs\\ct_acoustic_model_3d_profile_hu300_dx0p75\\acoustic_model_3d.npz"
ENTRY_PLAN = (
    "outputs\\a5_heldout_d60_trajectory_selection_20260719"
    "\\offset_y+12p5_z-15p0\\entry_plan.json"
)
BASELINE_DRY_RUN = (
    ROOT / "outputs" / "h3_large_full_bowl_domain_search_20260730"
    / "lat30_post16_baseline" / "quality_dry_run_summary.json"
)
TR_DRY_RUN = (
    ROOT / "outputs" / "h3_large_full_bowl_domain_search_20260730"
    / "lat30_post16_tr" / "quality_dry_run_summary.json"
)
CHAIN_BUDGET_MINUTES = 480
EXPECTED_SOURCE_POINTS = 4971


@dataclass(frozen=True)
class Stage:
    name: str
    method: str
    output_subdir: str
    required_files: tuple[str, ...]


STAGES = (
    Stage(
        "baseline",
        "baseline",
        "baseline",
        ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json"),
    ),
    Stage(
        "calibrate",
        "tr",
        "tr",
        ("element_signals.npz", "summary_calibrate.json"),
    ),
    Stage(
        "refocus",
        "tr",
        "tr",
        ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json"),
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def validate_dry_run_pair(
    baseline_path: Path = BASELINE_DRY_RUN,
    tr_path: Path = TR_DRY_RUN,
) -> dict[str, Any]:
    baseline = load_json(baseline_path)
    tr = load_json(tr_path)
    quality_fields = (
        "preset",
        "grid_size",
        "voxel_count",
        "nt",
        "ppw_min_sound_speed",
        "pml_size",
        "cfl",
    )
    drift: dict[str, Any] = {}
    for field in quality_fields:
        left = baseline["simulation_quality"].get(field)
        right = tr["simulation_quality"].get(field)
        if left != right:
            drift[field] = {"baseline": left, "tr": right}
    for field in ("source_points", "source_label_counts"):
        left = baseline["source"].get(field)
        right = tr["source"].get(field)
        if left != right:
            drift[f"source.{field}"] = {"baseline": left, "tr": right}
    if drift:
        raise RuntimeError(f"dry-run drift: {drift}")

    source_points = int(baseline["source"]["source_points"])
    label_counts = baseline["source"]["source_label_counts"]
    if source_points != EXPECTED_SOURCE_POINTS:
        raise RuntimeError(
            f"full-bowl source incomplete: {source_points} != {EXPECTED_SOURCE_POINTS}"
        )
    if label_counts != {"0": EXPECTED_SOURCE_POINTS}:
        raise RuntimeError(f"source is not background-only: {label_counts}")
    if not baseline.get("dry_run_quality_only") or not tr.get(
        "dry_run_quality_only"
    ):
        raise RuntimeError("quality gate input is not dry-run-only")
    quality = baseline["simulation_quality"]
    return {
        "grid_size": quality["grid_size"],
        "voxel_count": quality["voxel_count"],
        "nt": quality["nt"],
        "ppw_min_sound_speed": quality["ppw_min_sound_speed"],
        "pml_size": quality["pml_size"],
        "cfl": quality["cfl"],
        "source_points": source_points,
        "source_label_counts": label_counts,
    }


def common_arguments(output_dir: Path) -> list[str]:
    return [
        "--preset",
        "standard",
        "--output-dir",
        str(output_dir.relative_to(ROOT)),
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
    if stage.method == "baseline":
        return [
            sys.executable,
            "simulate_kwave_3d_focus.py",
            *common_arguments(output_dir),
        ]
    return [
        sys.executable,
        "simulate_time_reversal_focus.py",
        "--stage",
        stage.name,
        "--calibration-pressure-pa",
        "1000000",
        "--normalize",
        *common_arguments(output_dir),
    ]


def monitored_command(
    stage: Stage, output_dir: Path, maximum_minutes: float
) -> list[str]:
    emergency_minutes = min(180.0, maximum_minutes)
    return [
        sys.executable,
        "-m",
        "monitor_kwave_process",
        "--output-dir",
        str(output_dir.relative_to(ROOT)),
        "--checkpoint-sec",
        "120",
        "--poll-sec",
        "5",
        "--stall-stop-min",
        "20",
        "--emergency-ceiling-min",
        f"{emergency_minutes:.3f}",
        "--maximum-ceiling-min",
        f"{maximum_minutes:.3f}",
        "--",
        *child_command(stage, output_dir),
    ]


def write_status(status: dict[str, Any]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_ROOT / "chain_status.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def ensure_stage_can_start(stage: Stage, output_dir: Path) -> None:
    if stage.name == "refocus":
        for name in STAGES[1].required_files:
            if not (output_dir / name).is_file():
                raise RuntimeError(f"refocus prerequisite missing: {name}")
    for name in stage.required_files:
        if (output_dir / name).exists():
            raise RuntimeError(f"output collision for {stage.name}: {name}")


def main() -> int:
    gate = validate_dry_run_pair()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {
        "module": "freq250_h3_large_full_bowl_intermediate_domain_20260730",
        "status": "running",
        "started_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "chain_budget_minutes": CHAIN_BUDGET_MINUTES,
        "dry_run_gate": gate,
        "stages": [
            {"name": stage.name, "status": "pending", "return_code": None}
            for stage in STAGES
        ],
    }
    write_status(status)
    started = time.monotonic()

    for index, stage in enumerate(STAGES):
        elapsed_minutes = (time.monotonic() - started) / 60.0
        remaining_minutes = CHAIN_BUDGET_MINUTES - elapsed_minutes
        if remaining_minutes < 30.0:
            status["status"] = "budget_exhausted"
            status["updated_at_utc"] = utc_now()
            status["failure"] = {
                "stage": stage.name,
                "reason": "less than 30 minutes remain in chain budget",
            }
            write_status(status)
            return 2

        output_dir = OUTPUT_ROOT / stage.output_subdir
        output_dir.mkdir(parents=True, exist_ok=True)
        ensure_stage_can_start(stage, output_dir)
        entry = status["stages"][index]
        entry.update(
            {
                "status": "running",
                "started_at_utc": utc_now(),
                "maximum_ceiling_minutes": remaining_minutes,
                "command": child_command(stage, output_dir),
            }
        )
        status["current_stage"] = stage.name
        status["updated_at_utc"] = utc_now()
        write_status(status)

        completed = subprocess.run(
            monitored_command(stage, output_dir, remaining_minutes),
            cwd=ROOT,
            check=False,
        )
        entry["return_code"] = completed.returncode
        entry["finished_at_utc"] = utc_now()
        entry["required_outputs_complete"] = all(
            (output_dir / name).is_file() for name in stage.required_files
        )
        monitor_path = output_dir / "monitor_status.json"
        monitor = load_json(monitor_path) if monitor_path.is_file() else {}
        entry["monitor_status"] = monitor.get("status")
        entry["status"] = (
            "completed"
            if completed.returncode == 0
            and monitor.get("status") == "completed"
            and entry["required_outputs_complete"]
            else "failed"
        )
        status["updated_at_utc"] = utc_now()
        if entry["status"] != "completed":
            status["status"] = "failed"
            status["failure"] = {
                "stage": stage.name,
                "return_code": completed.returncode,
                "monitor_status": monitor.get("status"),
            }
            write_status(status)
            return 1
        write_status(status)

    status["status"] = "completed"
    status["current_stage"] = None
    status["finished_at_utc"] = utc_now()
    status["updated_at_utc"] = utc_now()
    status["elapsed_minutes"] = (time.monotonic() - started) / 60.0
    write_status(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
