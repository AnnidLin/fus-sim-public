"""Validate the matched PML16 TR execution, analysis and device evidence."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "outputs" / "pub2_250khz_pml16_tr_20260811"
TR = RUN / "tr"
ANALYSIS = ROOT / "outputs" / "pub2_250khz_pml16_tr_analysis_20260812" / "paired_pml_analysis.json"
FEEDBACK = ROOT / "outputs" / "evidence_briefs" / "pub2_250khz_ct_numerical_sensitivity_20260807" / "pml16_tr_gap_feedback.json"
OUTPUT = ROOT / "outputs" / "pub2_250khz_pml16_tr_validation_20260812"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def values(path: Path, key: str) -> list[float]:
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line).get(key)
            if isinstance(value, (int, float)) and np.isfinite(value):
                result.append(float(value))
    if not result:
        raise ValueError(f"No finite {key} samples in {path}")
    return result


def main() -> int:
    chain, analysis, feedback = load(RUN / "chain_status.json"), load(ANALYSIS), load(FEEDBACK)
    stage_results = {item.get("stage_id"): item for item in chain.get("results", [])}
    histories = [RUN / "tr_calibrate_device_history.jsonl", RUN / "tr_refocus_device_history.jsonl"]
    max_cores = max(max(values(path, "equivalent_cores")) for path in histories)
    max_ws = max(max(values(path, "working_set_gib")) for path in histories)
    min_free = min(min(values(path, "system_free_memory_gib")) for path in histories)
    with np.load(TR / "pressure_max_mpa.npz", allow_pickle=False) as archive:
        field = np.asarray(archive["pressure_max_mpa"])
        field_ok = bool(field.shape == (137, 98, 101) and np.isfinite(field).all() and np.max(field) > 0)
    with np.load(TR / "element_signals.npz", allow_pickle=False) as archive:
        signals = np.asarray(archive["signals"])
        signals_ok = bool(signals.size > 0 and np.isfinite(signals).all() and np.any(np.abs(signals) > 0))
    checks = {
        "chain_completed": chain.get("status") == "completed" and chain.get("automatic_rerun") is False,
        "calibration_valid": stage_results.get("tr_calibrate", {}).get("output_validation", {}).get("status") == "passed",
        "refocus_valid": stage_results.get("tr_refocus", {}).get("output_validation", {}).get("status") == "passed",
        "pressure_field_finite_nonzero_expected_shape": field_ok,
        "calibration_signals_finite_nonzero": signals_ok,
        "summary_pml16_low_memory": load(TR / "summary.json").get("config", {}).get("pml_size") == 16 and load(TR / "summary.json").get("config", {}).get("record_target_waveform") is False,
        "analysis_passed_with_claim_boundary": analysis.get("status") == "passed" and analysis.get("decision", {}).get("formal_convergence_established") is False,
        "feedback_completed": str(feedback.get("status", "")).startswith("completed"),
        "cpu_gate": max_cores <= 6.5,
        "working_set_gate": max_ws <= 16.0,
        "free_memory_gate": min_free >= 4.0,
    }
    report = {"schema_version": "1.0", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "status": "passed" if all(checks.values()) else "failed", "checks": checks, "device_extrema": {"max_equivalent_cores": max_cores, "max_working_set_gib": max_ws, "min_system_free_memory_gib": min_free}, "claim_boundary": "Package-integrity validation for one paired PML sensitivity experiment; not formal convergence, efficacy or safety evidence."}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "package_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "package_validation.md").write_text(f"# PUB.2 PML16 TR package validation\n\n- Status: **{report['status']}**\n- Checks passed: {sum(checks.values())}/{len(checks)}\n- Device extrema: `{report['device_extrema']}`\n\n{report['claim_boundary']}\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "json": str(OUTPUT / "package_validation.json")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
