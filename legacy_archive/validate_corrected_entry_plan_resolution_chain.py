from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


import argparse

PROJECT_ROOT = Path(__file__).resolve().parent

# Parse command line arguments
parser = argparse.ArgumentParser(description="Validate corrected entry-plan resolution chain.")
parser.add_argument("--dx", choices=["0.75", "0.5"], default="0.75", help="Grid resolution in mm.")
args = parser.parse_args()

dx_str = "dx0p75" if args.dx == "0.75" else "dx0p5"
SUMMARY_PATH = PROJECT_ROOT / f"outputs/corrected_entry_plan_resolution_chain/079_candidate_006_{dx_str}/corrected_entry_plan_resolution_chain.json"
DRY_RUN_PATH = PROJECT_ROOT / f"outputs/corrected_entry_plan_resolution_chain/079_candidate_006_{dx_str}/dry_run_quality/quality_dry_run_summary.json"
OUT_JSON = PROJECT_ROOT / f"outputs/corrected_entry_plan_resolution_chain/079_candidate_006_{dx_str}/corrected_entry_plan_resolution_chain_validation.json"
OUT_MD = PROJECT_ROOT / f"outputs/corrected_entry_plan_resolution_chain/079_candidate_006_{dx_str}/corrected_entry_plan_resolution_chain_validation.md"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8-sig"))
    dry_run = json.loads(DRY_RUN_PATH.read_text(encoding="utf-8-sig")) if DRY_RUN_PATH.exists() else None
    checks: list[dict[str, Any]] = []
    selected = next(item for item in summary["candidates"] if item["candidate_id"] == summary["selected_candidate_id"])

    add(checks, "summary.exists", SUMMARY_PATH.exists(), str(SUMMARY_PATH))
    add(checks, "selected.scaled_old_target", summary["selected_candidate_id"] == "scaled_old_target", summary["selected_candidate_id"])
    add(checks, "selected.passed", bool(selected["passed"]), str(selected["checks"]))
    add(checks, "selected.resolution_matches", bool(selected["checks"]["resolution_matches"]), str(selected["checks"]))
    add(checks, "selected.source_mask_background_only", bool(selected["checks"]["source_mask_background_only"]), str(selected["diagnostics"].get("source_label_counts")))
    add(checks, "selected.crop_contains_skull", bool(selected["checks"]["crop_contains_skull_material"]), str(selected["diagnostics"]["material_ranges"]))
    add(checks, "pressure.blocked", summary.get("pressure_execution_allowed") is False, str(summary.get("pressure_execution_allowed")))
    add(checks, "dry_run.exists", dry_run is not None, str(DRY_RUN_PATH))
    if dry_run is not None:
        add(checks, "dry_run.quality_only", dry_run.get("dry_run_quality_only") is True, str(dry_run.get("dry_run_quality_only")))
        add(checks, "dry_run.no_pressure", not (DRY_RUN_PATH.parent / "pressure_max_mpa.npz").exists(), str(DRY_RUN_PATH.parent))
        pml_size = dry_run.get("pml_size", dry_run.get("simulation_quality", {}).get("pml_size"))
        cfl = dry_run.get("cfl", dry_run.get("simulation_quality", {}).get("cfl"))
        add(checks, "dry_run.pml12", pml_size == 12, str(pml_size))
        add(checks, "dry_run.cfl02", abs(float(cfl) - 0.2) < 1e-9, str(cfl))
        add(
            checks,
            "dry_run.resolution_gate_not_bypassed",
            dry_run.get("config", {}).get("allow_entry_plan_resolution_mismatch") is False,
            str(dry_run.get("config", {}).get("allow_entry_plan_resolution_mismatch")),
        )

    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chain_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    # Only rewrite if the validation outcome changed, to keep reproducibility hashes stable.
    previous_checks: list[dict[str, Any]] = []
    if OUT_JSON.exists():
        try:
            previous_checks = json.loads(OUT_JSON.read_text(encoding="utf-8-sig")).get("checks", [])
        except Exception:
            previous_checks = []
    outcome_changed = previous_checks != checks
    if outcome_changed:
        OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        OUT_MD.write_text(
            "# Corrected Entry-Plan Resolution Chain Validation\n\n"
            f"- chain valid: `{result['chain_valid']}`\n"
            f"- failed check count: `{result['failed_check_count']}`\n",
            encoding="utf-8",
        )
    print(json.dumps({"chain_valid": result["chain_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
