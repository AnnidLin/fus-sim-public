from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from plan_ct_target_entry import load_model, plan_left_x_entry, save_layout_images, write_summary
from simulate_kwave_3d_focus import KWave3DConfig, build_source_mask, load_model as load_kwave_model


import argparse

PROJECT_ROOT = Path(__file__).resolve().parent
OLD_ENTRY_PLAN = PROJECT_ROOT / "outputs/case_refinement_plan/079/candidate_006/entry_plan.json"

# Parse command line arguments
parser = argparse.ArgumentParser(description="Generate corrected entry-plan resolution chain.")
parser.add_argument("--dx", choices=["0.75", "0.5"], default="0.75", help="Grid resolution in mm.")
args, _ = parser.parse_known_args()

dx_str = "dx0p75" if args.dx == "0.75" else "dx0p5"
OUT_DIR = PROJECT_ROOT / f"outputs/corrected_entry_plan_resolution_chain/079_candidate_006_{dx_str}"
TARGET_MODEL = PROJECT_ROOT / f"outputs/ct_acoustic_model_3d_profile_hu300_{dx_str}/acoustic_model_3d.npz"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def material_ranges(model) -> dict[str, list[float]]:
    return {
        "sound_speed_m_s": [float(model.sound_speed.min()), float(model.sound_speed.max())],
        "density_kg_m3": [float(model.density.min()), float(model.density.max())],
        "alpha_db_mhz_cm": [float(model.alpha_coeff.min()), float(model.alpha_coeff.max())],
    }


def source_and_crop_diagnostics(entry_plan_path: Path) -> dict[str, Any]:
    config = KWave3DConfig(
        model_path=TARGET_MODEL,
        entry_plan_path=entry_plan_path,
        quick_mode=True,
        quick_lateral_half_width_m=17e-3,
        quick_post_target_margin_m=8e-3,
        transducer_radius_m=35e-3,
        aperture_diameter_m=30e-3,
        tone_burst_cycles=8,
        cfl=0.2,
        simulation_time_s=55e-6,
        pml_size=12,
        preset="standard",
    )
    model = load_kwave_model(config)
    _source_mask, source_metadata = build_source_mask(model, config)
    counts = source_metadata.get("source_label_counts", {})
    return {
        "crop_origin_ijk": model.crop_origin_ijk.astype(int).tolist(),
        "crop_shape": [int(v) for v in model.sound_speed.shape],
        "target_index_in_crop_ijk": model.target_index_ijk.astype(int).tolist(),
        "source_label_counts": counts,
        "source_points": int(source_metadata["source_points"]),
        "source_mask_background_only": int(counts.get("1", 0)) == 0 and int(counts.get("2", 0)) == 0,
        "material_ranges": material_ranges(model),
        "crop_contains_skull_material": float(model.sound_speed.max()) >= 2500.0,
    }


def candidate_plan(
    candidate_id: str,
    target_index: np.ndarray,
    labels: np.ndarray,
    dx_m: float,
    output_dir: Path,
) -> dict[str, Any]:
    candidate_dir = output_dir / "candidates" / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    plan = plan_left_x_entry(labels, dx_m, target_index.astype(np.int32), 16.0, (10.0, 0.0))
    save_layout_images(candidate_dir, labels, plan)
    write_summary(candidate_dir, TARGET_MODEL, plan)
    diagnostics = source_and_crop_diagnostics(candidate_dir / "entry_plan.json")
    geometry_delta_mm = abs(float(plan["source_to_target_distance_mm"]) - 47.07441141967374)
    checks = {
        "resolution_matches": abs(float(plan["dx_m"]) - dx_m) <= 1e-12 and list(plan["model_shape"]) == list(labels.shape),
        "source_center_background": int(plan["source_center_label"]) == 0,
        "entry_is_skull": int(plan["entry_label"]) == 2,
        "target_is_soft_tissue": int(plan["target_label"]) == 1,
        "has_skull_crossing": bool(plan["has_skull_crossing"]),
        "source_mask_background_only": bool(diagnostics["source_mask_background_only"]),
        "crop_contains_skull_material": bool(diagnostics["crop_contains_skull_material"]),
    }
    return {
        "candidate_id": candidate_id,
        "entry_plan_path": rel(candidate_dir / "entry_plan.json"),
        "target_index_ijk": plan["target_index_ijk"],
        "source_center_index_ijk": plan["source_center_index_ijk"],
        "entry_index_ijk": plan["entry_index_ijk"],
        "beam_axis": plan["beam_axis"],
        "source_to_target_distance_mm": plan["source_to_target_distance_mm"],
        "skull_path_length_mm": plan["skull_path_length_mm"],
        "geometry_delta_from_historical_mm": geometry_delta_mm,
        "checks": checks,
        "diagnostics": diagnostics,
        "passed": all(checks.values()),
    }


def build_chain() -> dict[str, Any]:
    labels, dx_m, model_target = load_model(TARGET_MODEL)
    old_plan = read_json(OLD_ENTRY_PLAN)
    old_target = np.asarray(old_plan["target_index_ijk"], dtype=float)
    old_dx = float(old_plan["dx_m"])
    scaled_target = np.rint(old_target * old_dx / dx_m).astype(np.int32)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = [
        candidate_plan("model_target", model_target, labels, dx_m, OUT_DIR),
        candidate_plan("scaled_old_target", scaled_target, labels, dx_m, OUT_DIR),
    ]
    viable = [item for item in candidates if item["passed"]]
    selected = sorted(viable, key=lambda item: item["geometry_delta_from_historical_mm"])[0]
    selected_path = OUT_DIR / "selected_entry_plan.json"
    shutil.copyfile(PROJECT_ROOT / selected["entry_plan_path"], selected_path)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "corrected_entry_plan_resolution_chain",
        "case_id": "079",
        "candidate_id": "candidate_006",
        "target_model": rel(TARGET_MODEL),
        "old_entry_plan": rel(OLD_ENTRY_PLAN),
        "selection_rule": "choose passed candidate with closest source_to_target distance to historical candidate_006",
        "historical_source_to_target_distance_mm": 47.07441141967374,
        "candidates": candidates,
        "selected_candidate_id": selected["candidate_id"],
        "selected_entry_plan": rel(selected_path),
        "pressure_execution_allowed": False,
        "next_required_gate": "dry-run-quality with selected_entry_plan; no pressure execution",
        "not_executed": ["pressure simulation", "thermal simulation", "paper-grade run"],
    }


def markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Corrected Entry-Plan Resolution Chain - Case 079 candidate_006 dx{args.dx}",
        "",
        f"- target model: `{summary['target_model']}`",
        f"- old entry plan: `{summary['old_entry_plan']}`",
        f"- selected candidate: `{summary['selected_candidate_id']}`",
        f"- selected entry plan: `{summary['selected_entry_plan']}`",
        f"- pressure execution allowed: `{summary['pressure_execution_allowed']}`",
        "",
        "## Candidates",
        "",
        "| Candidate | Passed | Source-target mm | Historical delta mm | Skull path mm | Source counts | Crop material max c/rho/alpha |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for item in summary["candidates"]:
        mat = item["diagnostics"]["material_ranges"]
        maxima = f"{mat['sound_speed_m_s'][1]:.1f}/{mat['density_kg_m3'][1]:.1f}/{mat['alpha_db_mhz_cm'][1]:.3f}"
        lines.append(
            f"| `{item['candidate_id']}` | `{item['passed']}` | {item['source_to_target_distance_mm']:.3f} | "
            f"{item['geometry_delta_from_historical_mm']:.3f} | {item['skull_path_length_mm']:.3f} | "
            f"`{item['diagnostics']['source_label_counts']}` | {maxima} |"
        )
    lines.extend(["", "## Next Gate", "", f"- {summary['next_required_gate']}", "", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in summary["not_executed"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    summary = build_chain()
    summary_path = OUT_DIR / "corrected_entry_plan_resolution_chain.json"
    report_path = OUT_DIR / "corrected_entry_plan_resolution_chain.md"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(markdown(summary), encoding="utf-8")
    print(f"Wrote {rel(summary_path)}")
    print(f"Wrote {rel(report_path)}")
    print(json.dumps({"selected_candidate_id": summary["selected_candidate_id"], "pressure_execution_allowed": False}))


if __name__ == "__main__":
    main()
