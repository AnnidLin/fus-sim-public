from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "outputs" / "tr_generalization_audit_20260719" / "generalization_audit.json"


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    checks = {
        "six_trajectories": len(report["rows"]) == 6,
        "development_two_of_three": abs(report["development_pass_rate"] - 2 / 3) < 1e-12,
        "heldout_one_of_three": abs(report["heldout_pass_rate"] - 1 / 3) < 1e-12,
        "pooled_three_of_six": report["pooled_pass_rate"] == 0.5,
        "original_a4_preserved": report["original_a4_verdict_preserved"] == "hold",
        "expansion_blocked": "Do not unlock" in report["decision"],
        "figure_exists": (REPORT.parent / "tr_generalization_audit.png").stat().st_size > 50_000,
    }
    failed = [name for name, value in checks.items() if not value]
    print(json.dumps({"status": "pass" if not failed else "fail", "checks": checks, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
