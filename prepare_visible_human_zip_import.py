"""Split and import Visible Human head CT DICOM zip files.

The Dataverse download can contain both VHF and VHM head CT DICOM files in one
zip. This script groups files by DICOM SeriesInstanceUID and, when --extract is
given, safely extracts each series into its own public CT case directory.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import pydicom


DEFAULT_OUTPUT_DIR = Path("outputs/visible_human_zip_import")
DEFAULT_ZIP_PATH = Path("data/raw_ct/dataverse_files.zip")
DEFAULT_DEST_ROOT = Path("data/raw_ct/public")


def safe_case_name(examples: list[str], patient_id: str) -> str:
    joined = " ".join(examples).upper()
    if "VHFCT" in joined:
        return "visible_human_female_head_1mm"
    if "VHMCT" in joined:
        return "visible_human_male_head_1mm"
    patient = re.sub(r"[^A-Za-z0-9_]+", "_", patient_id).strip("_").lower()
    return f"visible_human_head_1mm_{patient or 'unknown'}"


def read_series(zip_path: Path) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "files": [],
            "examples": [],
            "patient_ids": set(),
            "series_descriptions": set(),
            "pixel_spacing": set(),
            "slice_thickness": set(),
            "modality": set(),
        }
    )
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            ds = pydicom.dcmread(io.BytesIO(zf.read(info)), stop_before_pixels=True, force=True)
            uid = str(getattr(ds, "SeriesInstanceUID", "NO_SERIES_UID"))
            group = groups[uid]
            group["files"].append(info.filename)
            if len(group["examples"]) < 8:
                group["examples"].append(info.filename)
            group["patient_ids"].add(str(getattr(ds, "PatientID", "")))
            group["series_descriptions"].add(str(getattr(ds, "SeriesDescription", "")))
            group["pixel_spacing"].add(str(getattr(ds, "PixelSpacing", "")))
            group["slice_thickness"].add(str(getattr(ds, "SliceThickness", "")))
            group["modality"].add(str(getattr(ds, "Modality", "")))

    summaries: list[dict[str, Any]] = []
    for uid, group in groups.items():
        patient_ids = sorted(group["patient_ids"])
        examples = group["examples"]
        case_id = safe_case_name(examples, patient_ids[0] if patient_ids else "")
        summaries.append(
            {
                "series_instance_uid": uid,
                "case_id": case_id,
                "file_count": len(group["files"]),
                "patient_ids": patient_ids,
                "series_descriptions": sorted(group["series_descriptions"]),
                "pixel_spacing": sorted(group["pixel_spacing"]),
                "slice_thickness": sorted(group["slice_thickness"]),
                "modality": sorted(group["modality"]),
                "examples": examples,
                "files": sorted(group["files"]),
            }
        )
    return sorted(summaries, key=lambda item: item["case_id"])


def safe_extract_members(zip_path: Path, members: list[str], destination: Path) -> int:
    destination_resolved = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for member in members:
            info = zf.getinfo(member)
            # Flatten files into each case folder; the source filenames are unique.
            target = (destination / Path(member).name).resolve()
            if not str(target).startswith(str(destination_resolved)):
                raise ValueError(f"Unsafe extraction target: {target}")
            with zf.open(info) as source, target.open("wb") as sink:
                sink.write(source.read())
            count += 1
    return count


def write_outputs(output_dir: Path, zip_path: Path, dest_root: Path, series: list[dict[str, Any]], extract: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_summary = {
        "description": "Visible Human head CT zip import review.",
        "zip_path": str(zip_path),
        "zip_exists": zip_path.exists(),
        "series_count": len(series),
        "destination_root": str(dest_root.resolve()),
        "extract_requested": extract,
        "series": [
            {key: value for key, value in item.items() if key != "files"}
            | {"destination": str((dest_root / item["case_id"]).resolve())}
            for item in series
        ],
    }
    (output_dir / "visible_human_zip_summary.json").write_text(
        json.dumps(json_summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8-sig",
    )

    with (output_dir / "visible_human_series.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fieldnames = [
            "case_id",
            "file_count",
            "patient_ids",
            "modality",
            "pixel_spacing",
            "slice_thickness",
            "destination",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in series:
            writer.writerow(
                {
                    "case_id": item["case_id"],
                    "file_count": item["file_count"],
                    "patient_ids": ";".join(item["patient_ids"]),
                    "modality": ";".join(item["modality"]),
                    "pixel_spacing": ";".join(item["pixel_spacing"]),
                    "slice_thickness": ";".join(item["slice_thickness"]),
                    "destination": str((dest_root / item["case_id"]).resolve()),
                }
            )

    lines = [
        "# Visible Human Head CT Zip 接入复核",
        "",
        f"- Zip：`{zip_path}`",
        f"- 检测到 series 数：`{len(series)}`",
        f"- 解压目标根目录：`{dest_root.resolve()}`",
        f"- 是否执行解压：`{extract}`",
        "",
        "## Series",
        "",
    ]
    for item in series:
        lines.extend(
            [
                f"### {item['case_id']}",
                "",
                f"- 文件数：`{item['file_count']}`",
                f"- Patient ID：`{'; '.join(item['patient_ids'])}`",
                f"- Modality：`{'; '.join(item['modality'])}`",
                f"- Pixel spacing：`{'; '.join(item['pixel_spacing'])}`",
                f"- Slice thickness：`{'; '.join(item['slice_thickness'])}`",
                f"- 目标目录：`{(dest_root / item['case_id']).resolve()}`",
                f"- 示例文件：`{', '.join(item['examples'][:4])}`",
                "",
            ]
        )
    (output_dir / "visible_human_zip_summary.md").write_text("\n".join(lines), encoding="utf-8-sig")

    commands = [r"# 解压完成后运行这些本地 QC / manifest 命令。"]
    python_exe = r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe"
    for item in series:
        case_id = item["case_id"]
        commands.append(
            f"{python_exe} validate_ct_case.py --case-id {case_id} --ct-path data\\raw_ct\\public\\{case_id} --output-dir outputs\\ct_case_qc\\{case_id}"
        )
    commands.append(
        f"{python_exe} inventory_ct_cases.py --input-dir data\\raw_ct\\public --output-dir data\\processed\\public_import"
    )
    commands.append(
        f"{python_exe} batch_build_ct_models.py --manifest data\\processed\\public_import\\ct_case_manifest.json --output-root outputs\\ct_acoustic_models_batch --run"
    )
    (output_dir / "post_visible_human_extract_commands.ps1").write_text(
        "\n".join(commands) + "\n",
        encoding="utf-8-sig",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip-path", default=str(DEFAULT_ZIP_PATH))
    parser.add_argument("--dest-root", default=str(DEFAULT_DEST_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()

    zip_path = Path(args.zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip not found: {zip_path}")
    bad_member = zipfile.ZipFile(zip_path).testzip()
    if bad_member is not None:
        raise ValueError(f"Zip integrity check failed at member: {bad_member}")

    series = read_series(zip_path)
    dest_root = Path(args.dest_root)
    if args.extract:
        for item in series:
            extracted = safe_extract_members(zip_path, item["files"], dest_root / item["case_id"])
            item["extracted_file_count"] = extracted
    write_outputs(Path(args.output_dir), zip_path, dest_root, series, args.extract)
    print(f"Detected {len(series)} series in {zip_path}")
    if args.extract:
        print(f"Extracted series to {dest_root}")


if __name__ == "__main__":
    main()
