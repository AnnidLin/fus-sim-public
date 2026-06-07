"""Create a reviewable shortlist of public CT case download targets.

This script does not download data. It turns the public source catalog into a
small set of candidate next actions, with one or two concrete manual targets.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDNAMES = [
    "rank",
    "candidate_id",
    "source_id",
    "candidate_name",
    "format",
    "pipeline_status",
    "download_status",
    "size_risk",
    "license_access_note",
    "recommended_action",
    "why_this_candidate",
    "manual_download_target",
    "future_local_dir",
    "evidence_url",
    "notes",
]


def read_sources(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {source["source_id"]: source for source in payload.get("sources", [])}


def make_shortlist(sources: dict[str, dict], download_root: Path) -> list[dict]:
    tcia = sources.get("tcia_head_neck_dicom", {})
    deepmind = sources.get("deepmind_tcia_ct_scan_dataset", {})
    visible_human = sources.get("visible_human_head_ct", {})
    slicer = sources.get("slicer_sample_data", {})

    return [
        {
            "rank": 1,
            "candidate_id": "hn_cetuximab_0522c0027_series5577",
            "source_id": "tcia_head_neck_dicom",
            "candidate_name": "TCIA Head-Neck Cetuximab, patient 0522c0027, CT series 5577",
            "format": "DICOM",
            "pipeline_status": "ready_after_manual_single_series_download",
            "download_status": "manual_only",
            "size_risk": "medium_if_single_series_high_if_collection",
            "license_access_note": tcia.get("license_access_note", "Review TCIA collection terms before use."),
            "recommended_action": "Use as the first real public-case target if a single CT series can be selected in TCIA/NBIA.",
            "why_this_candidate": (
                "A public DICOM example page identifies this as near-isotropic head/neck CT, "
                "which is more suitable than a random large TCIA bulk collection."
            ),
            "manual_download_target": (
                "TCIA Head-Neck Cetuximab collection; patient ID 0522c0027; study date 2000-05-17; series 5577."
            ),
            "future_local_dir": str(download_root / "hn_cetuximab_0522c0027_series5577"),
            "evidence_url": "https://www.rbvi.ucsf.edu/chimerax/dicom/examples.html",
            "notes": "Do not bulk-download the full Head-Neck Cetuximab collection; select one CT series only.",
        },
        {
            "rank": 2,
            "candidate_id": "tcia_head_neck_pet_ct_single_series",
            "source_id": "tcia_head_neck_dicom",
            "candidate_name": "TCIA Head-Neck-PET-CT single CT series",
            "format": "DICOM",
            "pipeline_status": "ready_after_manual_single_series_download",
            "download_status": "manual_only",
            "size_risk": "high_if_bulk_download",
            "license_access_note": tcia.get("license_access_note", "Review TCIA collection terms before use."),
            "recommended_action": "Keep as fallback only after manually identifying a small CT-only series.",
            "why_this_candidate": "The format is compatible, but collection-level downloads are too large for the current workflow.",
            "manual_download_target": "Choose one CT-only subject/series in TCIA/NBIA, not the full collection.",
            "future_local_dir": str(download_root / "tcia_head_neck_pet_ct_single_series"),
            "evidence_url": tcia.get("url", "https://www.cancerimagingarchive.net/"),
            "notes": "Run inventory and QC immediately after any future single-series download.",
        },
        {
            "rank": 3,
            "candidate_id": "slicer_ct_chest_nrrd_format_smoke",
            "source_id": "slicer_sample_data",
            "candidate_name": "3D Slicer CT-chest NRRD sample",
            "format": "NRRD",
            "pipeline_status": "blocked_requires_nrrd_support",
            "download_status": "do_not_download_yet",
            "size_risk": slicer.get("expected_size_risk", "low"),
            "license_access_note": slicer.get("license_access_note", "Review Slicer sample terms before use."),
            "recommended_action": "Use later only to test NRRD reader support; not a skull/tFUS case.",
            "why_this_candidate": "Small and convenient for format plumbing, but anatomically irrelevant to transcranial focusing.",
            "manual_download_target": "3D Slicer SampleData CT-chest after NRRD support exists.",
            "future_local_dir": str(download_root / "slicer_ct_chest_nrrd_format_smoke"),
            "evidence_url": slicer.get("url", "https://www.slicer.org/wiki/SampleData"),
            "notes": "This should not be included in multi-case skull conclusions.",
        },
        {
            "rank": 4,
            "candidate_id": "deepmind_tcia_nrrd_subset",
            "source_id": "deepmind_tcia_ct_scan_dataset",
            "candidate_name": "Google DeepMind tcia-ct-scan-dataset subset",
            "format": "NRRD",
            "pipeline_status": "blocked_requires_nrrd_support",
            "download_status": "do_not_download_yet",
            "size_risk": deepmind.get("expected_size_risk", "medium_to_high"),
            "license_access_note": deepmind.get("license_access_note", "Review repository and upstream terms before use."),
            "recommended_action": "Defer until NRRD support and subset download rules are implemented.",
            "why_this_candidate": "Potentially useful segmentation data, but format and size risk are not aligned with the current ready path.",
            "manual_download_target": "Choose a documented small subset after adding NRRD support.",
            "future_local_dir": str(download_root / "deepmind_tcia_nrrd_subset"),
            "evidence_url": deepmind.get("url", "https://github.com/google-deepmind/tcia-ct-scan-dataset"),
            "notes": "Avoid Git LFS or bulk dataset downloads in this stage.",
        },
        {
            "rank": 5,
            "candidate_id": "visible_human_head_ct_review",
            "source_id": "visible_human_head_ct",
            "candidate_name": "Visible Human Project head CT format review",
            "format": "image_stack_or_archive",
            "pipeline_status": "blocked_requires_format_and_spacing_confirmation",
            "download_status": "manual_review_only",
            "size_risk": visible_human.get("expected_size_risk", "medium"),
            "license_access_note": visible_human.get("license_access_note", "Review public data terms before use."),
            "recommended_action": "Defer until file format, voxel spacing metadata, and conversion route are confirmed.",
            "why_this_candidate": "Head anatomy is relevant, but uncertain metadata makes it unsafe as the next pipeline case.",
            "manual_download_target": "Inspect file listing and metadata first; do not import directly.",
            "future_local_dir": str(download_root / "visible_human_head_ct_review"),
            "evidence_url": visible_human.get("url", ""),
            "notes": "May need conversion to NIfTI/DICOM with reliable spacing before QC.",
        },
    ]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Public CT Case Shortlist",
        "",
        "This shortlist is a review aid only. No files were downloaded.",
        "",
        "| Rank | Candidate | Format | Status | Recommended action |",
        "|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['rank']} | {row['candidate_name']} | {row['format']} | "
            f"{row['pipeline_status']} | {row['recommended_action']} |"
        )
    lines.extend(
        [
            "",
            "## Recommended First Target",
            "",
            (
                "Start with `hn_cetuximab_0522c0027_series5577` only if TCIA/NBIA can export "
                "that single CT series without pulling the full collection."
            ),
            "",
            "Guardrails:",
            "",
            "- Do not bulk-download full TCIA head/neck collections.",
            "- Store future data only under `data/raw_ct/public/<case_id>/`.",
            "- Run `inventory_ct_cases.py` and `validate_ct_case.py` immediately after any future download.",
            "- Keep NRRD candidates blocked until an NRRD reader/conversion step is implemented.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default="data/processed/public_ct_sources.json")
    parser.add_argument("--output-dir", default="outputs/public_ct_case_shortlist")
    parser.add_argument("--download-root", default="data/raw_ct/public")
    args = parser.parse_args()

    sources_path = Path(args.sources)
    output_dir = Path(args.output_dir)
    download_root = Path(args.download_root)

    if not sources_path.exists():
        raise FileNotFoundError(f"Missing source catalog: {sources_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rows = make_shortlist(read_sources(sources_path), download_root.resolve())

    write_csv(output_dir / "public_ct_case_shortlist.csv", rows)
    (output_dir / "public_ct_case_shortlist.json").write_text(
        json.dumps(
            {
                "description": "Reviewable public CT case shortlist. No downloads performed.",
                "no_download_performed": True,
                "download_root_policy": str(download_root.resolve()),
                "recommended_first_candidate": rows[0]["candidate_id"],
                "candidates": rows,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    write_markdown(output_dir / "public_ct_case_shortlist.md", rows)

    print(f"Wrote {len(rows)} public CT case shortlist entries to {output_dir}")


if __name__ == "__main__":
    main()
