#!/usr/bin/env python3
"""Audit the extracted ITRUSST k-Wave BM1/BM3/BM4 reference subset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from analyze_itrusst_benchmark import sha256_file


EXPECTED_CASES = {
    1: {"p_amp_shape": [141, 241], "source_x_offset": 41.0},
    3: {"p_amp_shape": [141, 241], "source_x_offset": 41.0},
    4: {"p_amp_shape": [141, 241], "source_x_offset": 81.0},
}


def _value(handle: h5py.File, path: str) -> float | list[float] | None:
    if path not in handle:
        return None
    values = np.asarray(handle[path], dtype=np.float64).ravel()
    if values.size == 1:
        return float(values[0])
    return [float(item) for item in values]


def audit_reference(path: Path, benchmark: int) -> dict[str, Any]:
    expected = EXPECTED_CASES[benchmark]
    with h5py.File(path, "r") as handle:
        p_amp = np.asarray(handle["p_amp"])
        p_phase = np.asarray(handle["p_phase"])
        settings = {
            "source_f0_hz": _value(handle, "general_settings/source_f0"),
            "source_magnitude_pa": _value(handle, "general_settings/source_mag"),
            "bowl_diameter_m": _value(handle, "general_settings/bowl_diameter"),
            "bowl_radius_of_curvature_m": _value(handle, "general_settings/bowl_roc"),
            "simulation_grid_size": _value(handle, "simulation_settings/grid_size"),
            "simulation_grid_spacing_m": _value(
                handle, "simulation_settings/grid_spacing"
            ),
            "pml_size": _value(handle, "simulation_settings/pml_size"),
            "ppw": _value(handle, "simulation_settings/ppw"),
            "ppp": _value(handle, "simulation_settings/ppp"),
            "cfl": _value(handle, "simulation_settings/cfl"),
            "nt": _value(handle, "simulation_settings/Nt"),
            "dt_s": _value(handle, "simulation_settings/dt"),
            "t_end_s": _value(handle, "simulation_settings/t_end"),
            "source_x_offset": _value(
                handle, "simulation_settings/source_x_offset"
            ),
        }
    checks = {
        "p_amp_shape_141x241": list(p_amp.shape) == expected["p_amp_shape"],
        "p_phase_shape_matches": p_phase.shape == p_amp.shape,
        "p_amp_finite_nonnegative": bool(
            np.all(np.isfinite(p_amp)) and np.all(p_amp >= 0)
        ),
        "source_frequency_500khz": settings["source_f0_hz"] == 500000.0,
        "source_magnitude_60kpa": settings["source_magnitude_pa"] == 60000.0,
        "bowl_diameter_64mm": settings["bowl_diameter_m"] == 0.064,
        "bowl_radius_64mm": settings["bowl_radius_of_curvature_m"] == 0.064,
        "source_x_offset_matches_case": (
            settings["source_x_offset"] == expected["source_x_offset"]
        ),
    }
    return {
        "benchmark": f"BM{benchmark}",
        "source": 1,
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
        "p_amp_shape_h5py": list(p_amp.shape),
        "p_amp_peak_pa": float(np.max(p_amp)),
        "settings": settings,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    input_dir = Path(args.input_dir).resolve()
    cases = []
    for benchmark in (1, 3, 4):
        path = input_dir / f"PH1-BM{benchmark}-SC1_KWAVE.mat"
        if not path.is_file():
            raise FileNotFoundError(path)
        cases.append(audit_reference(path, benchmark))
    report = {
        "schema_version": "1.0",
        "status": "passed" if all(case["passed"] for case in cases) else "failed",
        "claim_level": "official_reference_subset_integrity_and_metadata_only",
        "case_count": len(cases),
        "cases": cases,
        "important_distinction": (
            "The 0.5 mm, 141x241 submitted comparison maps are not the native "
            "k-Wave simulation grids. Native settings vary by benchmark and "
            "must not be replaced by a single assumed PPW/CFL."
        ),
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "output": str(output)}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

