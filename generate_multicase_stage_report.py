from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent


CASE_FIELDS = [
    "case_id",
    "format",
    "ct_role",
    "qc_status",
    "qc_warnings",
    "shape_xyz",
    "spacing_mm_xyz",
    "hu_or_intensity_range",
    "batch_status",
    "batch_output_dir",
    "quick_plan_status",
    "smoke_status",
    "smoke_target_window_peak_mpa",
    "refinement_plan_status",
    "refinement_status",
    "refinement_target_index_ijk",
    "refinement_entry_offset_mm",
    "refinement_target_window_peak_mpa",
    "improvement_vs_smoke_x",
    "stage_note",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def by_case(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = summary.get("cases", [])
    if not isinstance(cases, list):
        return {}
    return {str(case.get("case_id")): case for case in cases}


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def fmt(value: Any, digits: int = 3) -> str:
    if value is None or value == "":
        return "n/a"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def role_for_case(case_id: str, manifest_case: dict[str, Any]) -> str:
    if case_id == "synthetic_case":
        return "DICOM reader test; not a realistic acoustic case"
    if manifest_case.get("format") == "nifti":
        return "real CT/NIfTI case"
    return "local CT case"


def stage_note(case_id: str, smoke: dict[str, Any] | None, refinement: dict[str, Any] | None) -> str:
    if case_id == "synthetic_case":
        return "Kept to exercise DICOM import; skipped for real pressure interpretation."
    if refinement and refinement.get("run_status") == "kwave_ok":
        return "Full reusable quick pipeline closed: smoke was weak, refinement recovered tuned route."
    if smoke and smoke.get("run_status") == "kwave_ok":
        return "Smoke run completed; needs target/entry refinement."
    return "Not yet validated by pressure run."


def build_case_rows(
    manifest: dict[str, Any],
    batch: dict[str, Any],
    quick_plan: dict[str, Any],
    smoke: dict[str, Any],
    refinement_plan: dict[str, Any],
    refinement: dict[str, Any],
) -> list[dict[str, Any]]:
    manifest_cases = by_case(manifest)
    batch_cases = by_case(batch)
    quick_cases = by_case(quick_plan)
    smoke_cases = by_case(smoke)
    refinement_plan_cases = by_case(refinement_plan)
    refinement_cases = by_case(refinement)

    case_ids = sorted(
        set(manifest_cases)
        | set(batch_cases)
        | set(quick_cases)
        | set(smoke_cases)
        | set(refinement_plan_cases)
        | set(refinement_cases)
    )
    rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        manifest_case = manifest_cases.get(case_id, {})
        batch_case = batch_cases.get(case_id, {})
        quick_case = quick_cases.get(case_id, {})
        smoke_case = smoke_cases.get(case_id, {})
        refinement_plan_case = refinement_plan_cases.get(case_id, {})
        refinement_case = refinement_cases.get(case_id, {})
        rows.append(
            {
                "case_id": case_id,
                "format": manifest_case.get("format"),
                "ct_role": role_for_case(case_id, manifest_case),
                "qc_status": manifest_case.get("status"),
                "qc_warnings": manifest_case.get("warnings", []),
                "shape_xyz": manifest_case.get("shape_xyz"),
                "spacing_mm_xyz": manifest_case.get("spacing_mm_xyz"),
                "hu_or_intensity_range": manifest_case.get("hu_or_intensity_range"),
                "batch_status": batch_case.get("status"),
                "batch_output_dir": batch_case.get("output_dir"),
                "quick_plan_status": quick_case.get("status"),
                "smoke_status": smoke_case.get("run_status"),
                "smoke_target_window_peak_mpa": smoke_case.get("target_window_peak_mpa"),
                "refinement_plan_status": refinement_plan_case.get("status"),
                "refinement_status": refinement_case.get("run_status"),
                "refinement_target_index_ijk": refinement_case.get("target_index_ijk")
                or refinement_plan_case.get("recommended_target_index_ijk"),
                "refinement_entry_offset_mm": refinement_case.get("entry_offset_mm")
                or [
                    refinement_plan_case.get("recommended_entry_offset_y_mm"),
                    refinement_plan_case.get("recommended_entry_offset_z_mm"),
                ],
                "refinement_target_window_peak_mpa": refinement_case.get("target_window_peak_mpa"),
                "improvement_vs_smoke_x": refinement_case.get("improvement_vs_smoke_x"),
                "stage_note": stage_note(case_id, smoke_case, refinement_case),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in CASE_FIELDS})


def markdown_table(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Case | Role | QC | Batch | Smoke | Refinement | Key metric | Note |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        key_metric = "n/a"
        if row.get("refinement_target_window_peak_mpa") is not None:
            key_metric = (
                f"refined target-window {fmt(row.get('refinement_target_window_peak_mpa'))} MPa; "
                f"{fmt(row.get('improvement_vs_smoke_x'), 1)}x smoke"
            )
        elif row.get("smoke_target_window_peak_mpa") is not None:
            key_metric = f"smoke target-window {fmt(row.get('smoke_target_window_peak_mpa'))} MPa"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("case_id", "")),
                    str(row.get("ct_role", "")),
                    str(row.get("qc_status", "")),
                    str(row.get("batch_status", "")),
                    str(row.get("smoke_status", "")),
                    str(row.get("refinement_status") or row.get("refinement_plan_status") or ""),
                    key_metric,
                    str(row.get("stage_note", "")),
                ]
            )
            + " |"
        )
    return lines


def build_markdown(summary: dict[str, Any]) -> str:
    rows = summary["cases"]
    refined_079 = next((row for row in rows if row["case_id"] == "079"), {})
    lines: list[str] = []
    lines.append("# Multi-case Stage Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("- The reusable quick pipeline is now closed: CT inventory/QC -> batch acoustic model -> quick smoke -> target/entry refinement -> one-candidate validation.")
    lines.append("- The local workspace currently contains one real CT/NIfTI case, `079`; `synthetic_case` is only a DICOM reader test.")
    lines.append(
        f"- After refinement, `079` reaches `target_window_peak_mpa={fmt(refined_079.get('refinement_target_window_peak_mpa'))} MPa`, "
        f"about `{fmt(refined_079.get('improvement_vs_smoke_x'), 1)}x` the default smoke result."
    )
    lines.append("- This demonstrates reusable platform plumbing, not paper-level reproduction or a medical safety conclusion.")
    lines.append("")
    lines.append("## Case Table")
    lines.append("")
    lines.extend(markdown_table(rows))
    lines.append("")
    lines.append("## 079 Pipeline Review")
    lines.append("")
    lines.append("- Input: `data/raw_ct/079.nii`, a NIfTI CT case. QC warning: coarse z spacing.")
    lines.append("- Batch model: `outputs/ct_acoustic_models_batch/079_bone300_dx1/`; this does not overwrite the earlier best model.")
    lines.append("- Default smoke run: runnable, but weak at the default batch target, with target-window peak about `0.013 MPa`.")
    lines.append("- Refinement: automatically recovered `target_020=[93,121,63]`; validating the `(10,0)` entry candidate recovered the hand-tuned quick best, `2.254 MPa`.")
    lines.append("")
    lines.append("## synthetic_case Note")
    lines.append("")
    lines.append("- `synthetic_case` confirms that a DICOM folder can be read and converted by the batch model pipeline.")
    lines.append("- It is not a realistic skull case; the quick plan flags geometry/source warnings, so it is not interpreted as a real pressure/refinement case.")
    lines.append("")
    lines.append("## Current Limits")
    lines.append("")
    lines.append("- Only one real CT case is available locally, so generalization is not established.")
    lines.append("- CT segmentation still uses coarse HU thresholds; there is no anatomical brain-region segmentation, MRI registration, or verified hippocampus target.")
    lines.append("- Pressure results come from CPU-friendly quick cropped-domain runs, not paper-scale full-head grids.")
    lines.append("- Thermal safety trends use quick pressure fields and approximate Pennes parameters; they are not medical safety claims.")
    lines.append("")
    lines.append("## Recommended Next Steps")
    lines.append("")
    lines.append("- Add one more real CT case or a small public dataset, then repeat manifest/QC/batch/refinement.")
    lines.append("- Improve target realism and CT segmentation quality before expanding the grid or claiming paper-style replication.")
    lines.append("- For new cases, generate plans first and run only one validation candidate before any broader k-Wave scans.")
    lines.append("")
    lines.append("## Source Files")
    lines.append("")
    for key, value in summary["inputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a multi-case stage report from existing JSON/CSV summaries.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--batch-summary", type=Path, required=True)
    parser.add_argument("--quick-plan", type=Path, required=True)
    parser.add_argument("--smoke-summary", type=Path, required=True)
    parser.add_argument("--refinement-plan", type=Path, required=True)
    parser.add_argument("--refinement-summary", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "multicase_stage_report",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_json(args.manifest)
    batch = load_json(args.batch_summary)
    quick_plan = load_json(args.quick_plan)
    smoke = load_json(args.smoke_summary)
    refinement_plan = load_json(args.refinement_plan)
    refinement = load_json(args.refinement_summary)
    rows = build_case_rows(manifest, batch, quick_plan, smoke, refinement_plan, refinement)
    summary = {
        "description": "Multi-case tFUS quick-pipeline stage report.",
        "inputs": {
            "manifest": str(args.manifest),
            "batch_summary": str(args.batch_summary),
            "quick_plan": str(args.quick_plan),
            "smoke_summary": str(args.smoke_summary),
            "refinement_plan": str(args.refinement_plan),
            "refinement_summary": str(args.refinement_summary),
        },
        "case_count": len(rows),
        "real_case_count": sum(1 for row in rows if row.get("ct_role") == "real CT/NIfTI case"),
        "synthetic_or_test_count": sum(1 for row in rows if "test" in str(row.get("ct_role", "")).lower()),
        "kwave_smoke_ok_count": sum(1 for row in rows if row.get("smoke_status") == "kwave_ok"),
        "refinement_ok_count": sum(1 for row in rows if row.get("refinement_status") == "kwave_ok"),
        "cases": rows,
        "limitations": [
            "Only one real CT case is available locally.",
            "Segmentation uses coarse HU thresholds.",
            "Targets are geometric candidates, not verified anatomical targets.",
            "Pressure simulations are quick cropped-domain runs.",
            "The report is for internal platform review, not medical safety claims.",
        ],
    }
    write_csv(args.output_dir / "multicase_case_table.csv", rows)
    (args.output_dir / "multicase_stage_report_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "multicase_stage_report.md").write_text(build_markdown(summary), encoding="utf-8")
    print(f"Wrote {args.output_dir / 'multicase_stage_report.md'}")


if __name__ == "__main__":
    main()
