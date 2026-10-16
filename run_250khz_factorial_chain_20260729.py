from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "outputs" / "factorial_250khz_trajectory_transducer_20260729"
MODEL = "outputs\\ct_acoustic_model_3d_profile_hu300_dx0p75\\acoustic_model_3d.npz"
CELLS = (
    {
        "name": "default_small",
        "entry": "outputs\\entry_plan_079_offset_y+5_z0\\entry_plan.json",
        "aperture_mm": 15,
        "radius_mm": 30,
    },
    {
        "name": "default_large",
        "entry": "outputs\\entry_plan_079_offset_y+5_z0\\entry_plan.json",
        "aperture_mm": 60,
        "radius_mm": 74.435,
    },
    {
        "name": "h3_small",
        "entry": (
            "outputs\\a5_heldout_d60_trajectory_selection_20260719"
            "\\offset_y+12p5_z-15p0\\entry_plan.json"
        ),
        "aperture_mm": 15,
        "radius_mm": 30,
    },
    {
        "name": "h3_large",
        "entry": (
            "outputs\\a5_heldout_d60_trajectory_selection_20260719"
            "\\offset_y+12p5_z-15p0\\entry_plan.json"
        ),
        "aperture_mm": 60,
        "radius_mm": 74.435,
    },
)
CORE_FILES = ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def write_status(status: dict[str, Any]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_ROOT / "factorial_chain_status.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    lines = [
        "# 250 kHz Trajectory × Transducer Factorial Chain",
        "",
        f"- Status: `{status['status']}`",
        f"- Updated: `{status['updated_at_utc']}`",
        "",
    ]
    for cell in status["cells"]:
        lines.append(
            f"- {cell['name']}: `{cell['status']}`"
            + (
                f" (return code {cell['return_code']})"
                if cell.get("return_code") is not None
                else ""
            )
        )
    (OUTPUT_ROOT / "FACTORIAL_CHAIN_STATUS.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def validate_dry_run(cell: dict[str, Any], directory: Path) -> None:
    quality = load_json(directory / "quality_dry_run_summary.json")
    config = quality["config"]
    source = quality["source"]
    expected = {
        "frequency_hz": 250000.0,
        "source_pressure_pa": 1000000.0,
        "tone_burst_cycles": 2,
        "cfl": 0.2,
        "pml_size": 12,
        "preset": "quick",
        "quick_lateral_half_width_m": 0.017,
        "quick_post_target_margin_m": 0.008,
        "allow_entry_plan_resolution_mismatch": False,
    }
    drift = {
        field: {"expected": value, "observed": config.get(field)}
        for field, value in expected.items()
        if config.get(field) != value
    }
    counts = source.get("source_label_counts")
    if drift:
        raise RuntimeError(f"{cell['name']}: dry-run drift {drift}")
    if not isinstance(counts, dict) or set(counts) != {"0"}:
        raise RuntimeError(f"{cell['name']}: source labels are not background-only: {counts}")
    if any((directory / filename).exists() for filename in CORE_FILES):
        raise RuntimeError(f"{cell['name']}: core output collision")


def child_command(cell: dict[str, Any], directory: Path) -> list[str]:
    return [
        sys.executable,
        "simulate_kwave_3d_focus.py",
        "--preset", "quick",
        "--output-dir", str(directory.relative_to(ROOT)),
        "--model", MODEL,
        "--entry-plan", cell["entry"],
        "--frequency-hz", "250000",
        "--source-pressure-pa", "1000000",
        "--cycles", "2",
        "--sim-time-us", "100",
        "--pml-size", "12",
        "--cfl", "0.2",
        "--quick-lateral-mm", "17",
        "--quick-post-target-mm", "8",
        "--aperture-mm", str(cell["aperture_mm"]),
        "--radius-mm", str(cell["radius_mm"]),
        "--backend", "python",
        "--device", "cpu",
    ]


def monitored_command(cell: dict[str, Any], directory: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "monitor_kwave_process",
        "--output-dir", str(directory.relative_to(ROOT)),
        "--checkpoint-sec", "120",
        "--poll-sec", "5",
        "--stall-stop-min", "20",
        "--emergency-ceiling-min", "90",
        "--maximum-ceiling-min", "240",
        "--",
        *child_command(cell, directory),
    ]


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {
        "module": "freq250_trajectory_transducer_factorial_20260729",
        "status": "running",
        "started_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "cells": [
            {"name": cell["name"], "status": "pending", "return_code": None}
            for cell in CELLS
        ],
    }
    write_status(status)

    for index, cell in enumerate(CELLS):
        directory = OUTPUT_ROOT / cell["name"]
        validate_dry_run(cell, directory)
        entry = status["cells"][index]
        entry["status"] = "running"
        entry["started_at_utc"] = utc_now()
        status["updated_at_utc"] = utc_now()
        write_status(status)

        completed = subprocess.run(
            monitored_command(cell, directory),
            cwd=ROOT,
            check=False,
        )
        entry["return_code"] = completed.returncode
        entry["finished_at_utc"] = utc_now()
        monitor = load_json(directory / "monitor_status.json")
        entry["monitor_status"] = monitor.get("status")
        entry["core_outputs_complete"] = all(
            (directory / filename).is_file() for filename in CORE_FILES
        )
        entry["status"] = (
            "completed"
            if completed.returncode == 0
            and monitor.get("status") == "completed"
            and entry["core_outputs_complete"]
            else "failed"
        )
        status["updated_at_utc"] = utc_now()
        if entry["status"] != "completed":
            status["status"] = "failed"
            write_status(status)
            return 1
        write_status(status)

    status["status"] = "completed"
    status["finished_at_utc"] = utc_now()
    status["updated_at_utc"] = utc_now()
    write_status(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
