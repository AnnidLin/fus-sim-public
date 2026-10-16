from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "outputs" / "a5_hamming_hotspot_report_20260720" / "hamming_hotspot_report.json"


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    checks = {
        "negative_status": report["status"] == "negative_pilot_hamming_worsened_hotspot_dominance",
        "control_reproduced": abs(report["control"]["target_global"] - 0.915193661148272) < 1e-9,
        "hamming_worse_target_global": report["hamming"]["target_global"] < report["control"]["target_global"],
        "hamming_worse_skull_focus": report["hamming"]["skull_focus"] > report["control"]["skull_focus"],
        "remote_skull_persists": report["hamming"]["global_material"] == "skull" and report["hamming"]["peak_target_mm"] > 50.0,
        "a5_hold_preserved": report["a5_original_verdict_preserved"] == "confirmatory_hold",
        "no_scan": report["followup_window_or_parameter_scan_authorized"] is False,
        "figure_exists": (REPORT.parent / "hamming_hotspot_comparison.png").stat().st_size > 30_000,
    }
    failed = [name for name, passed in checks.items() if not passed]
    print(json.dumps({"status": "pass" if not failed else "fail", "checks": checks, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
