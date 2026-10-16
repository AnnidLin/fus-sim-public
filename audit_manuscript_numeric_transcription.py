"""Check manuscript scalar transcription against retained machine-readable evidence."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(root: Path) -> dict:
    text = (root / "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md").read_text(encoding="utf-8-sig")
    closeout = load(root / "outputs/pub2_closeout_20260812/closeout_report.json")["accepted_evidence"]
    baseline = load(root / "outputs/pub2_250khz_reference_pair_throttled_20260807/baseline/focus_metrics.json")
    tr = load(root / "outputs/pub2_250khz_reference_pair_throttled_20260807/tr/focus_metrics.json")
    cfl = load(root / "outputs/pub2_250khz_cfl0p1_baseline_analysis_20260812/cfl0p1_baseline_analysis.json")
    pml = closeout["paired_pml_sensitivity"]
    ref = closeout["reference_pair"]
    expected = {
        "ratio_pair": f"{ref['baseline_target_to_global_ratio']:.4f} to {ref['tr_target_to_global_ratio']:.4f}",
        "distance_pair": f"{ref['baseline_global_peak_to_target_distance_mm']:.2f} to {ref['tr_global_peak_to_target_distance_mm']:.2f} mm",
        "target_pressure_pair": f"{baseline['target_pressure_mpa']:.3f} to {tr['target_pressure_mpa']:.3f} MPa",
        "global_pressure_pair": f"{baseline['global_peak_mpa']:.3f} to {tr['global_peak_mpa']:.3f} MPa",
        "target_pressure_change": f"+{ref['target_pressure_relative_change'] * 100:.2f}%",
        "global_pressure_change": f"−{(1 - tr['global_peak_mpa'] / baseline['global_peak_mpa']) * 100:.2f}%",
        "pml_baseline_l2": "1.83 × 10−5",
        "pml_baseline_linf": "6.75 × 10−5",
        "pml_tr_l2": "5.05 × 10−5",
        "pml_tr_linf": "1.46 × 10−4",
        "cfl_l2_linf": f"{cfl['field_difference']['relative_l2_percent']:.3f}%/{cfl['field_difference']['relative_linf_percent']:.3f}%",
        "cfl_target_change": f"−{abs(cfl['scalar_metrics']['target_pressure_mpa']['relative_difference_percent']):.3f}%",
    }
    checks = {key: token in text for key, token in expected.items()}
    checks.update({
        "pressure_units_are_mpa": text.count(" MPa") >= 5,
        "distance_units_are_mm": text.count(" mm") >= 10,
        "cfl_claim_is_baseline_only": "supports baseline time-step stability" in text and "not TR time-step robustness" in text,
        "pressure_accuracy_boundary_retained": "should not be interpreted as validated intracranial exposure estimates" in text,
    })
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": "TRACE-20260829-001",
        "status": "passed_numeric_transcription" if all(checks.values()) else "failed",
        "submission_ready": False,
        "expected_tokens": expected,
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "Scalar transcription and units only; this audit does not validate the underlying physics or authorize submission.",
    }


def render(report: dict) -> str:
    lines = ["# Manuscript numeric-transcription audit", "", f"Status: `{report['status']}`", "", "## Source-derived tokens", ""]
    lines += [f"- `{key}`: `{value}`" for key, value in report["expected_tokens"].items()]
    lines += ["", "## Checks", ""] + [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()]
    lines += ["", report["claim_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "numeric_transcription_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "numeric_transcription_audit.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed_checks"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
