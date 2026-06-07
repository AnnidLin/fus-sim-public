"""Write a Chinese manual TCIA single-series download guide.

The guide is intentionally offline-only: it does not download data, install
tools, or create the raw public CT folder. It documents the exact public target
and the post-download local checks that should be run after the user manually
places DICOM files in the expected folder.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FORBIDDEN_NETWORK_TOKENS = [
    "curl ",
    "Invoke-WebRequest",
    "wget ",
    "git clone",
    "nbia",
    "DataRetriever",
]


def load_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing import status file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def command_block(command: str) -> str:
    return f"```powershell\n{command}\n```"


def post_download_commands(status: dict[str, Any]) -> list[str]:
    commands = status.get("recommended_commands", {})
    ordered_keys = [
        "validate_this_case",
        "inventory_public_cases",
        "batch_build_after_manifest_update",
        "prepare_quick_pressure_after_build",
    ]
    return [commands[key] for key in ordered_keys if key in commands]


def assert_local_only(commands: list[str]) -> None:
    joined = "\n".join(commands)
    for token in FORBIDDEN_NETWORK_TOKENS:
        if token.lower() in joined.lower():
            raise ValueError(f"post-download commands contain network/download token: {token}")


def write_guide(path: Path, status: dict[str, Any], commands: list[str]) -> None:
    candidate = status["candidate"]
    case_dir = status["case_dir"]
    lines = [
        "# TCIA 单 Series 手动下载指南",
        "",
        "这份指南只用于人工下载一个指定 CT series，不允许批量下载整个 collection。",
        "",
        "## 目标数据",
        "",
        "- Collection：`Head-Neck Cetuximab`",
        "- Patient ID：`0522c0027`",
        "- Study date：`2000-05-17`",
        "- Series number：`5577`",
        f"- 本地病例 ID：`{status['case_id']}`",
        f"- 参考页面：{candidate.get('evidence_url')}",
        f"- 本地放置目录：`{case_dir}`",
        "",
        "## 手动下载约束",
        "",
        "- 只下载上面列出的一个 CT series。",
        "- 不要下载完整的 `Head-Neck Cetuximab` collection。",
        "- 本轮不要下载 PET、RTSTRUCT、RTPLAN、RTDOSE 或其他无关 study。",
        "- 如果 TCIA/NBIA 页面里无法明确只选中这个 series，先停下来人工确认，不要继续下载。",
        "- 所有数据都必须放在项目目录内，目标目录就是上面列出的本地放置目录。",
        "",
        "## 建议操作流程",
        "",
        "1. 打开 TCIA/NBIA 中 `Head-Neck Cetuximab` collection 的检索页面。",
        "2. 搜索或筛选 patient `0522c0027`。",
        "3. 选择 study date `2000-05-17`。",
        "4. 只选择 CT series `5577`。",
        "5. 将这一个 series 导出/下载为 DICOM 文件。",
        f"6. 将 DICOM 文件直接放入 `{case_dir}`。",
        "7. 下载完成后运行下面的本地检查命令。",
        "",
        "## 下载后的本地命令",
        "",
        "这些命令只做本地检查和后续流程准备，不会下载数据。",
        "",
    ]
    for command in commands:
        lines.append(command_block(command))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def write_checklist(path: Path, status: dict[str, Any]) -> None:
    case_dir = status["case_dir"]
    lines = [
        "# TCIA 下载检查清单",
        "",
        "- [ ] 确认数据来源是 TCIA `Head-Neck Cetuximab`。",
        "- [ ] 确认 patient ID 是 `0522c0027`。",
        "- [ ] 确认 study date 是 `2000-05-17`。",
        "- [ ] 确认选中的 series 是 `5577`。",
        "- [ ] 确认 modality 是 CT。",
        "- [ ] 下载前确认只选中了一个 CT series。",
        "- [ ] 确认没有混入 PET、RTSTRUCT、RTPLAN、RTDOSE 等 series。",
        f"- [ ] 将 DICOM 文件放入 `{case_dir}`。",
        "- [ ] 重新运行 `prepare_public_case_import.py`，确认状态不再是 `pending_manual_download`。",
        "- [ ] 建模前检查 QC 中的 spacing、HU 范围和骨强度 warning。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_ps1(path: Path, commands: list[str]) -> None:
    header = [
        "# hn_cetuximab_0522c0027_series5577 下载后的本地检查命令",
        "# 本文件故意不包含任何网络下载命令。",
        "",
    ]
    path.write_text("\n".join(header + commands) + "\n", encoding="utf-8-sig")


def write_summary(path: Path, status: dict[str, Any], commands: list[str], output_dir: Path) -> None:
    candidate = status["candidate"]
    summary = {
        "description": "TCIA 单 series 手动下载指南。本脚本没有下载任何文件。",
        "case_id": status["case_id"],
        "target_collection": "Head-Neck Cetuximab",
        "target_patient_id": "0522c0027",
        "target_study_date": "2000-05-17",
        "target_series_number": "5577",
        "evidence_url": candidate.get("evidence_url"),
        "local_destination": status["case_dir"],
        "no_download_performed": True,
        "raw_data_written_by_this_script": False,
        "post_download_command_count": len(commands),
        "outputs": {
            "guide": str(output_dir / "tcia_download_guide.md"),
            "checklist": str(output_dir / "tcia_download_checklist.md"),
            "commands": str(output_dir / "post_download_commands.ps1"),
        },
        "warnings": [
            "不要批量下载完整的 Head-Neck Cetuximab collection。",
            "如果 TCIA/NBIA 无法明确只选择指定 CT series，应停止并人工确认。",
        ],
    }
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--import-status",
        default="outputs/public_case_import/hn_cetuximab_0522c0027_series5577/import_status.json",
    )
    parser.add_argument("--output-dir", default="outputs/public_tcia_download_guide")
    args = parser.parse_args()

    status = load_status(Path(args.import_status))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    commands = post_download_commands(status)
    assert_local_only(commands)

    write_guide(output_dir / "tcia_download_guide.md", status, commands)
    write_checklist(output_dir / "tcia_download_checklist.md", status)
    write_ps1(output_dir / "post_download_commands.ps1", commands)
    write_summary(output_dir / "guide_summary.json", status, commands, output_dir)

    print(f"Wrote TCIA manual download guide to {output_dir}")


if __name__ == "__main__":
    main()
