from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "outputs" / "a4_gate_feasibility_20260719" / "a4_gate_feasibility.json"


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    rows = report["trajectories"]
    checks = {
        "three_trajectories": len(rows) == 3,
        "two_infeasible": report["n_mathematically_infeasible"] == 2,
        "bound_recomputed": all(abs(row["mathematical_maximum_improvement_x"] - 1 / row["baseline_target_global"]) < 1e-12 for row in rows),
        "original_hold_preserved": report["original_a4_verdict"] == "hold" and report["original_a4_verdict_preserved"],
        "no_duplicate_pressure": report["a4b_pressure_execution"] == "not_run_evidence_redundant" and report["a4b_numerically_equivalent"],
        "claim_boundary": "no retroactive pass" in report["claim_boundary"],
    }
    failed = [key for key, value in checks.items() if not value]
    print(json.dumps({"status": "pass" if not failed else "fail", "checks": checks, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
