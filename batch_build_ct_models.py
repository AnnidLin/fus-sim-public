from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

from build_ct_acoustic_model import CTBuildConfig, save_model


PROJECT_ROOT = Path(__file__).resolve().parent


BATCH_FIELDS = [
    "case_id",
    "status",
    "action",
    "reason",
    "format",
    "ct_path",
    "output_dir",
    "bone_threshold_hu",
    "target_dx_mm",
    "max_shape",
    "duration_s",
]


def load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"Manifest does not contain a cases list: {path}")
    return cases


def is_processable(case: dict[str, Any]) -> tuple[bool, str]:
    status = case.get("status")
    if status not in {"ok", "warning"}:
        return False, f"qc_status_{status}"
    if not bool(case.get("likely_ct_hu")):
        return False, "not_likely_ct_hu"
    if not bool(case.get("has_bone_intensity_range_gte_300hu")):
        return False, "no_bone_intensity_range_gte_300hu"
    ct_path = Path(str(case.get("ct_path", "")))
    if not ct_path.exists():
        return False, "ct_path_missing"
    fmt = case.get("format")
    if fmt not in {"nifti", "dicom_folder"}:
        return False, f"unsupported_format_{fmt}"
    return True, "ready"


def output_dir_for_case(output_root: Path, case_id: str, bone_threshold_hu: float, target_dx_mm: float) -> Path:
    bone = f"{bone_threshold_hu:g}".replace(".", "p")
    dx = f"{target_dx_mm:g}".replace(".", "p")
    return output_root / f"{case_id}_bone{bone}_dx{dx}"


def plan_case(case: dict[str, Any], output_root: Path, bone_threshold_hu: float, target_dx_mm: float, max_shape: int) -> dict[str, Any]:
    case_id = str(case.get("case_id", "unknown_case"))
    output_dir = output_dir_for_case(output_root, case_id, bone_threshold_hu, target_dx_mm)
    ok, reason = is_processable(case)
    return {
        "case_id": case_id,
        "status": "planned" if ok else "skipped",
        "action": "build" if ok else "skip",
        "reason": reason,
        "format": case.get("format"),
        "ct_path": case.get("ct_path"),
        "output_dir": str(output_dir),
        "bone_threshold_hu": float(bone_threshold_hu),
        "target_dx_mm": float(target_dx_mm),
        "max_shape": int(max_shape),
        "duration_s": "",
        "manifest_status": case.get("status"),
        "manifest_warnings": case.get("warnings", []),
    }


def build_case(plan: dict[str, Any], air_threshold_hu: float) -> dict[str, Any]:
    start = time.perf_counter()
    output_dir = Path(plan["output_dir"])
    status_path = output_dir / "build_status.json"
    result = dict(plan)
    if plan["action"] != "build":
        output_dir.mkdir(parents=True, exist_ok=True)
        result.update({"status": "skipped", "duration_s": 0.0})
        status_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        ct_path = Path(str(plan["ct_path"]))
        fmt = plan["format"]
        config = CTBuildConfig(
            dicom_dir=ct_path if fmt == "dicom_folder" else None,
            nifti_file=ct_path if fmt == "nifti" else None,
            output_dir=output_dir,
            air_threshold_hu=air_threshold_hu,
            bone_threshold_hu=float(plan["bone_threshold_hu"]),
            target_dx_m=float(plan["target_dx_mm"]) * 1e-3,
            max_shape=int(plan["max_shape"]),
        )
        save_model(config)
        result.update(
            {
                "status": "built",
                "action": "build",
                "reason": "completed",
                "duration_s": round(time.perf_counter() - start, 3),
            }
        )
    except Exception as exc:
        result.update(
            {
                "status": "failed",
                "action": "build",
                "reason": str(exc),
                "duration_s": round(time.perf_counter() - start, 3),
            }
        )
    status_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def write_batch_outputs(rows: list[dict[str, Any]], output_root: Path, mode: str, args: argparse.Namespace) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "batch_plan.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=BATCH_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    summary = {
        "description": "Batch CT acoustic model build plan/results.",
        "mode": mode,
        "manifest": str(args.manifest),
        "output_root": str(output_root),
        "bone_threshold_hu": args.bone_threshold_hu,
        "air_threshold_hu": args.air_threshold_hu,
        "target_dx_mm": args.target_dx_mm,
        "max_shape": args.max_shape,
        "case_count": len(rows),
        "planned_count": sum(1 for row in rows if row.get("status") == "planned"),
        "built_count": sum(1 for row in rows if row.get("status") == "built"),
        "skipped_count": sum(1 for row in rows if row.get("status") == "skipped"),
        "failed_count": sum(1 for row in rows if row.get("status") == "failed"),
        "cases": rows,
    }
    (output_root / "batch_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch-build CT acoustic models from a case manifest.")
    parser.add_argument(
        "--manifest",
        default=str(PROJECT_ROOT / "data" / "processed" / "ct_case_manifest.json"),
        help="Input manifest generated by inventory_ct_cases.py.",
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_models_batch"),
        help="Root output directory for independent per-case acoustic models.",
    )
    parser.add_argument("--bone-threshold-hu", type=float, default=300.0, help="Bone threshold forwarded to build_ct_acoustic_model.")
    parser.add_argument("--air-threshold-hu", type=float, default=-500.0, help="Air/background threshold forwarded to build_ct_acoustic_model.")
    parser.add_argument("--target-dx-mm", type=float, default=1.0, help="Target isotropic voxel size forwarded to build_ct_acoustic_model.")
    parser.add_argument("--max-shape", type=int, default=220, help="Maximum output dimension forwarded to build_ct_acoustic_model.")
    parser.add_argument("--run", action="store_true", help="Actually build models. Without this flag, only write a dry-run plan.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_manifest(Path(args.manifest))
    output_root = Path(args.output_root)
    plans = [plan_case(case, output_root, args.bone_threshold_hu, args.target_dx_mm, args.max_shape) for case in cases]

    if not args.run:
        write_batch_outputs(plans, output_root, "dry_run", args)
        for plan in plans:
            print(f"{plan['status'].upper()}: {plan['case_id']} -> {plan['output_dir']} ({plan['reason']})")
        print(f"Dry-run only. Add --run to build models. Wrote {output_root / 'batch_plan.csv'}")
        return

    results: list[dict[str, Any]] = []
    for plan in plans:
        print(f"{plan['action'].upper()}: {plan['case_id']} -> {plan['output_dir']}")
        result = build_case(plan, args.air_threshold_hu)
        print(f"{result['status'].upper()}: {result['case_id']} ({result['reason']}, {result['duration_s']} s)")
        results.append(result)
    write_batch_outputs(results, output_root, "run", args)
    print(f"Batch build complete. Wrote {output_root / 'batch_summary.json'}")


if __name__ == "__main__":
    main()
