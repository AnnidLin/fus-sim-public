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


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as data:
        return {key: data[key] for key in data.files}


def range_stats(arr: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float | int | None]:
    values = arr[mask] if mask is not None else arr.reshape(-1)
    if values.size == 0:
        return {"count": 0, "min": None, "p05": None, "median": None, "p95": None, "max": None, "mean": None}
    return {
        "count": int(values.size),
        "min": float(np.min(values)),
        "p05": float(np.percentile(values, 5)),
        "median": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
    }


def label_counts(labels: np.ndarray) -> dict[str, int]:
    unique, counts = np.unique(labels, return_counts=True)
    return {str(int(label)): int(count) for label, count in zip(unique, counts)}


def line_profile(arr: np.ndarray, target: np.ndarray, axis: int = 0) -> dict[str, Any]:
    index = [int(target[0]), int(target[1]), int(target[2])]
    slicer = [index[0], index[1], index[2]]
    slicer[axis] = slice(None)
    values = arr[tuple(slicer)]
    return {
        "axis": axis,
        "target_index": index,
        "count": int(values.size),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "target_value": float(arr[tuple(index)]),
        "nonzero_unique_sample": [float(v) for v in np.unique(values)[:20]],
    }


def model_summary(model_dir: Path) -> dict[str, Any]:
    npz_path = model_dir / "acoustic_model_3d.npz"
    summary_path = model_dir / "summary.json"
    if not npz_path.exists():
        raise FileNotFoundError(f"Model NPZ not found: {npz_path}")
    arrays = load_npz(npz_path)
    labels = arrays["labels"]
    target = np.array(arrays["target_index_ijk"], dtype=int)
    skull = labels == 2
    soft = labels == 1
    background = labels == 0
    summary = read_json(summary_path) if summary_path.exists() else {}
    alpha_metadata = {}
    for key in ("alpha_power", "alpha_mode", "alpha_unit_semantics", "alpha_coeff_kind", "alpha_source_route", "alpha_semantics_status", "alpha_pressure_allowed"):
        if key in arrays:
            value = arrays[key]
            alpha_metadata[key] = value.item() if getattr(value, "shape", ()) == () else value.tolist()
    return {
        "model_dir": rel(model_dir),
        "npz_path": rel(npz_path),
        "summary_path": rel(summary_path),
        "mapping_profile": summary.get("mapping_profile"),
        "alpha_metadata_npz": alpha_metadata,
        "shape": [int(x) for x in labels.shape],
        "dx_m": float(np.array(arrays["dx_m"]).reshape(-1)[0]),
        "target_index_ijk": [int(x) for x in target],
        "target_label": int(labels[tuple(target)]),
        "label_counts": label_counts(labels),
        "hu_range_all": range_stats(arrays["hu"]),
        "hu_range_skull": range_stats(arrays["hu"], skull),
        "sound_speed_all": range_stats(arrays["sound_speed"]),
        "sound_speed_skull": range_stats(arrays["sound_speed"], skull),
        "density_all": range_stats(arrays["density"]),
        "density_skull": range_stats(arrays["density"], skull),
        "alpha_all": range_stats(arrays["alpha_coeff"]),
        "alpha_skull": range_stats(arrays["alpha_coeff"], skull),
        "target_values": {
            "hu": float(arrays["hu"][tuple(target)]),
            "sound_speed_m_s": float(arrays["sound_speed"][tuple(target)]),
            "density_kg_m3": float(arrays["density"][tuple(target)]),
            "alpha_db_mhz_cm": float(arrays["alpha_coeff"][tuple(target)]),
        },
        "axis_x_profiles": {
            "labels": line_profile(labels.astype(float), target, axis=0),
            "hu": line_profile(arrays["hu"], target, axis=0),
            "sound_speed": line_profile(arrays["sound_speed"], target, axis=0),
            "density": line_profile(arrays["density"], target, axis=0),
            "alpha": line_profile(arrays["alpha_coeff"], target, axis=0),
        },
        "mask_counts": {
            "background": int(np.count_nonzero(background)),
            "soft": int(np.count_nonzero(soft)),
            "skull": int(np.count_nonzero(skull)),
        },
    }


def comparison_rows(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    metrics = [
        ("skull_sound_speed_min", baseline["sound_speed_skull"]["min"], candidate["sound_speed_skull"]["min"]),
        ("skull_sound_speed_max", baseline["sound_speed_skull"]["max"], candidate["sound_speed_skull"]["max"]),
        ("skull_density_min", baseline["density_skull"]["min"], candidate["density_skull"]["min"]),
        ("skull_density_max", baseline["density_skull"]["max"], candidate["density_skull"]["max"]),
        ("skull_alpha_min", baseline["alpha_skull"]["min"], candidate["alpha_skull"]["min"]),
        ("skull_alpha_max", baseline["alpha_skull"]["max"], candidate["alpha_skull"]["max"]),
        ("target_sound_speed", baseline["target_values"]["sound_speed_m_s"], candidate["target_values"]["sound_speed_m_s"]),
        ("target_density", baseline["target_values"]["density_kg_m3"], candidate["target_values"]["density_kg_m3"]),
        ("target_alpha", baseline["target_values"]["alpha_db_mhz_cm"], candidate["target_values"]["alpha_db_mhz_cm"]),
    ]
    for name, base, cand in metrics:
        diff = None if base is None or cand is None else float(cand) - float(base)
        rows.append({"metric": name, "baseline": base, "candidate": cand, "candidate_minus_baseline": diff})
    return rows


def make_report(data: dict[str, Any]) -> str:
    cand = data["candidate"]
    base = data["baseline"]
    alpha_meta = cand.get("alpha_metadata_npz", {})
    return f"""# Mapping Model-Build Validation Report

## 结论

本报告只验证 CT 声学模型构建结果，不运行 k-Wave，也不生成 pressure field。

候选 profile：`{data['candidate_profile_path']}`

候选状态：`{data['candidate_review_status']}`

当前判断：**model-build-only draft validation completed; not pressure-validated; not default-ready**。

## Baseline 与 Candidate

- baseline model：`{base['model_dir']}`
- candidate model：`{cand['model_dir']}`
- target：`{cand['target_index_ijk']}`
- target label：`{cand['target_label']}`
- grid shape：`{cand['shape']}`
- dx：`{cand['dx_m']}` m
- candidate alpha metadata：`{alpha_meta}`

## Skull 属性范围

| 属性 | baseline skull range | candidate skull range |
| --- | --- | --- |
| sound speed | {base['sound_speed_skull']['min']} - {base['sound_speed_skull']['max']} m/s | {cand['sound_speed_skull']['min']} - {cand['sound_speed_skull']['max']} m/s |
| density | {base['density_skull']['min']} - {base['density_skull']['max']} kg/m3 | {cand['density_skull']['min']} - {cand['density_skull']['max']} kg/m3 |
| alpha | {base['alpha_skull']['min']} - {base['alpha_skull']['max']} dB/MHz/cm | {cand['alpha_skull']['min']} - {cand['alpha_skull']['max']} dB/MHz/cm |

## 关键风险

- Candidate attenuation 来自 PRESTUS Mueller-style draft，仍需确认 k-Wave Python 的 `alpha_coeff` / `alpha_power` 语义。
- Candidate NPZ 已记录 alpha metadata，但该 metadata 只说明 intended semantics，不等于公式验证。
- 该模型构建通过不代表 pressure simulation 可以直接开始。
- `continuous_skull` 和本 draft profile 都不得作为默认 profile。

## 下一步

1. 人工复核 attenuation 单位和 `alpha_power`。
2. 如需继续，生成 profile comparison plots 或 entry-path property CSV。
3. 只有在 evidence brief 和 dry-run quality 通过后，才考虑最多一个 pressure sanity run。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate CT acoustic model build outputs without running pressure simulations.")
    parser.add_argument("--baseline-dir", required=True)
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--candidate-profile", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline = model_summary(ROOT / args.baseline_dir)
    candidate = model_summary(ROOT / args.candidate_dir)
    profile = read_json(ROOT / args.candidate_profile)
    rows = comparison_rows(baseline, candidate)
    data = {
        "generated_at": now_iso(),
        "scope": "model-build-only validation; no k-Wave and no pressure field",
        "baseline": baseline,
        "candidate": candidate,
        "candidate_profile_path": args.candidate_profile,
        "candidate_profile_id": profile.get("profile_id"),
        "candidate_review_status": profile.get("review_status"),
        "candidate_mapping_type": profile.get("mapping_type"),
        "comparison_rows": rows,
        "status": "draft_model_build_validation_completed_not_default_ready",
        "pressure_simulation_allowed": False,
    }
    write_json(out_dir / "model_build_validation.json", data)
    write_md(out_dir / "model_build_validation.md", make_report(data))
    write_csv(out_dir / "model_build_validation_metrics.csv", rows)
    print(f"Wrote model-build validation report to {rel(out_dir)}")


if __name__ == "__main__":
    main()
