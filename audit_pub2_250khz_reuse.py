#!/usr/bin/env python3
"""Inventory existing 250 kHz CT runs for PUB.2 reuse eligibility."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nested(value: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def discover_summaries(output_root: Path) -> list[Path]:
    paths = []
    for path in output_root.rglob("summary.json"):
        try:
            summary = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        frequency = nested(summary, "config", "frequency_hz")
        if frequency is None:
            frequency = nested(summary, "simulation_quality", "frequency_hz")
        if frequency is not None and float(frequency) == 250_000.0:
            paths.append(path)
    return sorted(paths)


def alpha_semantics(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("alpha_semantics")
    if not isinstance(value, dict):
        value = nested(summary, "model", "alpha_semantics", default={})
    if not isinstance(value, dict):
        value = {}
    return {
        "status": value.get("alpha_semantics_status", "missing"),
        "unit": value.get("alpha_unit_semantics"),
        "kind": value.get("alpha_coeff_kind"),
        "source_route": value.get("alpha_source_route"),
        "pressure_allowed": value.get("pressure_allowed_by_alpha_semantics"),
    }


def classify_method(summary: dict[str, Any]) -> str:
    stage = str(summary.get("stage", "")).lower()
    description = str(summary.get("description", "")).lower()
    if stage == "refocus" or "time-reversal" in description:
        return "time_reversal"
    return "baseline"


def extract_record(summary_path: Path) -> dict[str, Any]:
    summary = load_json(summary_path)
    output_dir = summary_path.parent
    config = summary.get("config", {})
    quality = summary.get("simulation_quality", {})
    if not isinstance(config, dict) or not isinstance(quality, dict):
        raise ValueError(f"{summary_path}: missing config or simulation_quality")
    alpha = alpha_semantics(summary)
    required_files = (
        output_dir / "pressure_max_mpa.npz",
        output_dir / "focus_metrics.json",
    )
    core_complete = all(path.is_file() for path in required_files)
    model_path = config.get("model_path")
    entry_plan_path = config.get("entry_plan_path")
    record = {
        "summary_path": str(summary_path.resolve()),
        "summary_sha256": sha256_file(summary_path),
        "output_dir": str(output_dir.resolve()),
        "method": classify_method(summary),
        "preset": config.get("preset"),
        "frequency_hz": config.get("frequency_hz"),
        "model_path": model_path,
        "entry_plan_path": entry_plan_path,
        "dx_mm": quality.get("dx_mm"),
        "grid_size": quality.get("grid_size"),
        "voxel_count": quality.get("voxel_count"),
        "pml_size": config.get("pml_size"),
        "cfl": config.get("cfl"),
        "nt": nested(summary, "runtime", "nt"),
        "dt_s": nested(summary, "runtime", "dt_s"),
        "source_pressure_pa": config.get("source_pressure_pa"),
        "radius_mm": (
            float(config["transducer_radius_m"]) * 1000
            if config.get("transducer_radius_m") is not None
            else None
        ),
        "aperture_mm": (
            float(config["aperture_diameter_m"]) * 1000
            if config.get("aperture_diameter_m") is not None
            else None
        ),
        "cycles": config.get("tone_burst_cycles"),
        "quick_lateral_mm": (
            float(config["quick_lateral_half_width_m"]) * 1000
            if config.get("quick_lateral_half_width_m") is not None
            else None
        ),
        "quick_post_target_mm": (
            float(config["quick_post_target_margin_m"]) * 1000
            if config.get("quick_post_target_margin_m") is not None
            else None
        ),
        "backend": config.get("backend"),
        "device": config.get("device"),
        "alpha_semantics": alpha,
        "core_outputs_complete": core_complete,
    }
    blockers = []
    if not core_complete:
        blockers.append("incomplete_pressure_or_focus_outputs")
    if alpha["status"] in {"missing", "missing_alpha_semantics", None}:
        blockers.append("missing_alpha_semantics")
    if alpha["pressure_allowed"] is False:
        blockers.append("alpha_semantics_pressure_blocked")
    if config.get("preset") != "standard":
        blockers.append("nonstandard_preset_context_only")
    record["pub2_reuse_status"] = (
        "candidate_for_matched_design" if not blockers else "context_only_or_blocked"
    )
    record["pub2_reuse_blockers"] = blockers
    return record


FINGERPRINT_FIELDS = (
    "method",
    "preset",
    "model_path",
    "entry_plan_path",
    "dx_mm",
    "grid_size",
    "pml_size",
    "cfl",
    "nt",
    "source_pressure_pa",
    "radius_mm",
    "aperture_mm",
    "cycles",
    "quick_lateral_mm",
    "quick_post_target_mm",
    "backend",
    "device",
)


def changed_fields(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    return [
        field
        for field in FINGERPRINT_FIELDS
        if left.get(field) != right.get(field)
    ]


def build_report(summary_paths: list[Path]) -> dict[str, Any]:
    records = [extract_record(path) for path in summary_paths]
    status_counts = Counter(record["pub2_reuse_status"] for record in records)
    blocker_counts = Counter(
        blocker
        for record in records
        for blocker in record["pub2_reuse_blockers"]
    )
    single_variable_pairs = []
    for left_index, left in enumerate(records):
        for right in records[left_index + 1 :]:
            changes = changed_fields(left, right)
            if len(changes) == 1:
                single_variable_pairs.append(
                    {
                        "left": left["summary_path"],
                        "right": right["summary_path"],
                        "changed_field": changes[0],
                        "eligible": (
                            left["pub2_reuse_status"]
                            == right["pub2_reuse_status"]
                            == "candidate_for_matched_design"
                        ),
                    }
                )
    return {
        "schema_version": "1.0",
        "report_id": "pub2_existing_250khz_reuse_audit",
        "status": "inventory_complete_no_execution",
        "record_count": len(records),
        "status_counts": dict(status_counts),
        "blocker_counts": dict(blocker_counts),
        "records": records,
        "single_variable_pairs": single_variable_pairs,
        "decision": {
            "pressure_execution_authorized": False,
            "existing_results_close_pub2": False,
            "next_action": (
                "After PUB.1 closeout, freeze one matched Case079 baseline/TR "
                "configuration with explicit alpha semantics, then generate "
                "dx/PML/CFL/domain dry-runs before any new pressure execution."
            ),
        },
        "claim_boundary": (
            "This is a metadata reuse audit only and does not establish "
            "numerical sensitivity, convergence, efficacy, or safety."
        ),
    }


def write_package(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "pub2_250khz_reuse_audit.json"
    csv_path = output_dir / "pub2_250khz_reuse_inventory.csv"
    markdown_path = output_dir / "pub2_250khz_reuse_audit.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    csv_fields = [
        "summary_path",
        "method",
        "preset",
        "dx_mm",
        "grid_size",
        "pml_size",
        "cfl",
        "nt",
        "radius_mm",
        "aperture_mm",
        "cycles",
        "alpha_semantics",
        "core_outputs_complete",
        "pub2_reuse_status",
        "pub2_reuse_blockers",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for record in report["records"]:
            writer.writerow(
                {
                    field: (
                        json.dumps(record.get(field), ensure_ascii=False)
                        if isinstance(record.get(field), (dict, list))
                        else record.get(field)
                    )
                    for field in csv_fields
                }
            )
    lines = [
        "# PUB.2 Existing 250 kHz Reuse Audit",
        "",
        f"- Records inspected: {report['record_count']}",
        f"- Status counts: `{json.dumps(report['status_counts'], ensure_ascii=False)}`",
        f"- Blocker counts: `{json.dumps(report['blocker_counts'], ensure_ascii=False)}`",
        f"- Exact single-variable pairs found: {len(report['single_variable_pairs'])}",
        "- New pressure execution authorized: **no**",
        "",
        "Existing runs are retained as engineering context. They close PUB.2 "
        "only if a future matched design resolves every recorded blocker; this "
        "audit itself is not numerical-sensitivity evidence.",
        "",
    ]
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    paths = discover_summaries(args.output_root.resolve())
    report = build_report(paths)
    write_package(report, args.output_dir.resolve())
    print(
        json.dumps(
            {
                "status": report["status"],
                "records": report["record_count"],
                "output_dir": str(args.output_dir.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
