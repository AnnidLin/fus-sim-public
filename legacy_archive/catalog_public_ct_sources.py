from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent


FIELDS = [
    "source_id",
    "source_name",
    "url",
    "format",
    "license_access_note",
    "expected_size_risk",
    "recommended_use",
    "pipeline_readiness",
    "download_policy",
    "notes",
]


def public_sources() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "tcia_head_neck_dicom",
            "source_name": "TCIA head/neck CT DICOM collections",
            "url": "https://www.cancerimagingarchive.net/",
            "format": "DICOM",
            "license_access_note": "TCIA public collections have collection-specific citation/access notes; review the exact collection page before download.",
            "expected_size_risk": "high",
            "recommended_use": "Best candidate family for a second real clinical CT case once a small head/neck case is selected manually.",
            "pipeline_readiness": "partial_ready_dicom",
            "download_policy": "manual_collection_selection_first",
            "notes": "Current pipeline supports DICOM folders, but TCIA collections can be large and may require NBIA/Data Retriever workflow.",
        },
        {
            "source_id": "deepmind_tcia_ct_scan_dataset",
            "source_name": "Google DeepMind tcia-ct-scan-dataset",
            "url": "https://github.com/google-deepmind/tcia-ct-scan-dataset",
            "format": "NRRD",
            "license_access_note": "Review repository license plus upstream TCIA collection terms before use.",
            "expected_size_risk": "medium_to_high",
            "recommended_use": "Useful later because it includes head/neck CT volumes and segmentations, but it requires NRRD support first.",
            "pipeline_readiness": "requires_format_support",
            "download_policy": "do_not_download_until_nrrd_reader_exists",
            "notes": "Likely Git LFS / large-file workflow; not a first download target for this project state.",
        },
        {
            "source_id": "visible_human_head_ct",
            "source_name": "Visible Human Project head CT images",
            "url": "https://data.lhncbc.nlm.nih.gov/public/Visible-Human/Additional-Head-Images/index.html",
            "format": "image_stack_or_archive",
            "license_access_note": "Visible Human Project public data terms apply; confirm redistribution and research-use requirements before use.",
            "expected_size_risk": "medium",
            "recommended_use": "Potential research/test source for head CT imagery after format and spacing metadata are confirmed.",
            "pipeline_readiness": "requires_format_confirmation",
            "download_policy": "manual_inspection_first",
            "notes": "May need conversion into DICOM or NIfTI with reliable spacing before entering the acoustic pipeline.",
        },
        {
            "source_id": "slicer_sample_data",
            "source_name": "3D Slicer sample data",
            "url": "https://www.slicer.org/wiki/SampleData",
            "format": "NRRD",
            "license_access_note": "3D Slicer sample data is for software testing/training; verify individual sample terms if reused.",
            "expected_size_risk": "low",
            "recommended_use": "Good small-file test for adding NRRD reader support; not a realistic tFUS skull case.",
            "pipeline_readiness": "requires_format_support",
            "download_policy": "safe_for_future_small_format_test_only",
            "notes": "Current pipeline does not read NRRD, so this should not be treated as a ready CT case.",
        },
    ]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Catalog public CT data source candidates without downloading anything.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Output directory for public_ct_sources.csv/json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = public_sources()
    write_csv(args.output_dir / "public_ct_sources.csv", rows)
    summary = {
        "description": "Public CT source candidates for future fus-sim multi-case expansion. No data has been downloaded.",
        "download_root_policy": str(PROJECT_ROOT / "data" / "raw_ct" / "public"),
        "supported_now": ["NIfTI .nii/.nii.gz", "DICOM folder"],
        "not_supported_yet": ["NRRD", "image stacks without spacing metadata"],
        "source_count": len(rows),
        "sources": rows,
    }
    (args.output_dir / "public_ct_sources.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} public CT source candidates to {args.output_dir}")


if __name__ == "__main__":
    main()
