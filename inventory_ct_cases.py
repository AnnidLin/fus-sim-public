from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from validate_ct_case import case_id_from_path, folder_size_bytes, is_nifti_path, summarize_case


PROJECT_ROOT = Path(__file__).resolve().parent


CSV_FIELDS = [
    "case_id",
    "format",
    "status",
    "ct_path",
    "file_size_bytes",
    "shape_xyz",
    "spacing_mm_xyz",
    "slice_count",
    "hu_min",
    "hu_max",
    "likely_ct_hu",
    "has_bone_intensity_range_gte_300hu",
    "bone_voxel_fraction_gte_300hu",
    "warnings",
    "errors",
]


def discover_cases(input_dir: Path) -> list[tuple[str, Path]]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input CT folder not found: {input_dir}")
    cases: list[tuple[str, Path]] = []
    for child in sorted(input_dir.iterdir(), key=lambda item: item.name.lower()):
        if child.is_file() and is_nifti_path(child):
            cases.append((case_id_from_path(child), child))
        elif child.is_dir():
            cases.append((case_id_from_path(child), child))
    return cases


def csv_row(summary: dict[str, Any]) -> dict[str, Any]:
    intensity_range = summary.get("hu_or_intensity_range") or [None, None]
    return {
        "case_id": summary.get("case_id"),
        "format": summary.get("format"),
        "status": summary.get("status"),
        "ct_path": summary.get("ct_path"),
        "file_size_bytes": summary.get("file_size_bytes", 0),
        "shape_xyz": format_list(summary.get("shape_xyz")),
        "spacing_mm_xyz": format_list(summary.get("spacing_mm_xyz")),
        "slice_count": summary.get("slice_count"),
        "hu_min": intensity_range[0],
        "hu_max": intensity_range[1],
        "likely_ct_hu": summary.get("likely_ct_hu"),
        "has_bone_intensity_range_gte_300hu": summary.get("has_bone_intensity_range_gte_300hu"),
        "bone_voxel_fraction_gte_300hu": summary.get("bone_voxel_fraction_gte_300hu"),
        "warnings": ";".join(summary.get("warnings", [])),
        "errors": ";".join(summary.get("errors", [])),
    }


def format_list(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "x".join(str(item) for item in value)
    return str(value)


def write_manifest(summaries: list[dict[str, Any]], output_dir: Path, input_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "ct_case_manifest.csv"
    json_path = output_dir / "ct_case_manifest.json"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for summary in summaries:
            writer.writerow(csv_row(summary))

    manifest = {
        "description": "Local CT case inventory for the fus-sim quick pipeline.",
        "input_dir": str(input_dir),
        "case_count": len(summaries),
        "ok_count": sum(1 for item in summaries if item.get("status") == "ok"),
        "warning_count": sum(1 for item in summaries if item.get("status") == "warning"),
        "error_count": sum(1 for item in summaries if item.get("status") == "error"),
        "cases": summaries,
    }
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory local CT NIfTI files and DICOM folders.")
    parser.add_argument("--input-dir", default=str(PROJECT_ROOT / "data" / "raw_ct"), help="Folder containing CT cases.")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "processed"),
        help="Output folder for ct_case_manifest.csv/json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    cases = discover_cases(input_dir)
    summaries: list[dict[str, Any]] = []
    for case_id, path in cases:
        summary = summarize_case(case_id, path)
        if "file_size_bytes" not in summary:
            summary["file_size_bytes"] = folder_size_bytes(path)
        summaries.append(summary)
        status = summary.get("status")
        if status == "error":
            print(f"ERROR: {case_id}: {summary.get('errors')}")
        elif status == "warning":
            print(f"WARNING: {case_id}: {summary.get('warnings')}")
        else:
            print(f"OK: {case_id}")
    write_manifest(summaries, Path(args.output_dir), input_dir)
    print(f"Wrote {len(summaries)} case(s) to {Path(args.output_dir) / 'ct_case_manifest.csv'}")


if __name__ == "__main__":
    main()
