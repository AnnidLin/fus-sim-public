from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mri_to_thermal_pipeline")

PROJECT_ROOT = Path(__file__).resolve().parent


def run_command(command: list[str], description: str) -> subprocess.CompletedProcess:
    logger.info(f"Running: {' '.join(command)}")
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        logger.error(f"Failed {description}:\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}")
        raise RuntimeError(f"{description} failed with exit code {result.returncode}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end tFUS Pipeline: MRI coordinates -> CT target -> Transducer Sweep -> Thermal Bioheat.")
    
    # 坐标配准与靶点映射参数
    parser.add_argument("--landmarks", default=None, help="Path to landmark pairs JSON (MRI to CT).")
    parser.add_argument("--matrix", default=None, help="Path to 4x4 matrix JSON.")
    parser.add_argument("--mri-point", required=True, help="MRI physical coordinate formatted as x,y,z in mm.")
    parser.add_argument("--dx-mm", type=float, default=1.0, help="CT grid size in mm.")
    
    # 扫查参数
    parser.add_argument("--model", required=True, help="Path to the CT acoustic model .npz file.")
    parser.add_argument("--sweep-axis", default="+x", choices=["+x", "-x", "+y", "-y", "+z", "-z"], help="Primary propagation axis.")
    parser.add_argument("--standoff-mm", type=float, default=8.0, help="Transducer standoff in mm.")
    parser.add_argument("--radius-mm", type=float, default=30.0, help="Transducer focal radius in mm.")
    parser.add_argument("--aperture-mm", type=float, default=25.0, help="Transducer active aperture in mm.")
    
    # 热学参数与外部声压
    parser.add_argument("--precomputed-pressure-dir", default=None, help="Optional pre-computed pressure directory to run BHTE cooling simulation end-to-end.")
    parser.add_argument("--output-dir", required=True, help="Output directory for all pipeline results.")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    python_exe = sys.executable

    # ==========================================
    # 步骤 1: 运行 MRI-CT 坐标映射
    # ==========================================
    logger.info("==========================================")
    logger.info("Step 1: Mapping MRI coordinate to CT Voxel Space")
    logger.info("==========================================")
    
    map_output = output_dir / "step1_mapped_point.json"
    map_cmd = [
        python_exe,
        "map_mri_to_ct_coordinates.py",
        "--mri-point", args.mri_point,
        "--dx-mm", str(args.dx_mm),
        "--output", str(map_output)
    ]
    if args.landmarks:
        map_cmd += ["--landmarks", args.landmarks]
    elif args.matrix:
        map_cmd += ["--matrix", args.matrix]
    else:
        # 如果未提供，使用单位矩阵 fallback
        fallback_matrix = output_dir / "fallback_identity_matrix.json"
        fallback_matrix.write_text(json.dumps({"affine_matrix": np.eye(4).tolist()}, indent=2), encoding="utf-8")
        map_cmd += ["--matrix", str(fallback_matrix)]
        logger.warning("No landmarks or matrix provided. Using identity matrix for mapping.")
        
    run_command(map_cmd, "MRI-CT coordinate mapping")
    
    # 读取转换得到的 CT voxel index
    with map_output.open("r", encoding="utf-8") as f:
        map_data = json.load(f)
    ct_voxel_ijk = map_data["ct_voxel_index_ijk"]
    ct_voxel_str = ",".join(str(v) for v in ct_voxel_ijk)
    logger.info(f"Target successfully mapped to CT voxel index: {ct_voxel_ijk}")

    # ==========================================
    # 步骤 2: 运行换能器偏角扫描
    # ==========================================
    logger.info("==========================================")
    logger.info("Step 2: Running Spherical Transducer Sweep")
    logger.info("==========================================")
    
    sweep_output_dir = output_dir / "step2_sweep_scan"
    sweep_cmd = [
        python_exe,
        "plan_transducer_sweep.py",
        "--model", args.model,
        "--target-index", ct_voxel_str,
        "--axis", args.sweep_axis,
        "--source-standoff-mm", str(args.standoff_mm),
        "--radius-mm", str(args.radius_mm),
        "--aperture-mm", str(args.aperture_mm),
        "--output-dir", str(sweep_output_dir)
    ]
    run_command(sweep_cmd, "Transducer sweep scan")
    
    # 读取扫描结果摘要
    sweep_summary_path = sweep_output_dir / "sweep_summary.json"
    with sweep_summary_path.open("r", encoding="utf-8") as f:
        sweep_data = json.load(f)
        
    valid_count = sweep_data["valid_count"]
    logger.info(f"Sweep completed. Found {valid_count} valid configurations.")
    
    best_candidate_id = None
    if valid_count > 0:
        best_cand = sweep_data["top_geometry_candidates"][0]
        best_candidate_id = best_cand["candidate_id"]
        logger.info(f"Recommended Top 1 Geometry Candidate: {best_candidate_id}")
        logger.info(f"  Angle: theta={best_cand['theta_deg']} deg, phi={best_cand['phi_deg']} deg")
        logger.info(f"  Heuristic transmission proxy score: {best_cand['heuristic_transmission_proxy']:.4f}")
        logger.info(f"  Collision safety: {best_cand.get('unsafe_source_points', 0)} unsafe points")
    else:
        logger.error("No valid transducer scan configurations found (all collided or out of bounds).")

    # ==========================================
    # 步骤 3: 提示 k-Wave 运行命令
    # ==========================================
    logger.info("==========================================")
    logger.info("Step 3: Proposed k-Wave Simulation Command")
    logger.info("==========================================")
    
    if best_candidate_id:
        kwave_out_dir = sweep_output_dir / best_candidate_id
        kwave_plan_path = kwave_out_dir / "entry_plan.json"
        
        # 如果是真实的 sweep_000 目录，会在 sweep 时自动写入 entry_plan.json 和 axial/coronal slice png。
        logger.info("To run the full-wave acoustic simulation for this best candidate, execute:")
        logger.info(f"  {python_exe} simulate_kwave_3d_focus.py --model {args.model} --entry-plan {kwave_plan_path} --output-dir {kwave_out_dir} --preset standard")
    else:
        logger.info("Simulation command generation skipped (no valid candidate).")

    # ==========================================
    # 步骤 4: 温升与热学 BHTE 模拟 (5s heating + 15s cooling)
    # ==========================================
    logger.info("==========================================")
    logger.info("Step 4: Running Pennes Bioheat Cooling Simulation")
    logger.info("==========================================")
    
    pressure_dir = args.precomputed_pressure_dir
    if not pressure_dir:
        # 如果没有指定预计算的声压目录，尝试看最优候选目录下是否存在 pressure_max_mpa.npz
        if best_candidate_id:
            candidate_p_dir = sweep_output_dir / best_candidate_id
            if (candidate_p_dir / "pressure_max_mpa.npz").exists():
                pressure_dir = str(candidate_p_dir)
                
    if pressure_dir:
        thermal_output_dir = output_dir / "step4_pennes_cooling"
        thermal_cmd = [
            python_exe,
            "simulate_pennes_bioheat.py",
            "--pressure-dir", pressure_dir,
            "--model", args.model,
            "--output-dir", str(thermal_output_dir),
            "--gao-cooling-protocol"
        ]
        run_command(thermal_cmd, "Pennes bioheat cooling simulation")
        
        # 读取热仿真结果
        with (thermal_output_dir / "pennes_summary.json").open("r", encoding="utf-8") as f:
            t_summary = json.load(f)
        logger.info("Pennes BHTE cooling simulation completed successfully!")
        logger.info(f"  Focal Peak Temperature Rise: {t_summary['max_temperature_rise_c']:.4f} °C")
        logger.info(f"  Focal peak coordinate: {t_summary['max_temperature_index_ijk']}")
        logger.info(f"  Result curve saved to: {thermal_output_dir / 'temperature_time_curve.png'}")
    else:
        logger.info("Acoustic pressure data not found. Skipping Pennes thermal simulation.")
        logger.info("Please run k-Wave simulation first, or specify --precomputed-pressure-dir with existing pressure data.")
        
    logger.info("==========================================")
    logger.info("Pipeline Execution Completed!")
    logger.info("==========================================")


if __name__ == "__main__":
    main()
