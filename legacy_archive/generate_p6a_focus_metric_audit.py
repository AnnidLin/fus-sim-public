from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from simulate_kwave_3d_focus import compute_focus_metrics


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard"
OUT_DIR = ROOT / "outputs/p6a_focus_metric_semantics_audit/079_candidate_006_dx0p75"
OUT_JSON = OUT_DIR / "focus_metric_semantics_audit.json"
OUT_MD = OUT_DIR / "focus_metric_semantics_audit.md"

LEGACY_FIELDS = [
    "global_peak_index_ijk",
    "global_peak_mpa",
    "global_peak_to_target_distance_mm",
    "target_pressure_mpa",
    "target_window_peak_index_ijk",
    "target_window_peak_mpa",
    "effective_start_x_index",
    "effective_peak_index_ijk",
    "effective_peak_mpa",
    "effective_peak_to_target_distance_mm",
    "target_to_global_peak_ratio",
    "target_to_effective_peak_ratio",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def equal_value(left: Any, right: Any) -> bool:
    if isinstance(left, list) or isinstance(right, list):
        return left == right
    if isinstance(left, (float, int)) and isinstance(right, (float, int)):
        return bool(np.isclose(float(left), float(right), rtol=0.0, atol=1e-7))
    return left == right


def build() -> dict[str, Any]:
    with np.load(INPUT_DIR / "pressure_max_mpa.npz") as data:
        pressure = np.asarray(data["pressure_max_mpa"], dtype=np.float32)
        source_mask = np.asarray(data["source_mask"], dtype=bool)
        target = np.asarray(data["target_index_ijk"], dtype=np.int32)
        labels = np.asarray(data["labels"], dtype=np.uint8)
        dx_m = float(np.asarray(data["dx_m"]).item())
        nearfield_m = float(np.asarray(data["nearfield_exclusion_m"]).item())

    dry_run = load_json(INPUT_DIR / "quality_dry_run_summary.json")
    legacy = load_json(INPUT_DIR / "focus_metrics.json")
    source_center = np.asarray(dry_run["source"]["source_center_index_ijk"], dtype=np.int32)
    entry = np.asarray(dry_run["source"]["entry_index_ijk"], dtype=np.int32)
    metrics = compute_focus_metrics(
        pressure,
        source_mask,
        target,
        dx_m,
        nearfield_m,
        source_center_index_ijk=source_center,
        entry_index_ijk=entry,
    )
    regression = {field: equal_value(metrics.get(field), legacy.get(field)) for field in LEGACY_FIELDS}

    peak_keys = {
        "global": "global_peak_index_ijk",
        "beam_axis_nearfield": "beam_axis_effective_peak_index_ijk",
        "post_entry": "post_entry_peak_index_ijk",
        "legacy_effective": "effective_peak_index_ijk",
        "target_window": "target_window_peak_index_ijk",
    }
    peak_labels = {
        name: int(labels[tuple(metrics[field])])
        for name, field in peak_keys.items()
    }
    source_x_max = int(np.max(np.where(source_mask)[0]))
    legacy_start_from_source_center_mm = float((metrics["effective_start_x_index"] - source_center[0]) * dx_m * 1e3)
    return {
        "audit_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": "079",
        "candidate_id": "candidate_006",
        "input_pressure": str((INPUT_DIR / "pressure_max_mpa.npz").relative_to(ROOT)).replace("\\", "/"),
        "no_kwave_execution": True,
        "legacy_regression": {
            "all_preserved": all(regression.values()),
            "fields": regression,
        },
        "semantics": {
            "declared_nearfield_exclusion_mm": metrics["nearfield_exclusion_mm"],
            "source_center_index_ijk": source_center.tolist(),
            "source_mask_x_max": source_x_max,
            "legacy_effective_start_x_index": metrics["effective_start_x_index"],
            "legacy_start_x_distance_from_source_center_mm": legacy_start_from_source_center_mm,
            "legacy": metrics["legacy_effective_peak_semantics"],
            "beam_axis": metrics["beam_axis_nearfield_semantics"],
            "post_entry": metrics["post_entry_semantics"],
        },
        "metrics": metrics,
        "peak_labels": peak_labels,
        "findings": [
            "The legacy effective peak is an x-plane exclusion after the source-mask front, not a 10 mm beam-axis exclusion from source center.",
            "The beam-axis 10 mm effective peak equals the global peak for this dataset.",
            "The explicit post-entry peak remains strongly prefocal, so metric semantics do not fully explain prefocal dominance.",
            "The target-window peak is close to the intended target but weaker than prefocal maxima.",
        ],
        "decision": {
            "p6a_complete": True,
            "recommended_next_packet": "P6b_post_skull_beam_axis_profile_and_interface_audit",
            "authorization": "not_required_read_only_no_kwave",
            "reason": "Trace pressure and material labels along the beam through entry and skull exit before considering geometry changes or a new pressure run.",
            "pressure_execution_authorized": False,
        },
        "blocked_claims": [
            "prefocal dominance root cause fully established",
            "tuned focus",
            "validated pressure baseline",
            "numerical convergence",
            "clinical or medical safety",
        ],
    }


def markdown(audit: dict[str, Any]) -> str:
    metrics = audit["metrics"]
    semantics = audit["semantics"]
    lines = [
        "# P6a Focus Metric Semantics Audit",
        "",
        f"- legacy fields preserved: `{audit['legacy_regression']['all_preserved']}`",
        f"- no k-Wave execution: `{audit['no_kwave_execution']}`",
        f"- next packet: `{audit['decision']['recommended_next_packet']}`",
        "",
        "## Semantics",
        "",
        f"- declared nearfield exclusion: `{semantics['declared_nearfield_exclusion_mm']}` mm",
        f"- legacy x-start distance from source center: `{semantics['legacy_start_x_distance_from_source_center_mm']:.3f}` mm",
        f"- legacy rule: `{semantics['legacy']}`",
        f"- beam-axis rule: `{semantics['beam_axis']}`",
        f"- post-entry rule: `{semantics['post_entry']}`",
        "",
        "## Recomputed Peaks",
        "",
        f"- global / beam-axis 10 mm peak: `{metrics['global_peak_mpa']:.6f}` MPa at `{metrics['global_peak_index_ijk']}`",
        f"- post-entry peak: `{metrics['post_entry_peak_mpa']:.6f}` MPa; axial shortfall `{metrics['post_entry_peak_axial_shortfall_to_target_mm']:.3f}` mm",
        f"- legacy effective peak: `{metrics['effective_peak_mpa']:.6f}` MPa; axial shortfall `{metrics['legacy_effective_peak_axial_shortfall_to_target_mm']:.3f}` mm",
        f"- target-window peak: `{metrics['target_window_peak_mpa']:.6f}` MPa; axial shortfall `{metrics['target_window_peak_axial_shortfall_to_target_mm']:.3f}` mm",
        "",
        "## Findings",
        "",
    ]
    lines.extend(f"- {item}" for item in audit["findings"])
    lines.extend(["", "No pressure, thermal, or safety conclusion is authorized by this audit.", ""])
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = build()
    OUT_JSON.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(markdown(audit), encoding="utf-8")
    print(json.dumps({"legacy_preserved": audit["legacy_regression"]["all_preserved"], "post_entry_peak_mpa": audit["metrics"]["post_entry_peak_mpa"], "next_packet": audit["decision"]["recommended_next_packet"]}))


if __name__ == "__main__":
    main()
