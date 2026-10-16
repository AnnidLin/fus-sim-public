from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "heldout_tr_report.json"


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    rows = report["trajectories"]
    checks = {
        "registered": report["registered_before_pressure"] is True,
        "three_frozen_trajectories": len(rows) == 3,
        "verdict_consistent": (report["n_pass"] >= report["study_min_pass"]) == (report["status"] == "confirmatory_pass"),
        "counts_consistent": report["n_pass"] == sum(row["verdict"] == "pass" for row in rows),
        "all_gates_present": all(len(row["checks"]) == 6 for row in rows),
        "no_thermal_claim": "thermal or clinical safety" in report["blocked_claims"],
    }
    failed = [name for name, passed in checks.items() if not passed]
    print(json.dumps({"status": "pass" if not failed else "fail", "checks": checks, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
