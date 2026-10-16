from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("/", "\\")
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8-sig")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_model(model_dir: Path) -> dict[str, Any]:
    npz_path = model_dir / "acoustic_model_3d.npz"
    summary_path = model_dir / "summary.json"
    if not npz_path.exists():
        raise FileNotFoundError(f"Missing model: {npz_path}")
    with np.load(npz_path) as data:
        arrays = {key: data[key] for key in data.files}
    summary = read_json(summary_path) if summary_path.exists() else {}
    return {"dir": model_dir, "arrays": arrays, "summary": summary}


def sample_indices(start: np.ndarray, end: np.ndarray, step_mm: float, dx_m: float) -> tuple[np.ndarray, np.ndarray]:
    distance_vox = float(np.linalg.norm(end - start))
    distance_mm = distance_vox * dx_m * 1000.0
    n = max(2, int(np.ceil(distance_mm / step_mm)) + 1)
    t = np.linspace(0.0, 1.0, n)
    points = start[None, :] + (end - start)[None, :] * t[:, None]
    indices = np.rint(points).astype(int)
    return t, indices


def dedupe_indices(indices: np.ndarray) -> np.ndarray:
    seen: set[tuple[int, int, int]] = set()
    out: list[list[int]] = []
    for idx in indices:
        key = tuple(int(x) for x in idx)
        if key in seen:
            continue
        seen.add(key)
        out.append([int(x) for x in idx])
    return np.array(out, dtype=int)


def stats(values: list[float]) -> dict[str, float | int | None]:
    arr = np.array(values, dtype=float)
    if arr.size == 0:
        return {"count": 0, "min": None, "median": None, "max": None, "mean": None}
    return {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "median": float(np.median(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
    }


def summarize_rows(rows: list[dict[str, Any]], model_name: str) -> dict[str, Any]:
    model_rows = [row for row in rows if row["model"] == model_name]
    skull_rows = [row for row in model_rows if int(row["label"]) == 2]
    return {
        "total_samples": len(model_rows),
        "label_counts": {
            str(label): sum(1 for row in model_rows if int(row["label"]) == label)
            for label in sorted({int(row["label"]) for row in model_rows})
        },
        "skull_samples": len(skull_rows),
        "skull_distance_from_source_mm_min": min((row["distance_from_source_mm"] for row in skull_rows), default=None),
        "skull_distance_from_source_mm_max": max((row["distance_from_source_mm"] for row in skull_rows), default=None),
        "skull_distance_from_entry_mm_min": min((row["distance_from_entry_mm"] for row in skull_rows), default=None),
        "skull_distance_from_entry_mm_max": max((row["distance_from_entry_mm"] for row in skull_rows), default=None),
        "hu_all": stats([row["hu"] for row in model_rows]),
        "hu_skull": stats([row["hu"] for row in skull_rows]),
        "sound_speed_all": stats([row["sound_speed_m_s"] for row in model_rows]),
        "sound_speed_skull": stats([row["sound_speed_m_s"] for row in skull_rows]),
        "density_all": stats([row["density_kg_m3"] for row in model_rows]),
        "density_skull": stats([row["density_kg_m3"] for row in skull_rows]),
        "alpha_all": stats([row["alpha_db_mhz_cm"] for row in model_rows]),
        "alpha_skull": stats([row["alpha_db_mhz_cm"] for row in skull_rows]),
    }


def make_report(data: dict[str, Any]) -> str:
    lines = []
    for name, summary in data["model_summaries"].items():
        lines.append(
            f"| {name} | {summary['skull_samples']} | "
            f"{summary['sound_speed_skull']['min']} - {summary['sound_speed_skull']['max']} | "
            f"{summary['density_skull']['min']} - {summary['density_skull']['max']} | "
            f"{summary['alpha_skull']['min']} - {summary['alpha_skull']['max']} |"
        )
    table = "\n".join(lines)
    return f"""# 079 Candidate 006 Entry Path Property Profile

## 结论

本报告只比较 source-center 到 target 直线路径上的材料属性，不是声传播仿真。

entry plan：`{data['entry_plan_path']}`

source：`{data['source_center_index_ijk']}`  
entry：`{data['entry_index_ijk']}`  
target：`{data['target_index_ijk']}`  
采样点数：`{data['sample_count']}`

## Skull path 属性范围

| model | skull samples | skull sound speed m/s | skull density kg/m3 | skull alpha dB/MHz/cm |
| --- | ---: | --- | --- | --- |
{table}

## 解释边界

- path profile 只能说明材料属性，不代表 pressure transmission。
- 最近邻直线采样可能低估薄结构复杂性。
- draft profile 的 attenuation 仍需单位审计。
- 本阶段没有运行 k-Wave。

## 下一步

如果继续，应优先审查 draft profile 中 alpha 的单位语义，或生成 entry-path 可视化图；仍不建议直接跑 pressure。
"""


def parse_model_arg(items: list[str]) -> dict[str, Path]:
    models: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Model argument must be name=path, got: {item}")
        name, path = item.split("=", 1)
        models[name] = Path(path)
    return models


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate entry path acoustic property profiles for existing CT models.")
    parser.add_argument("--entry-plan", required=True)
    parser.add_argument("--model", action="append", required=True, help="name=path_to_model_dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--step-mm", type=float, default=0.5)
    parser.add_argument("--include-entry-neighborhood", action="store_true", help="Add a small explicit neighborhood around entry_index_ijk to avoid missing thin skull in nearest-neighbor path sampling.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    entry_plan_path = ROOT / args.entry_plan
    entry_plan = read_json(entry_plan_path)
    models = parse_model_arg(args.model)

    source = np.array(entry_plan["source_center_index_ijk"], dtype=float)
    entry = np.array(entry_plan.get("entry_index_ijk", entry_plan["source_center_index_ijk"]), dtype=float)
    target = np.array(entry_plan["target_index_ijk"], dtype=float)
    dx_m = float(entry_plan["dx_m"])
    source_t, source_indices = sample_indices(source, target, args.step_mm, dx_m)
    entry_t, entry_indices = sample_indices(entry, target, args.step_mm, dx_m)
    extra_indices: list[list[int]] = []
    if args.include_entry_neighborhood:
        entry_i = np.rint(entry).astype(int)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for dk in (-1, 0, 1):
                    extra_indices.append((entry_i + np.array([di, dj, dk])).tolist())

    loaded = {name: load_model(ROOT / path) for name, path in models.items()}
    shapes = {name: tuple(model["arrays"]["labels"].shape) for name, model in loaded.items()}
    if len(set(shapes.values())) != 1:
        raise ValueError(f"Model shapes differ: {shapes}")
    shape = next(iter(shapes.values()))
    all_indices = dedupe_indices(np.vstack([source_indices, entry_indices, np.array(extra_indices, dtype=int) if extra_indices else entry_indices[:0]]))
    for idx in all_indices.reshape(-1, 3):
        if np.any(idx < 0) or np.any(idx >= np.array(shape)):
            raise ValueError(f"Sample index out of bounds: {idx.tolist()} for shape {shape}")

    rows: list[dict[str, Any]] = []
    sample_id = 0
    def append_rows(path_name: str, t: float | None, idx: np.ndarray) -> None:
        nonlocal sample_id
        distance_from_source_mm = float(np.linalg.norm(idx.astype(float) - source) * dx_m * 1000.0)
        distance_from_entry_mm = float(np.linalg.norm(idx.astype(float) - entry) * dx_m * 1000.0)
        distance_to_target_mm = float(np.linalg.norm(idx.astype(float) - target) * dx_m * 1000.0)
        i, j, k = [int(x) for x in idx]
        for name, model in loaded.items():
            arrays = model["arrays"]
            rows.append(
                {
                    "sample_id": sample_id,
                    "path_name": path_name,
                    "t_path": None if t is None else float(t),
                    "distance_from_source_mm": distance_from_source_mm,
                    "distance_from_entry_mm": distance_from_entry_mm,
                    "distance_to_target_mm": distance_to_target_mm,
                    "i": i,
                    "j": j,
                    "k": k,
                    "model": name,
                    "label": int(arrays["labels"][i, j, k]),
                    "hu": float(arrays["hu"][i, j, k]),
                    "sound_speed_m_s": float(arrays["sound_speed"][i, j, k]),
                    "density_kg_m3": float(arrays["density"][i, j, k]),
                    "alpha_db_mhz_cm": float(arrays["alpha_coeff"][i, j, k]),
                }
            )
        sample_id += 1

    seen_path_indices: set[tuple[str, int, int, int]] = set()
    for path_name, t_seq, idx_seq in (
        ("source_to_target", source_t, source_indices),
        ("entry_to_target", entry_t, entry_indices),
    ):
        for t, idx in zip(t_seq, idx_seq):
            key = (path_name, int(idx[0]), int(idx[1]), int(idx[2]))
            if key in seen_path_indices:
                continue
            seen_path_indices.add(key)
            append_rows(path_name, float(t), idx)
    if args.include_entry_neighborhood:
        for idx in dedupe_indices(np.array(extra_indices, dtype=int)):
            key = ("entry_neighborhood", int(idx[0]), int(idx[1]), int(idx[2]))
            if key in seen_path_indices:
                continue
            seen_path_indices.add(key)
            append_rows("entry_neighborhood", None, idx)

    summaries = {name: summarize_rows(rows, name) for name in models}
    data = {
        "generated_at": now_iso(),
        "scope": "entry path property profile only; no k-Wave and no pressure simulation",
        "entry_plan_path": args.entry_plan,
        "source_center_index_ijk": entry_plan["source_center_index_ijk"],
        "entry_index_ijk": entry_plan.get("entry_index_ijk"),
        "target_index_ijk": entry_plan["target_index_ijk"],
        "step_mm": args.step_mm,
        "include_entry_neighborhood": bool(args.include_entry_neighborhood),
        "sample_count": int(sample_id),
        "model_dirs": {name: str(path) for name, path in models.items()},
        "model_shapes": {name: list(shape) for name, shape in shapes.items()},
        "model_mapping_profiles": {
            name: model["summary"].get("mapping_profile")
            for name, model in loaded.items()
        },
        "model_summaries": summaries,
        "pressure_simulation_allowed": False,
    }
    write_csv(out_dir / "entry_path_profile.csv", rows)
    write_json(out_dir / "entry_path_property_summary.json", data)
    write_md(out_dir / "entry_path_property_report.md", make_report(data))
    print(f"Wrote entry path property profile to {rel(out_dir)}")


if __name__ == "__main__":
    main()
