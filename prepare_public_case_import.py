"""Prepare and gate a manually downloaded public CT case.

This script never downloads files. It checks whether the expected public-case
folder exists, optionally runs lightweight CT QC, and writes the next commands
needed to bring the case into the existing manifest/batch pipeline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_ct_case import summarize_case


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CASE_ID = "hn_cetuximab_0522c0027_series5577"


def load_candidate(shortlist_path: Path, case_id: str) -> dict[str, Any]:
    payload = json.loads(shortlist_path.read_text(encoding="utf-8"))
    for candidate in payload.get("candidates", []):
        if candidate.get("candidate_id") == case_id:
            return candidate
    raise ValueError(f"Candidate {case_id!r} not found in {shortlist_path}")


def count_files(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"file_count": 0, "dcm_like_count": 0}
    files = [item for item in path.rglob("*") if item.is_file()]
    dcm_like = [
        item
        for item in files
        if item.suffix.lower() in {".dcm", ".dicom", ""} or item.name.lower().endswith(".ima")
    ]
    return {"file_count": len(files), "dcm_like_count": len(dcm_like)}


def build_commands(case_id: str, case_dir: Path) -> dict[str, str]:
    python_exe = r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe"
    return {
        "inventory_public_cases": (
            f"{python_exe} inventory_ct_cases.py --input-dir data\\raw_ct\\public "
            f"--output-dir data\\processed\\public_import"
        ),
        "validate_this_case": (
            f"{python_exe} validate_ct_case.py --case-id {case_id} --ct-path {case_dir} "
            f"--output-dir outputs\\ct_case_qc\\{case_id}"
        ),
        "batch_build_after_manifest_update": (
            f"{python_exe} batch_build_ct_models.py "
            f"--manifest data\\processed\\public_import\\ct_case_manifest.json "
            f"--output-root outputs\\ct_acoustic_models_batch --run"
        ),
        "prepare_quick_pressure_after_build": (
            f"{python_exe} prepare_case_quick_pressure.py "
            f"--batch-summary outputs\\ct_acoustic_models_batch\\batch_summary.json "
            f"--output-dir outputs\\case_quick_pressure_plan"
        ),
    }


def status_from_qc(case_dir: Path, qc: dict[str, Any] | None, counts: dict[str, int]) -> str:
    if not case_dir.exists():
        return "pending_manual_download"
    if not case_dir.is_dir():
        return "error_expected_dicom_folder"
    if counts["file_count"] == 0:
        return "pending_empty_folder"
    if qc is None:
        return "qc_not_run"
    if qc.get("status") == "error":
        return "qc_error"
    if qc.get("format") != "dicom_folder":
        return "warning_unexpected_format"
    if qc.get("likely_ct_hu") and qc.get("has_bone_intensity_range_gte_300hu"):
        return "ready_for_manifest_qc_batch"
    return "warning_needs_manual_review"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    candidate = summary["candidate"]
    qc = summary.get("qc_summary") or {}
    commands = summary["recommended_commands"]
    lines = [
        "# Public Case Import Gate",
        "",
        f"- Case ID: `{summary['case_id']}`",
        f"- Status: `{summary['status']}`",
        f"- Expected local folder: `{summary['case_dir']}`",
        f"- Candidate: {candidate.get('candidate_name')}",
        f"- Manual target: {candidate.get('manual_download_target')}",
        f"- Evidence URL: {candidate.get('evidence_url')}",
        "",
        "## Checks",
        "",
        f"- Folder exists: `{summary['folder_exists']}`",
        f"- File count: `{summary['file_count']}`",
        f"- DICOM-like file count: `{summary['dcm_like_count']}`",
    ]
    if qc:
        lines.extend(
            [
                f"- QC status: `{qc.get('status')}`",
                f"- Format: `{qc.get('format')}`",
                f"- Shape xyz: `{qc.get('shape_xyz')}`",
                f"- Spacing mm xyz: `{qc.get('spacing_mm_xyz')}`",
                f"- HU/intensity range: `{qc.get('hu_or_intensity_range')}`",
                f"- Likely CT HU: `{qc.get('likely_ct_hu')}`",
                f"- Bone range detected: `{qc.get('has_bone_intensity_range_gte_300hu')}`",
            ]
        )
        if qc.get("warnings"):
            lines.append(f"- Warnings: `{qc.get('warnings')}`")
        if qc.get("errors"):
            lines.append(f"- Errors: `{qc.get('errors')}`")
    lines.extend(
        [
            "",
            "## Next Commands",
            "",
            "Run these only after manually placing the single selected CT series in the expected folder.",
            "",
        ]
    )
    for name, command in commands.items():
        lines.extend([f"### {name}", "", "```powershell", command, "```", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", default=DEFAULT_CASE_ID)
    parser.add_argument("--shortlist", default="outputs/public_ct_case_shortlist/public_ct_case_shortlist.json")
    parser.add_argument(
        "--case-dir",
        default=None,
        help="Expected manually downloaded DICOM folder. Defaults to data/raw_ct/public/<case-id>.",
    )
    parser.add_argument("--output-dir", default="outputs/public_case_import")
    args = parser.parse_args()

    shortlist_path = Path(args.shortlist)
    case_dir = Path(args.case_dir) if args.case_dir else Path("data") / "raw_ct" / "public" / args.case_id
    output_dir = Path(args.output_dir) / args.case_id
    output_dir.mkdir(parents=True, exist_ok=True)

    candidate = load_candidate(shortlist_path, args.case_id)
    counts = count_files(case_dir)
    qc_summary: dict[str, Any] | None = None
    if case_dir.exists() and case_dir.is_dir() and counts["file_count"] > 0:
        qc_summary = summarize_case(args.case_id, case_dir)

    summary = {
        "case_id": args.case_id,
        "status": status_from_qc(case_dir, qc_summary, counts),
        "case_dir": str(case_dir.resolve()),
        "folder_exists": case_dir.exists(),
        "folder_is_dir": case_dir.is_dir() if case_dir.exists() else False,
        "file_count": counts["file_count"],
        "dcm_like_count": counts["dcm_like_count"],
        "candidate": candidate,
        "qc_summary": qc_summary,
        "recommended_commands": build_commands(args.case_id, case_dir),
        "no_download_performed": True,
        "raw_data_written_by_this_script": False,
    }

    (output_dir / "import_status.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_markdown(output_dir / "import_status.md", summary)
    (output_dir / "recommended_commands.ps1").write_text(
        "\n".join(summary["recommended_commands"].values()) + "\n",
        encoding="utf-8",
    )

    print(f"{summary['status']}: wrote public case import gate to {output_dir}")


if __name__ == "__main__":
    main()
