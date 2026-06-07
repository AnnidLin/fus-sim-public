from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def read_summary(model_dir: Path) -> dict[str, Any]:
    path = model_dir / "summary.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing CT model summary: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_target_label(model_dir: Path, target: list[int] | None) -> int | None:
    model_path = model_dir / "acoustic_model_3d.npz"
    if not model_path.exists() or target is None:
        return None
    data = np.load(model_path)
    labels = np.asarray(data["labels"], dtype=np.uint8)
    index = np.asarray(target, dtype=int)
    if index.shape != (3,) or np.any(index < 0) or np.any(index >= np.asarray(labels.shape)):
        return None
    return int(labels[tuple(index)])


def compact_model(model_dir: Path) -> dict[str, Any]:
    summary = read_summary(model_dir)
    grid_shape = summary.get("grid_shape", [])
    voxel_total = int(np.prod(grid_shape)) if grid_shape else None
    counts = summary.get("voxel_counts", {})
    skull_count = int(counts.get("skull_bone", 0))
    target = summary.get("target_index_ijk")
    return {
        "model_dir": str(model_dir),
        "mapping_profile": summary.get("mapping_profile"),
        "thresholds_hu": summary.get("thresholds_hu", {}),
        "grid_shape": grid_shape,
        "dx_m": summary.get("dx_m"),
        "target_index_ijk": target,
        "target_label": read_target_label(model_dir, target),
        "voxel_counts": counts,
        "skull_voxel_fraction": None if not voxel_total else skull_count / voxel_total,
        "hu_range": summary.get("hu_range"),
        "sound_speed_range_m_s": summary.get("sound_speed_range_m_s"),
        "density_range_kg_m3": summary.get("density_range_kg_m3"),
        "alpha_range_db_mhz_cm": summary.get("alpha_range_db_mhz_cm"),
    }


def build_comparison(baseline_dir: Path, candidate_dir: Path, extra_dir: Path | None) -> dict[str, Any]:
    models = {
        "baseline": compact_model(baseline_dir),
        "candidate": compact_model(candidate_dir),
    }
    if extra_dir is not None:
        models["extra"] = compact_model(extra_dir)
    return {
        "description": "CT acoustic mapping profile comparison. This compares model material maps only; it does not run k-Wave.",
        "models": models,
        "interpretation": [
            "Profile-based HU300 should reproduce the old 300 HU baseline material map within normal rebuild/resampling consistency.",
            "Profile-based HU250 is a sensitivity candidate and should not automatically replace HU300.",
            "This report compares segmentation/material-map differences, not acoustic focusing quality.",
        ],
    }


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def write_markdown(path: Path, comparison: dict[str, Any]) -> None:
    lines = [
        "# CT-HU 声学映射 Profile 对比报告",
        "",
        "## 结论边界",
        "",
        "- 本报告只比较 CT 分割与材料映射，不运行 k-Wave。",
        "- `simple_hu300` 用于复现当前 300 HU baseline。",
        "- `simple_hu250` 仅用于阈值敏感性对照，不自动替代当前 best。",
        "",
        "## 模型对比",
        "",
        "| 模型 | profile | bone threshold HU | grid shape | target label | skull fraction | sound speed range | alpha range |",
        "|---|---|---:|---|---:|---:|---|---|",
    ]
    for key, model in comparison["models"].items():
        profile = model.get("mapping_profile") or {}
        profile_id = profile.get("profile_id") if isinstance(profile, dict) else None
        thresholds = model.get("thresholds_hu") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    key,
                    fmt(profile_id),
                    fmt(thresholds.get("bone_gte")),
                    fmt(model.get("grid_shape")),
                    fmt(model.get("target_label")),
                    fmt(model.get("skull_voxel_fraction")),
                    fmt(model.get("sound_speed_range_m_s")),
                    fmt(model.get("alpha_range_db_mhz_cm")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## 解释", ""])
    for item in comparison["interpretation"]:
        lines.append(f"- {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison = build_comparison(
        Path(args.baseline_dir),
        Path(args.candidate_dir),
        None if args.extra_dir is None else Path(args.extra_dir),
    )
    (output_dir / "mapping_profile_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(output_dir / "mapping_profile_comparison.md", comparison)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare CT acoustic mapping profile model outputs.")
    parser.add_argument("--baseline-dir", required=True)
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--extra-dir", default=None)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
