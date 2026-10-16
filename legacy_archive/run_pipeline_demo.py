from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipeline_demo")



def run_command(command: list[str], description: str) -> subprocess.CompletedProcess:
    logger.info(f"Running: {' '.join(command)}")
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        logger.error(f"Failed {description}:\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}")
        raise RuntimeError(f"{description} failed with exit code {result.returncode}")
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end multi-module cascade pipeline demo script.")
    parser.add_argument("--config", default=None, help="Path to config JSON file containing MRI point and landmarks.")
    parser.add_argument("--preset", choices=["smoke", "quick", "standard", "paper_grade"], default="quick", help="Quality preset for k-Wave simulation.")
    parser.add_argument("--execute", action="store_true", help="Actually execute the k-Wave simulation.")
    parser.add_argument("--output-dir", default="outputs/pipeline_demo_079", help="Isolated output directory for pipeline results.")
    parser.add_argument("--bypass-auth", action="store_true", help="Bypass safety authorization gate for standard preset execution.")
    
    # Transducer sweep defaults which can be overridden or read
    parser.add_argument("--model", default="outputs/ct_acoustic_models_batch/079_bone300_dx1/acoustic_model_3d.npz", help="CT acoustic model path.")
    parser.add_argument("--dx-mm", type=float, default=1.0, help="CT grid voxel size in mm.")
    parser.add_argument("--theta-step", type=float, default=10.0, help="Sweep theta step in degrees.")
    parser.add_argument("--phi-step", type=float, default=30.0, help="Sweep phi step in degrees.")
    parser.add_argument("--sweep-axis", default="+x", help="Sweep propagation direction axis.")
    parser.add_argument("--radius-mm", type=float, default=30.0, help="Transducer focal radius in mm.")
    parser.add_argument("--aperture-mm", type=float, default=25.0, help="Transducer active aperture in mm.")
    parser.add_argument("--source-standoff-mm", type=float, default=8.0, help="Standoff distance in mm.")

    args = parser.parse_args()
    
    python_exe = sys.executable
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Using output directory: {output_dir}")
    
    # ==========================================
    # Step 1: MRI-CT coordinate registration mapping
    # ==========================================
    logger.info("==========================================")
    logger.info("Step 1: Running MRI-CT Coordinate Mapping")
    logger.info("==========================================")
    
    step1_dir = output_dir / "step1_registration"
    step1_dir.mkdir(parents=True, exist_ok=True)
    
    mri_point = [113.0, 101.0, 78.0]
    landmarks_path = None
    matrix_path = None
    
    # Check config
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        logger.info(f"Loading config from {config_path}...")
        with config_path.open("r", encoding="utf-8") as f:
            cfg_data = json.load(f)
        mri_point = cfg_data.get("mri_point", mri_point)
        
        # If landmarks exist in config, write them to step1 landmarks JSON
        if "mri_landmarks" in cfg_data and "ct_landmarks" in cfg_data:
            landmarks_path = step1_dir / "landmarks.json"
            landmarks_path.write_text(json.dumps({
                "mri_landmarks": cfg_data["mri_landmarks"],
                "ct_landmarks": cfg_data["ct_landmarks"]
            }, indent=2), encoding="utf-8")
            logger.info(f"Written landmarks JSON to {landmarks_path}")
            
    if not landmarks_path:
        # Fallback to identity matrix mapping
        matrix_path = step1_dir / "identity_matrix.json"
        matrix_path.write_text(json.dumps({
            "affine_matrix": np.eye(4).tolist()
        }, indent=2), encoding="utf-8")
        logger.info("No landmarks provided or config missing. Using identity matrix fallback.")
        
    map_output = step1_dir / "mapped_point.json"
    map_cmd = [
        python_exe,
        "map_mri_to_ct_coordinates.py",
        "--mri-point", f"{mri_point[0]},{mri_point[1]},{mri_point[2]}",
        "--dx-mm", str(args.dx_mm),
        "--output", str(map_output)
    ]
    if landmarks_path:
        map_cmd += ["--landmarks", str(landmarks_path)]
    else:
        map_cmd += ["--matrix", str(matrix_path)]
        
    run_command(map_cmd, "MRI-CT coordinate mapping")
    
    with map_output.open("r", encoding="utf-8") as f:
        map_data = json.load(f)
    ct_voxel_index = map_data["ct_voxel_index_ijk"]
    ct_voxel_str = ",".join(str(v) for v in ct_voxel_index)
    logger.info(f"Mapped MRI point to CT voxel index: {ct_voxel_index}")

    # ==========================================
    # Step 2: Transducer Sweep
    # ==========================================
    logger.info("==========================================")
    logger.info("Step 2: Running Transducer Sweep Scan")
    logger.info("==========================================")
    
    step2_dir = output_dir / "step2_sweep"
    step2_dir.mkdir(parents=True, exist_ok=True)
    
    # Import plan_transducer_sweep to run in-process, optimizing I/O and memory double loading
    import plan_transducer_sweep
    
    logger.info(f"Loading acoustic model: {args.model}")
    labels, dx_m, model_target = plan_transducer_sweep.load_model(Path(args.model))
    target = np.array(ct_voxel_index, dtype=np.int32)
    
    # Safety check: Verify target voxel is not inside skull bone
    if labels[tuple(target)] == 2:
        logger.error("Safety Gate Intercepted: Target voxel is located inside the skull bone!")
        raise ValueError("Safety Gate Violation: Target voxel falls inside the skull bone (Label 2). Check coordinate alignment.")
    
    logger.info("Running sweep planning in-process to avoid redundant model loading...")
    radius_gp = int(round(args.radius_mm * 1e-3 / dx_m))
    diameter_gp = plan_transducer_sweep.odd_grid_points(args.aperture_mm * 1e-3, dx_m)
    source_standoff_gp = max(1, int(round(args.source_standoff_mm * 1e-3 / dx_m)))
    
    candidates = plan_transducer_sweep.generate_spherical_candidates(
        labels=labels,
        dx_m=dx_m,
        target=target,
        radius_gp=radius_gp,
        diameter_gp=diameter_gp,
        source_standoff_gp=source_standoff_gp,
        theta_step=args.theta_step,
        theta_max=40.0,
        phi_step=args.phi_step,
        phi_range=(-30.0, 30.0),
        axis=args.sweep_axis
    )
    
    valid_cands = [c for c in candidates if c["status"] == "valid"]
    rejected_cands = [c for c in candidates if c["status"] != "valid"]
    
    logger.info(f"Sweep completed. Total: {len(candidates)}, Valid: {len(valid_cands)}, Rejected: {len(rejected_cands)}")
    
    if not valid_cands:
        logger.error("No valid transducer scan configurations found (all collided or out of bounds).")
        raise RuntimeError("No valid entry candidate found during transducer sweep.")
        
    # Estimate crop and simulation time for each candidate
    for c in candidates:
        arrival_time_us = float(c["source_to_target_distance_mm"]) * 1e-3 / 1540.0 * 1e6
        sim_time_us = min(65.0, max(45.0, arrival_time_us + 8.0))
        estimates = plan_transducer_sweep.estimate_quick_crop(c, labels.shape, dx_m, sim_time_us)
        c.update(estimates)
        
    ranked_valid = plan_transducer_sweep.rank_geometry(valid_cands)
    best_cand = ranked_valid[0]
    
    # Time window check: Ensure simulation time avoids truncation
    arrival_time_us = float(best_cand["source_to_target_distance_mm"]) * 1e-3 / 1540.0 * 1e6
    min_required_time = arrival_time_us + 16.0  # 16 us corresponds to ~8 cycles at 500 kHz
    if best_cand["sim_time_us_estimate"] < min_required_time:
        logger.warning(f"Simulation time warning: {best_cand['sim_time_us_estimate']} us is too short. Auto-correcting to {min_required_time:.2f} us to avoid truncation.")
        best_cand["sim_time_us_estimate"] = min_required_time

    best_candidate_id = best_cand["candidate_id"]
    best_theta = best_cand["theta_deg"]
    best_phi = best_cand["phi_deg"]
    logger.info(f"Best Candidate: {best_candidate_id} (theta={best_theta} deg, phi={best_phi} deg)")
    
    # Write axial and coronal slice layouts for top candidate
    cand_dir = step2_dir / best_candidate_id
    cand_dir.mkdir(parents=True, exist_ok=True)
    
    axial_img = plan_transducer_sweep.label_image(labels[:, :, target[2]].T)
    plan_transducer_sweep.draw_slice_with_beam(
        axial_img, f"Axial - {best_candidate_id} (theta={best_theta} phi={best_phi})", 
        np.array(best_cand["source_center_index_ijk"]), np.array(best_cand["entry_index_ijk"]), target, 0, 1
    ).save(cand_dir / "layout_axial.png")
    
    coronal_img = plan_transducer_sweep.label_image(labels[:, target[1], :].T)
    plan_transducer_sweep.draw_slice_with_beam(
        coronal_img, f"Coronal - {best_candidate_id} (theta={best_theta} phi={best_phi})", 
        np.array(best_cand["source_center_index_ijk"]), np.array(best_cand["entry_index_ijk"]), target, 0, 2
    ).save(cand_dir / "layout_coronal.png")
    
    # Write CSVs and summary JSON to keep step 2 directory outputs consistent
    summary_data = {
        "target_index_ijk": target.tolist(),
        "total_sweep_candidates": len(candidates),
        "valid_count": len(valid_cands),
        "rejected_count": len(rejected_cands),
        "top_geometry_candidates": [
            {
                "candidate_id": r["candidate_id"],
                "theta_deg": r["theta_deg"],
                "phi_deg": r["phi_deg"],
                "source_points": int(r["source_points"]),
                "source_label_0_count": int(r["source_label_0_count"]),
                "source_label_1_count": int(r["source_label_1_count"]),
                "source_label_2_count": int(r["source_label_2_count"]),
                "unsafe_source_points": int(r["unsafe_source_points"]),
                "unsafe_source_fraction": float(r["unsafe_source_fraction"]),
                "skull_path_length_mm": r["skull_path_length_mm"],
                "incidence_angle_deg": r["incidence_angle_deg"],
                "heuristic_transmission_proxy": r["heuristic_transmission_proxy"],
                "source_to_target_distance_mm": r["source_to_target_distance_mm"]
            }
            for r in ranked_valid[:3]
        ]
    }
    (step2_dir / "sweep_summary.json").write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Save CSVs
    import csv
    csv_header = [
        "candidate_id", "theta_deg", "phi_deg", "status", "has_collision",
        "source_points", "source_label_0_count", "source_label_1_count", "source_label_2_count",
        "unsafe_source_points", "unsafe_source_fraction",
        "skull_path_length_mm", "incidence_angle_deg", "source_to_target_distance_mm",
        "source_to_entry_distance_mm", "heuristic_transmission_proxy", "heuristic_rank",
        "recommended_for_kwave", "voxel_count", "nt_estimate", "sim_time_us_estimate"
    ]
    with open(step2_dir / "candidates_valid.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_header, extrasaction="ignore")
        writer.writeheader()
        for r in ranked_valid:
            writer.writerow(r)
            
    # Build entry plan
    entry_plan_data = {
        "description": "Spherical sweep candidate plan",
        "entry_direction": f"sweep_theta_{best_cand['theta_deg']}_phi_{best_cand['phi_deg']}",
        "entry_offset_mm": [0.0, 0.0],
        "entry_offset_grid_points_yz": [0, 0],
        "beam_axis": (np.array(best_cand["target_index_ijk"]) - np.array(best_cand["source_center_index_ijk"])).tolist(),
        "beam_unit_vector": best_cand["beam_unit_vector"],
        "target_index_ijk": best_cand["target_index_ijk"],
        "entry_index_ijk": best_cand["entry_index_ijk"],
        "source_center_index_ijk": best_cand["source_center_index_ijk"],
        "has_skull_crossing": best_cand["has_skull_crossing"],
        "source_standoff_mm": best_cand["source_to_entry_distance_mm"],
        "source_to_target_distance_mm": best_cand["source_to_target_distance_mm"],
        "skull_path_length_mm": best_cand["skull_path_length_mm"],
        "dx_m": dx_m,
        "model_shape": list(labels.shape)
    }

    # ==========================================
    # Step 3: k-Wave Simulation Cascade
    # ==========================================
    logger.info("==========================================")
    logger.info("Step 3: Running k-Wave Simulation Cascade")
    logger.info("==========================================")
    
    step3_dir = output_dir / "step3_kwave"
    step3_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the entry plan
    entry_plan_path = step3_dir / "entry_plan.json"
    entry_plan_path.write_text(json.dumps(entry_plan_data, indent=2), encoding="utf-8")
    
    # Check Safety Authorization Package if --execute and --preset standard are passed
    if args.execute and args.preset == "standard":
        auth_path = PROJECT_ROOT / "outputs" / "one_run_authorization_package" / "079_candidate_006" / "one_run_authorization_package.json"
        logger.info(f"Checking safety authorization gate at {auth_path}...")
        if not auth_path.exists():
            logger.error(f"Authorization package not found at {auth_path}.")
            sys.exit("safety validation failure: Authorization package missing.")
            
        with auth_path.open("r", encoding="utf-8") as f:
            auth_data = json.load(f)
            
        allowed = auth_data.get("decision", {}).get("pressure_execution_allowed_now", False)
        if not allowed:
            logger.warning("Safety validation failure: pressure_execution_allowed_now is False in authorization package.")
            if args.bypass_auth:
                logger.info("Bypassing safety authorization block as --bypass-auth is specified.")
            else:
                logger.error("Execution blocked by safety authorization package.")
                sys.exit("safety validation failure: pressure execution not authorized now.")
        else:
            logger.info("Safety validation check passed.")
            
    kwave_cmd = [
        python_exe,
        "run_kwave_command.py",
        "--script", "simulate_kwave_3d_focus.py",
        "--output-dir", str(step3_dir),
        "--preset", args.preset,
        "--python-exe", python_exe
    ]
    if args.execute:
        kwave_cmd.append("--execute")
        
    # Append simulate_kwave_3d_focus specific args
    kwave_cmd += [
        "--model", args.model,
        "--entry-plan", str(entry_plan_path),
        "--sim-time-us", str(best_cand["sim_time_us_estimate"]),
        "--aperture-mm", str(args.aperture_mm),
        "--radius-mm", str(args.radius_mm)
    ]
    
    run_command(kwave_cmd, "k-Wave focus simulation")
    
    # Check if pressure field exists
    pressure_file = step3_dir / "pressure_max_mpa.npz"
    if not pressure_file.exists():
        logger.warning("No acoustic pressure file found. Simulation was likely dry-run only.")
        logger.warning("Pennes bioheat solver simulation will be skipped.")
        print("SAFETY STATUS: N/A (Dry run check only)")
        return

    # ==========================================
    # Step 4: Pennes Bioheat Solver
    # ==========================================
    logger.info("==========================================")
    logger.info("Step 4: Running Pennes Bioheat Cooling Simulation")
    logger.info("==========================================")
    
    step4_dir = output_dir / "step4_pennes"
    step4_dir.mkdir(parents=True, exist_ok=True)
    
    pennes_cmd = [
        python_exe,
        "simulate_pennes_bioheat.py",
        "--pressure-dir", str(step3_dir),
        "--model", args.model,
        "--output-dir", str(step4_dir),
        "--gao-cooling-protocol"
    ]
    
    run_command(pennes_cmd, "Pennes bioheat cooling simulation")
    
    pennes_summary_path = step4_dir / "pennes_summary.json"
    if not pennes_summary_path.exists():
        logger.error("Pennes bioheat summary not generated.")
        raise FileNotFoundError("pennes_summary.json is missing.")
        
    with pennes_summary_path.open("r", encoding="utf-8") as f:
        p_summary = json.load(f)
        
    # Extract thermal dose safety fields
    safety = p_summary.get("thermal_dose_safety", {})
    brain_safety = safety.get("brain_safety", {})
    skull_safety = safety.get("skull_safety", {})
    overall_safe = safety.get("overall_safe", False)
    
    brain_temp = brain_safety.get("max_temperature_c", 0.0)
    brain_dose = max(brain_safety.get("max_cem43_min", 0.0), brain_safety.get("max_cem43_iso_min", 0.0))
    
    skull_temp = skull_safety.get("max_temperature_c", 0.0)
    skull_dose = max(skull_safety.get("max_cem43_min", 0.0), skull_safety.get("max_cem43_iso_min", 0.0))
    
    logger.info("==========================================")
    logger.info("Pennes Bioheat Safety Audit Results:")
    logger.info(f"  Soft Tissue (Brain) Peak Temp: {brain_temp:.4f} °C (Limit: <= 42.0 °C)")
    logger.info(f"  Soft Tissue (Brain) Peak Dose: {brain_dose:.4f} min (Limit: <= 2.0 min)")
    logger.info(f"  Bone (Skull) Peak Temp: {skull_temp:.4f} °C (Limit: <= 42.0 °C)")
    logger.info(f"  Bone (Skull) Peak Dose: {skull_dose:.4f} min (Limit: <= 16.0 min)")
    
    status_str = "SAFE" if overall_safe else "UNSAFE"
    logger.info(f"  Overall Safety Decision: {status_str}")
    logger.info("==========================================")
    
    print(f"SAFETY STATUS: {status_str}")

if __name__ == "__main__":
    main()
