"""Validate the complete PUB.2 PML16 baseline sensitivity package."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "outputs" / "pub2_250khz_pml16_baseline_20260810"
ANALYSIS = ROOT / "outputs" / "pub2_250khz_pml16_baseline_analysis_20260810" / "pml16_baseline_analysis.json"
FEEDBACK = ROOT / "outputs" / "evidence_briefs" / "pub2_250khz_ct_numerical_sensitivity_20260807" / "pml16_baseline_gap_feedback.json"
OUTPUT = ROOT / "outputs" / "pub2_250khz_pml16_baseline_validation_20260810"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def numeric_values(rows: list[dict], key: str) -> list[float]:
    """Return finite numeric device samples, excluding the sampler warm-up null."""
    values = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)) and np.isfinite(value):
            values.append(float(value))
    if not values:
        raise ValueError(f"No numeric device samples for {key}")
    return values


def main() -> int:
    stage = load(RUN / "stage_result.json")
    execution = load(RUN / "execution_status.json")
    monitor = load(RUN / "monitor_status.json")
    analysis = load(ANALYSIS)
    feedback = load(FEEDBACK)
    with np.load(RUN / "pressure_max_mpa.npz", allow_pickle=False) as archive:
        field = np.asarray(archive["pressure_max_mpa"])
        field_ok = bool(field.shape == (137, 98, 101) and np.isfinite(field).all() and np.max(field) > 0)
    rows = [json.loads(line) for line in (RUN / "device_history.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    max_cores = max(numeric_values(rows, "equivalent_cores"))
    max_ws = max(numeric_values(rows, "working_set_gib"))
    min_free = min(numeric_values(rows, "system_free_memory_gib"))
    checks = {
        "execution_completed": execution.get("status") == "completed",
        "stage_completed_and_outputs_passed": stage.get("status") == "completed" and stage.get("output_validation", {}).get("status") == "passed",
        "monitor_completed": monitor.get("status") == "completed" and monitor.get("return_code") == 0,
        "pressure_field_finite_nonzero_expected_shape": field_ok,
        "summary_valid": load(RUN / "summary.json").get("config", {}).get("pml_size") == 16,
        "focus_metrics_valid": isinstance(load(RUN / "focus_metrics.json").get("global_peak_mpa"), (int, float)),
        "analysis_passed": analysis.get("status") == "passed" and analysis.get("decision", {}).get("formal_convergence_established") is False,
        "feedback_completed": str(feedback.get("status", "")).startswith("completed"),
        "cpu_gate": max_cores <= 6.5,
        "working_set_gate": max_ws <= 16.0,
        "free_memory_gate": min_free >= 4.0,
        "no_additional_cells_authorized": analysis.get("decision", {}).get("automatic_additional_cells_authorized") is False,
    }
    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "device_extrema": {"max_equivalent_cores": max_cores, "max_working_set_gib": max_ws, "min_system_free_memory_gib": min_free, "samples": len(rows)},
        "claim_boundary": "Package-integrity validation for one PML16 baseline cell; not physical validation, convergence, efficacy or safety evidence.",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "package_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "package_validation.md").write_text(
        "# PUB.2 PML16 baseline package validation\n\n"
        f"- Status: **{report['status']}**\n"
        f"- Checks passed: {sum(checks.values())}/{len(checks)}\n"
        f"- Device extrema: {report['device_extrema']}\n\n"
        f"{report['claim_boundary']}\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "json": str(OUTPUT / "package_validation.json")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
