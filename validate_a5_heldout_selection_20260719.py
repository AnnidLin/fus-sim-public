from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from select_paper_gate_a_trajectories import angular_separation_deg


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "outputs" / "a5_heldout_d60_trajectory_selection_20260719" / "heldout_selection.json"


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    selected = report["selected"]
    beams = [np.asarray(item["beam_unit"], dtype=float) for item in selected]
    pairwise_ok = all(
        angular_separation_deg(beams[i], beams[j]) >= report["minimum_angular_separation_deg"]
        for i in range(len(beams)) for j in range(i + 1, len(beams))
    )
    checks = {
        "valid_status": report["status"] in {"heldout_selection_ready", "heldout_selection_blocked"},
        "a4_excluded": not ({item["candidate_id"] for item in selected} & set(report["a4_exclusion_ids"])),
        "source_safe": all(item["background_only"] and item["source_label_counts"] == {"0": item["source_points"]} for item in selected),
        "pairwise_separation": pairwise_ok,
        "pressure_not_authorized": report["pressure_execution_authorized"] is False,
        "status_matches_count": (len(selected) == 3) == (report["status"] == "heldout_selection_ready"),
        "entry_plans_exist": all((REPORT.parent / item["candidate_id"] / "entry_plan.json").exists() for item in selected),
    }
    failed = [name for name, value in checks.items() if not value]
    print(json.dumps({"status": "pass" if not failed else "fail", "selection_status": report["status"], "selected_count": len(selected), "checks": checks, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
