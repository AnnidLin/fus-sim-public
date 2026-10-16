"""Review a Gen3/GC public CT file manifest without downloading data.

The manifest CSV is a navigation artifact, not CT image data. This script
summarizes the selected files, checks whether they look like a usable CT DICOM
zip target, and writes Chinese review notes plus local-only next steps.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


EXPECTED_CASE_ID = "hn_cetuximab_0522c0027_series5577"
EXPECTED_PARTICIPANT = "0522c0027"
EXPECTED_STUDY = "Head-Neck Cetuximab"
LOCAL_DESTINATION = Path("data/raw_ct/public") / EXPECTED_CASE_ID


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def review_rows(rows: list[dict[str, str]], manifest_path: Path) -> dict[str, Any]:
    ct_rows = [
        row
        for row in rows
        if row.get("File Type", "").upper() == "DICOM" and row.get("Image Modality", "").upper() == "CT"
    ]
    participant_ids = sorted({row.get("Participant ID", "") for row in rows if row.get("Participant ID", "")})
    study_names = sorted({row.get("Study Name", "") for row in rows if row.get("Study Name", "")})
    access_values = sorted({row.get("Study Access", "") for row in rows if row.get("Study Access", "")})
    total_size = sum(parse_int(row.get("File Size (in bytes)")) or 0 for row in rows)
    selected = ct_rows[0] if len(ct_rows) == 1 else {}

    warnings: list[str] = []
    if len(rows) == 0:
        warnings.append("manifest_is_empty")
    if len(ct_rows) == 0:
        warnings.append("no_ct_dicom_row_found")
    if len(ct_rows) > 1:
        warnings.append("multiple_ct_dicom_rows_selected_review_before_download")
    if EXPECTED_PARTICIPANT not in participant_ids:
        warnings.append("participant_id_does_not_match_expected_0522c0027")
    if EXPECTED_STUDY not in study_names:
        warnings.append("study_name_does_not_match_expected_head_neck_cetuximab")
    if "Controlled" in access_values:
        warnings.append("controlled_access_download_may_require_authorization")

    if len(ct_rows) == 1 and EXPECTED_PARTICIPANT in participant_ids:
        status = "single_ct_dicom_manifest_ready_for_manual_download"
    elif len(ct_rows) > 1:
        status = "needs_manual_series_selection"
    else:
        status = "not_ready"

    return {
        "description": "GC/Gen3 manifest review. This is a CSV manifest, not CT image data.",
        "manifest_path": str(manifest_path),
        "row_count": len(rows),
        "ct_dicom_row_count": len(ct_rows),
        "status": status,
        "participant_ids": participant_ids,
        "study_names": study_names,
        "study_access_values": access_values,
        "total_manifest_file_size_bytes": total_size,
        "total_manifest_file_size_mb": round(total_size / 1_000_000, 3),
        "selected_file": {
            "name": selected.get("name"),
            "drs_uri": selected.get("drs_uri"),
            "md5sum": selected.get("Md5sum"),
            "file_size_bytes": parse_int(selected.get("File Size (in bytes)")),
            "file_size_mb": round((parse_int(selected.get("File Size (in bytes)")) or 0) / 1_000_000, 3),
            "file_type": selected.get("File Type"),
            "image_modality": selected.get("Image Modality"),
            "participant_id": selected.get("Participant ID"),
            "study_name": selected.get("Study Name"),
            "accession": selected.get("Accession"),
            "study_access": selected.get("Study Access"),
        },
        "local_destination_after_download": str(LOCAL_DESTINATION.resolve()),
        "warnings": warnings,
        "no_download_performed": True,
        "raw_data_written_by_this_script": False,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    selected = summary["selected_file"]
    lines = [
        "# GC 文件 Manifest 复核",
        "",
        "这个 CSV 是下载清单，不是 CT 图像本体。本脚本只解析清单，不下载数据。",
        "",
        "## 结论",
        "",
        f"- 状态：`{summary['status']}`",
        f"- 清单行数：`{summary['row_count']}`",
        f"- CT DICOM 行数：`{summary['ct_dicom_row_count']}`",
        f"- 预计文件总大小：`{summary['total_manifest_file_size_mb']} MB`",
        f"- Study access：`{', '.join(summary['study_access_values'])}`",
        "",
        "## 选中的文件",
        "",
        f"- 文件名：`{selected.get('name')}`",
        f"- Participant ID：`{selected.get('participant_id')}`",
        f"- Study：`{selected.get('study_name')}`",
        f"- Accession：`{selected.get('accession')}`",
        f"- File Type：`{selected.get('file_type')}`",
        f"- Image Modality：`{selected.get('image_modality')}`",
        f"- 大小：`{selected.get('file_size_mb')} MB`",
        f"- Md5：`{selected.get('md5sum')}`",
        f"- DRS URI：`{selected.get('drs_uri')}`",
        "",
        "## 下载后的放置位置",
        "",
        f"下载并解压后，请把 DICOM 文件放到：`{summary['local_destination_after_download']}`",
        "",
        "## 注意事项",
        "",
        "- 当前清单只包含一个 CT DICOM zip，适合先做小样本接入验证。",
        "- `Study Access=Controlled` 表示下载可能需要平台授权或登录权限。",
        "- 不要把 CSV 当作影像数据导入；真正需要的是 zip 内的 DICOM 文件。",
        "- 下载后先运行 `prepare_public_case_import.py`，不要直接进入 k-Wave。",
    ]
    if summary["warnings"]:
        lines.extend(["", "## Warning", ""])
        lines.extend(f"- `{warning}`" for warning in summary["warnings"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_next_commands(path: Path, summary: dict[str, Any]) -> None:
    case_id = EXPECTED_CASE_ID
    python_exe = r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe"
    commands = [
        "# 下载 zip 并解压 DICOM 后，再运行下面这些本地命令。",
        "# 本文件不包含任何网络下载命令。",
        "",
        f"{python_exe} prepare_public_case_import.py --case-id {case_id} --output-dir outputs\\public_case_import",
        (
            f"{python_exe} validate_ct_case.py --case-id {case_id} "
            f"--ct-path data\\raw_ct\\public\\{case_id} --output-dir outputs\\ct_case_qc\\{case_id}"
        ),
        f"{python_exe} inventory_ct_cases.py --input-dir data\\raw_ct\\public --output-dir data\\processed\\public_import",
        (
            f"{python_exe} batch_build_ct_models.py --manifest data\\processed\\public_import\\ct_case_manifest.json "
            f"--output-root outputs\\ct_acoustic_models_batch --run"
        ),
    ]
    path.write_text("\n".join(commands) + "\n", encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to GC/Gen3 manifest CSV.")
    parser.add_argument("--output-dir", default="outputs/public_gc_manifest_review")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = review_rows(read_rows(manifest_path), manifest_path)
    (output_dir / "gc_manifest_review.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8-sig",
    )
    write_markdown(output_dir / "gc_manifest_review.md", summary)
    write_next_commands(output_dir / "post_manifest_next_commands.ps1", summary)

    print(f"{summary['status']}: wrote GC manifest review to {output_dir}")


if __name__ == "__main__":
    main()
