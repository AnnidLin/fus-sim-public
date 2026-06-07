"""Prepare a manually downloaded public DICOM zip for local import.

This script does not download data. By default it only checks whether the
expected zip exists, verifies size/MD5 when present, lists zip contents, and
writes Chinese next-step notes. Use --extract explicitly to unpack the zip into
the public raw CT destination.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


DEFAULT_CASE_ID = "hn_cetuximab_0522c0027_series5577"


def load_manifest_review(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest review: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def md5_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_member_summary(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        names = [info.filename for info in infos]
        dcm_like = [
            name
            for name in names
            if Path(name).suffix.lower() in {".dcm", ".dicom", ".ima", ""} and not name.endswith("/")
        ]
        return {
            "member_count": len(names),
            "dcm_like_count": len(dcm_like),
            "first_members": names[:20],
            "uncompressed_size_bytes": int(sum(info.file_size for info in infos)),
        }


def safe_extract(zip_path: Path, destination: Path) -> int:
    destination_resolved = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (destination / member.filename).resolve()
            if not str(target).startswith(str(destination_resolved)):
                raise ValueError(f"Unsafe zip member path: {member.filename}")
            zf.extract(member, destination)
            if not member.is_dir():
                count += 1
    return count


def build_post_extract_commands(case_id: str) -> list[str]:
    python_exe = r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe"
    return [
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
        (
            f"{python_exe} prepare_case_quick_pressure.py "
            f"--batch-summary outputs\\ct_acoustic_models_batch\\batch_summary.json "
            f"--output-dir outputs\\case_quick_pressure_plan"
        ),
    ]


def summarize(
    manifest_review: dict[str, Any],
    zip_path: Path,
    destination: Path,
    extract: bool,
) -> dict[str, Any]:
    selected = manifest_review["selected_file"]
    expected_name = selected.get("name")
    expected_size = selected.get("file_size_bytes")
    expected_md5 = selected.get("md5sum")

    summary: dict[str, Any] = {
        "description": "本地 DICOM zip 接入守门检查。本脚本不下载数据。",
        "case_id": DEFAULT_CASE_ID,
        "expected_zip_name": expected_name,
        "expected_size_bytes": expected_size,
        "expected_md5": expected_md5,
        "zip_path": str(zip_path),
        "zip_exists": zip_path.exists(),
        "destination": str(destination.resolve()),
        "extract_requested": extract,
        "extracted_file_count": 0,
        "no_download_performed": True,
        "post_extract_commands": build_post_extract_commands(DEFAULT_CASE_ID),
        "warnings": [],
    }

    if not zip_path.exists():
        summary["status"] = "pending_zip_download"
        summary["warnings"].append("zip_not_found_place_downloaded_zip_at_expected_path")
        return summary

    actual_size = zip_path.stat().st_size
    actual_md5 = md5_file(zip_path)
    summary.update(
        {
            "actual_size_bytes": actual_size,
            "actual_size_matches": actual_size == expected_size,
            "actual_md5": actual_md5,
            "actual_md5_matches": actual_md5.lower() == str(expected_md5).lower(),
            "zip_member_summary": zip_member_summary(zip_path),
        }
    )

    if zip_path.name != expected_name:
        summary["warnings"].append("zip_filename_differs_from_manifest_name")
    if actual_size != expected_size:
        summary["warnings"].append("zip_size_mismatch")
    if actual_md5.lower() != str(expected_md5).lower():
        summary["warnings"].append("zip_md5_mismatch")

    if summary["warnings"]:
        summary["status"] = "zip_found_but_needs_review"
        return summary

    if extract:
        summary["extracted_file_count"] = safe_extract(zip_path, destination)
        summary["status"] = "zip_verified_and_extracted"
        summary["raw_data_written_by_this_script"] = True
    else:
        summary["status"] = "zip_verified_ready_to_extract"
        summary["raw_data_written_by_this_script"] = False
    return summary


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# 公开 DICOM Zip 接入检查",
        "",
        "这个文件用于检查手动下载的 zip 是否符合 manifest。默认只检查，不解压。",
        "",
        "## 状态",
        "",
        f"- 状态：`{summary['status']}`",
        f"- 期望 zip：`{summary['expected_zip_name']}`",
        f"- 当前 zip 路径：`{summary['zip_path']}`",
        f"- zip 是否存在：`{summary['zip_exists']}`",
        f"- 解压目标目录：`{summary['destination']}`",
        f"- 是否请求解压：`{summary['extract_requested']}`",
    ]
    if summary.get("actual_size_bytes") is not None:
        lines.extend(
            [
                "",
                "## 完整性检查",
                "",
                f"- 大小匹配：`{summary.get('actual_size_matches')}`",
                f"- MD5 匹配：`{summary.get('actual_md5_matches')}`",
                f"- 实际 MD5：`{summary.get('actual_md5')}`",
            ]
        )
    if summary.get("zip_member_summary"):
        member = summary["zip_member_summary"]
        lines.extend(
            [
                "",
                "## Zip 内容概览",
                "",
                f"- 文件数：`{member['member_count']}`",
                f"- DICOM-like 文件数：`{member['dcm_like_count']}`",
                f"- 解压后总大小：`{round(member['uncompressed_size_bytes'] / 1_000_000, 3)} MB`",
                "- 前 20 个文件：",
            ]
        )
        lines.extend(f"  - `{name}`" for name in member["first_members"])
    if summary.get("warnings"):
        lines.extend(["", "## Warning", ""])
        lines.extend(f"- `{warning}`" for warning in summary["warnings"])
    lines.extend(["", "## 下载后/解压后命令", ""])
    lines.extend("```powershell\n" + command + "\n```" for command in summary["post_extract_commands"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_commands(path: Path, commands: list[str]) -> None:
    path.write_text(
        "# zip 解压并确认后运行这些本地命令。\n# 本文件不包含下载命令。\n\n"
        + "\n".join(commands)
        + "\n",
        encoding="utf-8-sig",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-review", default="outputs/public_gc_manifest_review/gc_manifest_review.json")
    parser.add_argument("--zip-path", default=None)
    parser.add_argument("--destination", default=str(Path("data/raw_ct/public") / DEFAULT_CASE_ID))
    parser.add_argument("--output-dir", default="outputs/public_zip_import")
    parser.add_argument("--extract", action="store_true", help="Extract the verified zip into --destination.")
    args = parser.parse_args()

    manifest_review = load_manifest_review(Path(args.manifest_review))
    selected = manifest_review["selected_file"]
    zip_path = Path(args.zip_path) if args.zip_path else Path("data/raw_ct/public_downloads") / selected["name"]
    destination = Path(args.destination)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = summarize(manifest_review, zip_path, destination, args.extract)
    (output_dir / "zip_import_status.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8-sig",
    )
    write_markdown(output_dir / "zip_import_status.md", summary)
    write_commands(output_dir / "post_extract_commands.ps1", summary["post_extract_commands"])

    print(f"{summary['status']}: wrote zip import status to {output_dir}")


if __name__ == "__main__":
    main()
