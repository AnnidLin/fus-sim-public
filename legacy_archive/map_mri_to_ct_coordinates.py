from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("map_mri_to_ct_coordinates")


def solve_rigid_transform_svd(P: np.ndarray, Q: np.ndarray) -> np.ndarray:
    """
    使用 SVD (Kabsch 算法) 求解刚体变换矩阵 M = [R | T; 0 1]
    使得 Q ≈ R * P + T
    P: N x 3 矩阵 (源空间坐标，例如 MRI)
    Q: N x 3 矩阵 (目标空间坐标，例如 CT)
    """
    if P.shape != Q.shape:
        raise ValueError(f"Point sets must have the same shape: P {P.shape} vs Q {Q.shape}")
    
    N = P.shape[0]
    if N < 3:
        raise ValueError("At least 3 point pairs are required for rigid registration.")

    # 1. 计算质心
    centroid_P = np.mean(P, axis=0)
    centroid_Q = np.mean(Q, axis=0)

    # 2. 去中心化
    P_centered = P - centroid_P
    Q_centered = Q - centroid_Q

    # 3. 计算协方差矩阵 H
    H = P_centered.T @ Q_centered

    # 4. SVD 分解
    U, S, Vt = np.linalg.svd(H)

    # 5. 计算旋转矩阵 R
    R = Vt.T @ U.T

    # 6. 处理镜像反射风险 (reflection check)
    d = np.linalg.det(R)
    if d < 0:
        raise ValueError("Chirality mismatch (reflection detected). Rigid transformation cannot contain a reflection.")

    # 7. 物理约束与正交性校验
    # 旋转矩阵必须是正交的 (R^T R = I) 且行列式等于 +1
    if not np.allclose(R.T @ R, np.eye(3), atol=1e-5):
        raise ValueError("Calculated rotation matrix is not orthogonal.")
    if not np.isclose(np.linalg.det(R), 1.0, atol=1e-4):
        raise ValueError(f"Calculated rotation matrix determinant {np.linalg.det(R)} is not +1.")

    # 8. 计算平移向量 T
    T = centroid_Q - R @ centroid_P

    # 9. 构建 4x4 齐次变换矩阵
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = T
    return M


def apply_affine_transform(point: np.ndarray, M: np.ndarray) -> np.ndarray:
    """
    应用 4x4 仿射变换矩阵到 3D 坐标上
    """
    pt_homogeneous = np.append(point, 1.0)
    transformed = M @ pt_homogeneous
    return transformed[:3]


def parse_coordinate(value: str) -> np.ndarray:
    try:
        parts = [float(v.strip()) for v in value.split(",") if v.strip()]
        if len(parts) != 3:
            raise ValueError()
        return np.array(parts)
    except Exception:
        raise argparse.ArgumentTypeError("Coordinate must be formatted as x,y,z")


def run(args: argparse.Namespace) -> None:
    M = None

    # 优先级 1: 如果提供了地标点对，则通过 SVD 计算配准矩阵
    if args.landmarks:
        landmarks_path = Path(args.landmarks)
        if not landmarks_path.exists():
            raise FileNotFoundError(f"Landmarks file not found: {landmarks_path}")
        
        logger.info(f"Loading landmarks from {landmarks_path}...")
        with landmarks_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            
        if "mri_landmarks" not in data or "ct_landmarks" not in data:
            raise ValueError("Landmarks JSON must contain 'mri_landmarks' and 'ct_landmarks'.")
            
        P = np.array(data["mri_landmarks"], dtype=float)
        Q = np.array(data["ct_landmarks"], dtype=float)
        
        # 计算最优配准变换矩阵
        M = solve_rigid_transform_svd(P, Q)
        logger.info("Rigid transform matrix successfully calculated via SVD (Kabsch algorithm).")
        
        # 打印残差均方根误差 (RMSE) 进行精度验证
        Q_est = (R := M[:3, :3]) @ P.T + M[:3, 3:4]
        rmse = np.sqrt(np.mean(np.sum((Q - Q_est.T) ** 2, axis=1)))
        logger.info(f"Landmarks registration RMSE: {rmse:.6f} mm")

        # 保存生成的矩阵
        if args.save_matrix:
            save_path = Path(args.save_matrix)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            matrix_data = {"affine_matrix": M.tolist(), "rmse_mm": float(rmse)}
            save_path.write_text(json.dumps(matrix_data, indent=2), encoding="utf-8")
            logger.info(f"Saved computed affine matrix to {save_path}")

    # 优先级 2: 如果提供了矩阵文件，则直接加载
    elif args.matrix:
        matrix_path = Path(args.matrix)
        if not matrix_path.exists():
            raise FileNotFoundError(f"Matrix file not found: {matrix_path}")
            
        logger.info(f"Loading 4x4 matrix from {matrix_path}...")
        with matrix_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            
        if "affine_matrix" not in data:
            raise ValueError("Matrix JSON must contain 'affine_matrix'.")
            
        M = np.array(data["affine_matrix"], dtype=float)
        if M.shape != (4, 4):
            raise ValueError(f"Matrix must be 4x4, but got shape {M.shape}")
            
        # 校验正交性
        R = M[:3, :3]
        if not np.allclose(R.T @ R, np.eye(3), atol=1e-3) or not np.isclose(np.linalg.det(R), 1.0, atol=1e-3):
            logger.warning("Loaded matrix rotation part is not perfectly orthogonal or determinant is not +1. Proceed with caution.")
    
    if M is None:
        raise ValueError("Either --matrix or --landmarks must be provided to perform registration mapping.")

    # 执行单点坐标变换
    if args.mri_point is not None:
        mri_pt = args.mri_point
        ct_phys_pt = apply_affine_transform(mri_pt, M)
        
        # 转换为 CT 空间的体素坐标 ijk
        # 以 mm 为单位，dx 为毫米步长
        dx_mm = args.dx_mm
        ct_voxel_ijk = np.rint(ct_phys_pt / dx_mm).astype(int)
        
        logger.info(f"MRI physical point [x, y, z]: {mri_pt.tolist()} mm")
        logger.info(f"Mapped CT physical point: {ct_phys_pt.tolist()} mm")
        logger.info(f"Mapped CT voxel index [i, j, k] (dx={dx_mm} mm): {ct_voxel_ijk.tolist()}")

        # 输出结果
        output_data = {
            "mri_point_mm": mri_pt.tolist(),
            "ct_physical_point_mm": ct_phys_pt.tolist(),
            "ct_voxel_index_ijk": ct_voxel_ijk.tolist(),
            "dx_mm": float(dx_mm),
            "affine_matrix": M.tolist()
        }
        
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
            logger.info(f"Written transformation output to {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Map coordinates from MRI to CT space.")
    parser.add_argument("--matrix", default=None, help="Path to 4x4 matrix JSON.")
    parser.add_argument("--landmarks", default=None, help="Path to landmark pairs JSON.")
    parser.add_argument("--mri-point", type=parse_coordinate, default=None, help="MRI physical coordinate x,y,z to map.")
    parser.add_argument("--dx-mm", type=float, default=1.0, help="Voxel size in millimeters for CT grid index calculation.")
    parser.add_argument("--output", default=None, help="Path to save mapping result JSON.")
    parser.add_argument("--save-matrix", default=None, help="Path to save calculated affine matrix if using landmarks.")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        logger.error(f"Fatal error: {exc}", exc_info=True)
        raise SystemExit(1)
