from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_d60_grid_convergence_report import build_report, write_report

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DX075 = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run"
DEFAULT_DX05 = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p5_pointwave_20260716/run"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_grid_convergence_corrected_20260716"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dx075-dir", type=Path, default=DEFAULT_DX075)
    parser.add_argument("--dx05-dir", type=Path, default=DEFAULT_DX05)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = build_report(args.dx075_dir, args.dx05_dir)
    write_report(report, args.output_dir)
    print(json.dumps({"status": report["status"], "output_dir": str(args.output_dir.relative_to(PROJECT_ROOT))}))


if __name__ == "__main__":
    main()
