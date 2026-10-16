from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from simulate_time_reversal_focus import (
    TimeReversalConfig,
    _loader_config,
    build_bowl_mask,
    load_model,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs" / "dual_point_hotspot_constrained_tr_20260720"
CONTROL = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr"


def mask_hash(mask: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(mask, dtype=np.uint8).tobytes(order="C")).hexdigest()


def main() -> None:
    request = json.loads((OUTPUT / "hotspot_calibration_request.json").read_text(encoding="utf-8"))
    dryrun = json.loads((OUTPUT / "hotspot_calibration_dryrun" / "quality_dry_run_summary.json").read_text(encoding="utf-8"))
    cfg = dryrun["config"]
    config = TimeReversalConfig(
        model_path=ROOT / cfg["model_path"],
        entry_plan_path=ROOT / cfg["entry_plan_path"],
        calibration_point_override=tuple(cfg["calibration_point_override"]),
        transducer_radius_m=cfg["transducer_radius_m"],
        aperture_diameter_m=cfg["aperture_diameter_m"],
        cfl=cfg["cfl"],
        simulation_time_s=cfg["simulation_time_s"],
        pml_size=cfg["pml_size"],
        preset=cfg["preset"],
        quick_mode=cfg["quick_mode"],
        quick_lateral_half_width_m=cfg["quick_lateral_half_width_m"],
        quick_post_target_margin_m=cfg["quick_post_target_margin_m"],
    )
    current_mask, metadata = build_bowl_mask(load_model(_loader_config(config)), config)
    with np.load(CONTROL / "element_signals.npz", allow_pickle=False) as stored:
        control_mask = np.asarray(stored["source_mask"], dtype=np.uint8)
        control_rows = np.asarray(stored["mask_point_ijk"], dtype=np.int32)

    point = dryrun["source"]["calibration_point"]
    checks = {
        "design_status_is_nonexecuting": request["status"] == "hotspot_transfer_required_no_pressure_authorized",
        "pressure_is_not_authorized": request["hotspot_calibration_pressure_authorized"] is False,
        "refocus_is_not_authorized": request["constrained_refocus_authorized"] is False,
        "grid_is_frozen": dryrun["model"]["model_shape"] == [125, 60, 50],
        "bowl_target_is_frozen": point["bowl_geometry_target_local_ijk"] == [114, 36, 26],
        "hotspot_full_index_exact": point["full_index_ijk"] == [75, 139, 113],
        "hotspot_local_index_exact": point["local_index_ijk"] == [38, 39, 34],
        "hotspot_is_skull_label_2": point["material_label"] == 2,
        "calibration_point_is_independent": point["independent_of_bowl_geometry"] is True,
        "source_point_count_exact": metadata["source_points"] == 2979,
        "source_mask_exact": np.array_equal(current_mask.astype(np.uint8), control_mask),
        "c_order_rows_exact": np.array_equal(np.argwhere(current_mask).astype(np.int32), control_rows),
        "source_mask_hash_exact": mask_hash(current_mask) == request["source_mask_sha256"],
        "ppw_is_four": abs(dryrun["simulation_quality"]["ppw_min_sound_speed"] - 4.0) < 1e-6,
        "pml_and_cfl_frozen": dryrun["config"]["pml_size"] == 12 and dryrun["config"]["cfl"] == 0.2,
    }
    result = {
        "status": "pass" if all(checks.values()) else "fail",
        "passed": sum(checks.values()),
        "total": len(checks),
        "checks": checks,
        "current_source_mask_sha256": mask_hash(current_mask),
        "pressure_executed": False,
        "claim_boundary": "implementation_and_dryrun_only_not_pressure_evidence",
    }
    (OUTPUT / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
