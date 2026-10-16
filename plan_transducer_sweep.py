from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# 必须在导入 kwave 前配置 matplotlib 以避免 headless 环境报错
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("plan_transducer_sweep")

# 引入 kwave 的 make_bowl 用于碰撞检查
try:
    from kwave.data import Vector
    from kwave.utils.mapgen import make_bowl
except ImportError:
    logger.error("kwave is not installed. Please run under python environment with kwave library.")

def odd_grid_points(length_m: float, dx_m: float) -> int:
    points = int(round(length_m / dx_m))
    return points if points % 2 == 1 else points + 1

PROJECT_ROOT = Path(__file__).resolve().parent

# 定义可视化颜色 (水/背景, 脑/软组织, 颅骨)
LABEL_COLORS = np.array(
    [
        [31, 43, 77],    # Label 0: Background/water (Dark blue)
        [66, 160, 121],  # Label 1: Soft tissue (Green)
        [218, 204, 137],  # Label 2: Skull bone (Yellow/Sand)
    ],
    dtype=np.uint8,
)

def parse_index(value: str) -> tuple[int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("index must be formatted as i,j,k")
    return tuple(parts)

def parse_range(value: str) -> tuple[float, float]:
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("range must be formatted as min,max")
    return tuple(parts)

def load_model(model_path: Path) -> tuple[np.ndarray, float, np.ndarray]:
    if not model_path.exists():
        raise FileNotFoundError(f"Missing acoustic model npz: {model_path}")
    data = np.load(model_path)
    required = {"labels", "dx_m", "target_index_ijk"}
    missing = required - set(data.files)
    if missing:
        raise ValueError(f"Model is missing required fields: {sorted(missing)}")
    
    labels = np.asarray(data["labels"], dtype=np.uint8)
    dx_m = float(np.asarray(data["dx_m"]).item())
    target = np.asarray(data["target_index_ijk"], dtype=np.int32)
    return labels, dx_m, target

def trace_beam_ray(labels: np.ndarray, dx_m: float, source: np.ndarray, target: np.ndarray) -> dict[str, object]:
    """
    使用射线步进法分析沿声轴从 source 到 target 的介质穿透情况。
    """
    direction = target - source
    distance_gp = np.linalg.norm(direction)
    unit_vec = direction / distance_gp if distance_gp > 0 else np.zeros(3)
    
    # 步进采样
    num_steps = int(np.ceil(distance_gp)) * 2
    steps = np.linspace(0, distance_gp, num_steps)
    
    entry_pt = None
    skull_enter_pt = None
    skull_exit_pt = None
    
    in_skull = False
    skull_voxels = set()
    
    for t in steps:
        pt = source + t * unit_vec
        ijk = np.rint(pt).astype(int)
        # 边界检查
        if np.any(ijk < 0) or np.any(ijk >= np.array(labels.shape)):
            continue
        label = labels[tuple(ijk)]
        
        # 记录第一个遇到的非背景像素 (即进入头部的入口)
        if label != 0 and entry_pt is None:
            entry_pt = ijk
            
        # 颅骨判定 (Label 2)
        if label == 2:
            skull_voxels.add(tuple(ijk))
            if not in_skull:
                in_skull = True
                if skull_enter_pt is None:
                    skull_enter_pt = ijk
        else:
            if in_skull:
                in_skull = False
                if skull_exit_pt is None:
                    skull_exit_pt = ijk
                    
    # 如果终点刚好在颅骨内，导致未捕获 exit_pt，则反向寻找最后的颅骨像素作为 exit
    if in_skull and skull_exit_pt is None:
        for t in reversed(steps):
            pt = source + t * unit_vec
            ijk = np.rint(pt).astype(int)
            if np.any(ijk < 0) or np.any(ijk >= np.array(labels.shape)):
                continue
            if labels[tuple(ijk)] == 2:
                skull_exit_pt = ijk
                break
                
    has_skull_crossing = len(skull_voxels) > 0
    if has_skull_crossing and skull_enter_pt is not None and skull_exit_pt is not None:
        skull_path_length = np.linalg.norm(skull_exit_pt - skull_enter_pt) * dx_m * 1e3
    else:
        skull_path_length = len(skull_voxels) * dx_m * 1e3 if has_skull_crossing else 0.0
        
    return {
        "has_skull_crossing": bool(has_skull_crossing),
        "entry_index_ijk": None if entry_pt is None else [int(v) for v in entry_pt],
        "skull_enter_index_ijk": None if skull_enter_pt is None else [int(v) for v in skull_enter_pt],
        "skull_exit_index_ijk": None if skull_exit_pt is None else [int(v) for v in skull_exit_pt],
        "skull_path_length_mm": float(skull_path_length),
        "source_to_target_distance_mm": float(distance_gp * dx_m * 1e3),
        "source_to_entry_distance_mm": float(np.linalg.norm(entry_pt - source) * dx_m * 1e3) if entry_pt is not None else 0.0
    }

def check_collision_kwave(
    labels: np.ndarray,
    dx_m: float,
    source_center: np.ndarray,
    target: np.ndarray,
    radius_gp: int,
    diameter_gp: int
) -> tuple[bool, dict[str, int]]:
    """
    在三维网格上为给定的 source 和 target 构建换能器碗的几何掩膜，并统计重叠体素标签以检测碰撞。
    """
    # check shape constraints
    shape = labels.shape
    # 顶点的 1-based 索引，用于 make_bowl
    bowl_one = (source_center + 1).astype(int)
    target_one = (target + 1).astype(int)
    
    # 限制越界
    if np.any(source_center < 0) or np.any(source_center >= np.array(shape)):
        return True, {"out_of_bounds": 1}
        
    try:
        grid_size = Vector(list(shape))
        source_mask = make_bowl(
            grid_size,
            Vector(bowl_one.tolist()),
            radius_gp,
            diameter_gp,
            Vector(target_one.tolist()),
            binary=True,
            remove_overlap=True,
        ).astype(bool)
    except Exception as exc:
        logger.warning(f"make_bowl failed at source {source_center.tolist()}: {exc}")
        return True, {"make_bowl_error": 1}
        
    if not np.any(source_mask):
        return True, {"empty_mask": 1}
        
    # 提取掩膜内体素的标签并统计
    masked_labels = labels[source_mask]
    unique, counts = np.unique(masked_labels, return_counts=True)
    label_counts = {str(k): int(v) for k, v in zip(unique, counts)}
    
    # 只要包含了非 0（水/背景）体素，即说明换能器物理表面撞到了头皮(1)或颅骨(2)
    unsafe_points = label_counts.get("1", 0) + label_counts.get("2", 0)
    has_collision = unsafe_points > 0
    
    return has_collision, label_counts

def label_image(slice_2d: np.ndarray) -> Image.Image:
    return Image.fromarray(LABEL_COLORS[np.clip(slice_2d, 0, len(LABEL_COLORS) - 1)], mode="RGB")

def draw_slice_with_beam(
    image: Image.Image,
    title: str,
    source: np.ndarray,
    entry: np.ndarray | None,
    target: np.ndarray,
    axis_idx_1: int,
    axis_idx_2: int
) -> Image.Image:
    """
    在指定的 2D 切片图上，缩放并画出声轴射线以及相关焦点标注。
    """
    scale = max(2, min(5, 780 // max(image.width, image.height)))
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (image.width, image.height + 34), "white")
    canvas.paste(image, (0, 34))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 10), title, fill=(0, 0, 0))
    
    # 转换坐标 (x_pixel = val * scale, y_pixel = val * scale + 34)
    def to_pixel(pt):
        return int(pt[axis_idx_1]) * scale, int(pt[axis_idx_2]) * scale + 34
        
    s_x, s_y = to_pixel(source)
    t_x, t_y = to_pixel(target)
    
    # 绘制射线
    draw.line((s_x, s_y, t_x, t_y), fill=(255, 255, 255), width=2)
    
    # 标注点 (source, entry, target)
    markers = [
        (s_x, s_y, (255, 255, 255), "source"),
        (t_x, t_y, (255, 0, 0), "target")
    ]
    if entry is not None:
        e_x, e_y = to_pixel(entry)
        markers.append((e_x, e_y, (255, 160, 0), "entry"))
        
    for x, y, color, label in markers:
        draw.line((x - 8, y, x + 8, y), fill=color, width=2)
        draw.line((x, y - 8, x, y + 8), fill=color, width=2)
        draw.text((x + 10, y - 8), label, fill=color)
        
    return canvas

def generate_spherical_candidates(
    labels: np.ndarray,
    dx_m: float,
    target: np.ndarray,
    radius_gp: int,
    diameter_gp: int,
    source_standoff_gp: int,
    theta_step: float,
    theta_max: float,
    phi_step: float,
    phi_range: tuple[float, float],
    axis: str = "+x"
) -> list[dict[str, object]]:
    """
    基于球面偏角坐标生成候选点，并执行碰撞检查和射线分析。
    """
    candidates = []
    
    # 极角 theta 从 0 到 theta_max
    theta_vals = np.arange(0, theta_max + 1e-5, theta_step)
    # 方位角 phi 在指定范围内
    phi_vals = np.arange(phi_range[0], phi_range[1] + 1e-5, phi_step)
    
    logger.info(f"Generating spherical candidates: theta_steps={len(theta_vals)}, phi_steps={len(phi_vals)}, axis={axis}")
    
    valid_index = 0
    for theta_deg in theta_vals:
        theta_rad = np.radians(theta_deg)
        # 对 theta = 0，phi 重复无意义，只扫描一次
        current_phi_vals = [0.0] if theta_deg == 0.0 else phi_vals
        
        for phi_deg in current_phi_vals:
            phi_rad = np.radians(phi_deg)
            
            # 计算朝向靶点的入射单位矢量 (以极角theta相对于主轴进行球面投影)
            ux = np.cos(theta_rad)
            uy = np.sin(theta_rad) * np.cos(phi_rad)
            uz = np.sin(theta_rad) * np.sin(phi_rad)
            
            if axis == "+x":
                beam_unit_vector = np.array([ux, uy, uz])
            elif axis == "-x":
                beam_unit_vector = np.array([-ux, uy, uz])
            elif axis == "+y":
                beam_unit_vector = np.array([uy, ux, uz])
            elif axis == "-y":
                beam_unit_vector = np.array([uy, -ux, uz])
            elif axis == "+z":
                beam_unit_vector = np.array([uy, uz, ux])
            elif axis == "-z":
                beam_unit_vector = np.array([uy, uz, -ux])
            else:
                beam_unit_vector = np.array([ux, uy, uz])
            
            # 几何射线分析：为了确定换能器和头骨的最短 standoff 距离，我们先沿声轴射线寻找颅骨入口点
            # 模拟一条足够长的射线（从靶点反向出发，其长度应大于网格对角线，以确保起点在头部外面）
            max_dist = float(np.linalg.norm(labels.shape))
            test_source = target - np.rint(max_dist * beam_unit_vector).astype(int)
            ray_info = trace_beam_ray(labels, dx_m, test_source, target)
            
            if not ray_info["has_skull_crossing"] or ray_info["entry_index_ijk"] is None:
                # 若无骨交叉，属于非法或无效穿颅路径
                continue
                
            entry_pt = np.array(ray_info["entry_index_ijk"])
            
            # 物理上，换能器顶点 (source center) 与颅骨入口 (entry) 必须保持给定的 source_standoff 距离
            # 因此，碗中心位置应从 entry 点往反方向外推 standoff 距离
            source_center = entry_pt - np.rint(source_standoff_gp * beam_unit_vector).astype(int)
            
            # 边界及碰撞干涉检查
            has_collision, label_counts = check_collision_kwave(
                labels, dx_m, source_center, target, radius_gp, diameter_gp
            )
            
            # 射线指标重新以真实的 source_center 计算
            ray_metrics = trace_beam_ray(labels, dx_m, source_center, target)
            
            status = "rejected_collision" if has_collision else "valid"
            
            # 计算局部法线与入射夹角
            incidence_angle_deg = 0.0
            heuristic_proxy = 0.0
            if status == "valid" and entry_pt is not None:
                x_center = np.array(labels.shape) / 2.0
                n_skull = entry_pt - x_center
                n_skull_norm = np.linalg.norm(n_skull)
                if n_skull_norm > 0:
                    n_skull = n_skull / n_skull_norm
                else:
                    n_skull = -beam_unit_vector # 默认与入射反方向
                
                # 入射偏角余弦值
                cos_theta_inc = np.dot(beam_unit_vector, -n_skull)
                if cos_theta_inc > 0.0:
                    cos_theta_inc = np.clip(cos_theta_inc, 0.0, 1.0)
                    incidence_angle_deg = np.degrees(np.arccos(cos_theta_inc))
                    if ray_metrics["has_skull_crossing"]:
                        # alpha_eff = 0.1 / mm
                        heuristic_proxy = np.exp(-0.1 * ray_metrics["skull_path_length_mm"]) * cos_theta_inc
                else:
                    cos_theta_inc = 0.0
                    incidence_angle_deg = 90.0
                    heuristic_proxy = 0.0

            # 计算换能器在头部网格中占用的体素总量、不同材料的数量与碰撞比例
            s_label0 = label_counts.get("0", 0)
            s_label1 = label_counts.get("1", 0)
            s_label2 = label_counts.get("2", 0)
            s_total = sum(label_counts.values())
            s_unsafe_points = s_label1 + s_label2
            s_unsafe_fraction = float(s_unsafe_points / s_total) if s_total > 0 else 0.0

            candidates.append({
                "candidate_id": f"sweep_{valid_index:03d}" if status == "valid" else "rejected",
                "theta_deg": float(theta_deg),
                "phi_deg": float(phi_deg),
                "beam_unit_vector": beam_unit_vector.tolist(),
                "source_center_index_ijk": [int(v) for v in source_center],
                "target_index_ijk": [int(v) for v in target],
                "entry_index_ijk": [int(v) for v in entry_pt],
                "status": status,
                "has_collision": bool(has_collision),
                "source_points": int(s_total),
                "source_label_0_count": int(s_label0),
                "source_label_1_count": int(s_label1),
                "source_label_2_count": int(s_label2),
                "unsafe_source_points": int(s_unsafe_points),
                "unsafe_source_fraction": float(s_unsafe_fraction),
                "source_mask_label_counts": label_counts,
                "has_skull_crossing": ray_metrics["has_skull_crossing"],
                "skull_path_length_mm": ray_metrics["skull_path_length_mm"],
                "source_to_target_distance_mm": ray_metrics["source_to_target_distance_mm"],
                "source_to_entry_distance_mm": ray_metrics["source_to_entry_distance_mm"],
                "incidence_angle_deg": float(incidence_angle_deg),
                "heuristic_transmission_proxy": float(heuristic_proxy),
                "heuristic_rank": "",
                "recommended_for_kwave": False,
                "voxel_count": 0, # 会在后续 quick_crop 中计算
            })
            if status == "valid":
                valid_index += 1
                
    return candidates

def estimate_quick_crop(
    cand: dict[str, object],
    model_shape: tuple[int, int, int],
    dx_m: float,
    sim_time_us: float,
    pml_size: int = 8
) -> dict[str, object]:
    """
    计算剪裁包围盒和离散网格点数。
    """
    target = np.array(cand["target_index_ijk"], dtype=int)
    source = np.array(cand["source_center_index_ijk"], dtype=int)
    
    # 增加富余量以保障碗源和焦域完整包围
    lateral_margin = max(8, int(round(17.0 * 1e-3 / dx_m)))  # 17mm 侧向半宽度
    post_target_margin = max(4, int(round(8.0 * 1e-3 / dx_m))) # 8mm 焦后边界
    
    anchor_min = np.minimum(target, source)
    anchor_max = np.maximum(target, source)
    
    x0 = max(0, int(anchor_min[0]) - pml_size - 4)
    x1 = min(model_shape[0], int(anchor_max[0]) + post_target_margin)
    y0 = max(0, int(anchor_min[1]) - lateral_margin)
    y1 = min(model_shape[1], int(anchor_max[1]) + lateral_margin + 1)
    z0 = max(0, int(anchor_min[2]) - lateral_margin)
    z1 = min(model_shape[2], int(anchor_max[2]) + lateral_margin + 1)
    
    crop_shape = [int(x1 - x0), int(y1 - y0), int(z1 - z0)]
    voxel_count = int(np.prod(crop_shape))
    nt_estimate = int(np.ceil(sim_time_us * 1e-6 / (0.20 * dx_m / 2800.0)))
    
    return {
        "crop_origin_ijk": [int(x0), int(y0), int(z0)],
        "crop_shape": crop_shape,
        "voxel_count": voxel_count,
        "nt_estimate": nt_estimate,
        "sim_time_us_estimate": float(sim_time_us)
    }

def rank_geometry(valid_cands: list[dict[str, object]]) -> list[dict[str, object]]:
    """
    根据启发式透射率代理指标给候选方案排序：proxy 值越大越优。
    """
    # 排序优先级：heuristic_transmission_proxy 降序 -> 骨路径长度升序
    sorted_list = sorted(
        valid_cands,
        key=lambda row: (
            -float(row["heuristic_transmission_proxy"]),
            float(row["skull_path_length_mm"])
        )
    )
    for rank, row in enumerate(sorted_list, start=1):
        row["heuristic_rank"] = rank
        row["recommended_for_kwave"] = rank <= 3
    return sorted_list

def run_fast_candidate(
    python_exe: Path,
    model_path: Path,
    cand: dict[str, object],
    timeout_s: int
) -> dict[str, object]:
    """
    调用模拟器 simulate_kwave_3d_focus.py 执行极速仿真。
    """
    output_dir = PROJECT_ROOT / "outputs" / "sweep_runs" / cand["candidate_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成临时的 entry_plan.json
    plan_data = {
        "description": "Spherical sweep candidate plan",
        "entry_direction": f"sweep_theta_{cand['theta_deg']}_phi_{cand['phi_deg']}",
        "entry_offset_mm": [0.0, 0.0],
        "entry_offset_grid_points_yz": [0, 0],
        "beam_axis": (np.array(cand["target_index_ijk"]) - np.array(cand["source_center_index_ijk"])).tolist(),
        "beam_unit_vector": cand["beam_unit_vector"],
        "target_index_ijk": cand["target_index_ijk"],
        "entry_index_ijk": cand["entry_index_ijk"],
        "source_center_index_ijk": cand["source_center_index_ijk"],
        "has_skull_crossing": cand["has_skull_crossing"],
        "source_standoff_mm": cand["source_to_entry_distance_mm"],
        "source_to_target_distance_mm": cand["source_to_target_distance_mm"],
        "skull_path_length_mm": cand["skull_path_length_mm"]
    }
    plan_path = output_dir / "entry_plan.json"
    plan_path.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")
    
    # 构造 k-wave 命令参数
    command = [
        str(python_exe),
        "simulate_kwave_3d_focus.py",
        "--model",
        str(model_path),
        "--entry-plan",
        str(plan_path),
        "--output-dir",
        str(output_dir),
        "--sim-time-us",
        str(cand["sim_time_us_estimate"]),
        "--quick-lateral-mm",
        "17.0",
        "--quick-post-target-mm",
        "8.0"
    ]
    
    logger.info(f"Executing fast simulation for {cand['candidate_id']}...")
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, timeout=timeout_s)
    
    row = dict(cand)
    row["kwave_output_dir"] = str(output_dir)
    row["returncode"] = result.returncode
    if result.returncode != 0:
        row["status"] = "kwave_failed"
        row["error"] = result.stderr[-1000:]
        return row
        
    # 读取物理场结果
    metrics_path = output_dir / "focus_metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        row.update({
            "status": "kwave_ok",
            "global_peak_mpa": metrics.get("global_peak_mpa"),
            "effective_peak_mpa": metrics.get("effective_peak_mpa"),
            "effective_peak_to_target_distance_mm": metrics.get("effective_peak_to_target_distance_mm"),
            "target_pressure_mpa": metrics.get("target_pressure_mpa"),
            "target_window_peak_mpa": metrics.get("target_window_peak_mpa")
        })
    else:
        row["status"] = "kwave_no_metrics"
        
    return row

def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    labels, dx_m, model_target = load_model(Path(args.model))
    target = np.array(args.target_index if args.target_index is not None else model_target, dtype=np.int32)
    
    # 尺寸网格单位转换
    radius_gp = int(round(args.radius_mm * 1e-3 / dx_m))
    diameter_gp = odd_grid_points(args.aperture_mm * 1e-3, dx_m)
    source_standoff_gp = max(1, int(round(args.source_standoff_mm * 1e-3 / dx_m)))
    
    logger.info(f"Target target_index_ijk={target.tolist()}, dx={dx_m*1e3:.3f}mm")
    logger.info(f"Transducer: radius_gp={radius_gp}, diameter_gp={diameter_gp}, standoff_gp={source_standoff_gp}")
    
    # 生成并筛选偏角候选点
    candidates = generate_spherical_candidates(
        labels=labels,
        dx_m=dx_m,
        target=target,
        radius_gp=radius_gp,
        diameter_gp=diameter_gp,
        source_standoff_gp=source_standoff_gp,
        theta_step=args.theta_step,
        theta_max=args.theta_max,
        phi_step=args.phi_step,
        phi_range=args.phi_range,
        axis=args.axis
    )
    
    # 分流有效与重叠/无效的候选点
    valid_cands = [c for c in candidates if c["status"] == "valid"]
    rejected_cands = [c for c in candidates if c["status"] != "valid"]
    
    logger.info(f"Calculated: total_candidates={len(candidates)}, valid={len(valid_cands)}, rejected={len(rejected_cands)}")
    
    if not valid_cands:
        logger.error("No valid candidate path generated (all collided or out of bounds).")
        return
        
    # 计算仿真所需剪裁网格与时间估算
    # 以声速 1540 计算回波声时
    for c in candidates:
        arrival_time_us = float(c["source_to_target_distance_mm"]) * 1e-3 / 1540.0 * 1e6
        sim_time_us = min(65.0, max(45.0, arrival_time_us + 8.0))
        estimates = estimate_quick_crop(c, labels.shape, dx_m, sim_time_us)
        c.update(estimates)
        
    # 几何排序
    ranked_valid = rank_geometry(valid_cands)
    
    # 可视化前 3 名几何规划路径切片
    for i, cand in enumerate(ranked_valid[:3]):
        cand_id = cand["candidate_id"]
        source = np.array(cand["source_center_index_ijk"])
        entry = np.array(cand["entry_index_ijk"])
        
        cand_dir = output_dir / cand_id
        cand_dir.mkdir(parents=True, exist_ok=True)
        
        # 绘制 axial 切片
        axial_img = label_image(labels[:, :, target[2]].T)
        draw_slice_with_beam(axial_img, f"Axial - {cand_id} (theta={cand['theta_deg']} phi={cand['phi_deg']})", 
                             source, entry, target, 0, 1).save(cand_dir / "layout_axial.png")
                             
        # 绘制 coronal 切片
        coronal_img = label_image(labels[:, target[1], :].T)
        draw_slice_with_beam(coronal_img, f"Coronal - {cand_id} (theta={cand['theta_deg']} phi={cand['phi_deg']})", 
                             source, entry, target, 0, 2).save(cand_dir / "layout_coronal.png")
                             
    # 保存 CSV 文件
    csv_header = [
        "candidate_id", "theta_deg", "phi_deg", "status", "has_collision",
        "source_points", "source_label_0_count", "source_label_1_count", "source_label_2_count",
        "unsafe_source_points", "unsafe_source_fraction",
        "skull_path_length_mm", "incidence_angle_deg", "source_to_target_distance_mm",
        "source_to_entry_distance_mm", "heuristic_transmission_proxy", "heuristic_rank",
        "recommended_for_kwave", "voxel_count", "nt_estimate", "sim_time_us_estimate"
    ]
    
    def save_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=csv_header, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
                
    save_csv(output_dir / "candidates_valid.csv", ranked_valid)
    save_csv(output_dir / "candidates_rejected.csv", rejected_cands)
    
    # 跑快速仿真测试
    final_rows = []
    if args.run_fast:
        max_runs = args.max_fast_runs if args.max_fast_runs is not None else 3
        test_subset = ranked_valid[:max_runs]
        logger.info(f"Running fast k-Wave sweep for top {len(test_subset)} geometry candidate(s)...")
        for c in test_subset:
            try:
                res = run_fast_candidate(Path(args.python_exe), Path(args.model), c, args.fast_timeout_s)
                final_rows.append(res)
            except Exception as exc:
                logger.error(f"Failed simulating candidate {c['candidate_id']}: {exc}")
                res = dict(c)
                res["status"] = "kwave_exception"
                res["error"] = str(exc)
                final_rows.append(res)
                
        # 按照声场压强重新排序
        ok_rows = [r for r in final_rows if r.get("status") == "kwave_ok"]
        other_rows = [r for r in final_rows if r.get("status") != "kwave_ok"]
        ok_rows.sort(key=lambda r: -float(r.get("target_window_peak_mpa", 0.0)))
        
        # 标注排序
        for rank, r in enumerate(ok_rows, start=1):
            r["acoustic_rank"] = rank
            
        final_rows = ok_rows + other_rows
        
        # 保存声学排序结果
        extended_header = csv_header + ["status", "global_peak_mpa", "effective_peak_mpa", 
                                        "effective_peak_to_target_distance_mm", "target_pressure_mpa", 
                                        "target_window_peak_mpa", "acoustic_rank", "error"]
        with open(output_dir / "sweep_simulation_results.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=extended_header, extrasaction="ignore")
            writer.writeheader()
            for r in final_rows:
                writer.writerow(r)
                
        # 输出最优方案摘要
        if ok_rows:
            best_run = ok_rows[0]
            logger.info(f"===========================================================")
            logger.info(f"🎉 Sweep search completed! Best acoustic candidate:")
            logger.info(f"ID: {best_run['candidate_id']}")
            logger.info(f"Angle: theta={best_run['theta_deg']} deg, phi={best_run['phi_deg']} deg")
            logger.info(f"Acoustic Focus Pressure in Target Window: {best_run['target_window_peak_mpa']:.4f} MPa")
            logger.info(f"Target Pressure: {best_run['target_pressure_mpa']:.4f} MPa")
            logger.info(f"Output directory: {best_run['kwave_output_dir']}")
            logger.info(f"===========================================================")
            
    # 输出汇总 JSON
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
    if args.run_fast and ok_rows:
        summary_data["best_acoustic_candidate"] = {
            "candidate_id": ok_rows[0]["candidate_id"],
            "theta_deg": ok_rows[0]["theta_deg"],
            "phi_deg": ok_rows[0]["phi_deg"],
            "target_window_peak_mpa": ok_rows[0]["target_window_peak_mpa"],
            "kwave_output_dir": ok_rows[0]["kwave_output_dir"]
        }
    (output_dir / "sweep_summary.json").write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Written sweep summary to {output_dir / 'sweep_summary.json'}")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spherical sweep planner for tFUS single-element transducer.")
    parser.add_argument(
        "--model",
        default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d" / "acoustic_model_3d.npz"),
        help="Path to the CT acoustic model .npz file."
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_sweep_scan_079"),
        help="Output directory for sweep plans."
    )
    parser.add_argument("--target-index", type=parse_index, default=None, help="Target voxel index (i,j,k).")
    parser.add_argument("--source-standoff-mm", type=float, default=8.0, help="Minimum standoff coupling distance in mm.")
    parser.add_argument("--radius-mm", type=float, default=30.0, help="Transducer focal radius in mm.")
    parser.add_argument("--aperture-mm", type=float, default=25.0, help="Transducer active aperture in mm.")
    
    # 球面扫描角分辨率
    parser.add_argument("--theta-step", type=float, default=5.0, help="Tilt angle step in degrees.")
    parser.add_argument("--theta-max", type=float, default=40.0, help="Maximum tilt angle in degrees.")
    parser.add_argument("--phi-step", type=float, default=15.0, help="Azimuth rotation step in degrees.")
    parser.add_argument("--phi-range", type=parse_range, default=(-30.0, 30.0), help="Azimuth rotation range in degrees formatted as min,max.")
    parser.add_argument(
        "--axis",
        choices=["+x", "-x", "+y", "-y", "+z", "-z"],
        default="+x",
        help="Primary wave propagation axis (direction of sound vector projection at theta=0)."
    )
    
    # 模拟检验参数
    parser.add_argument("--run-fast", action="store_true", help="Run fast k-Wave simulations for top candidates.")
    parser.add_argument("--max-fast-runs", type=int, default=3, help="Maximum number of fast sweep simulations.")
    parser.add_argument("--fast-timeout-s", type=int, default=900, help="Timeout in seconds for each simulation.")
    parser.add_argument(
        "--python-exe",
        default=str(PROJECT_ROOT.parent / "python-envs" / "kwave312" / "Scripts" / "python.exe"),
        help="Python executable inside virtual environment."
    )
    return parser.parse_args()

if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        logger.error(f"Fatal error during sweep execution: {exc}", exc_info=True)
        raise SystemExit(1)
