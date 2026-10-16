from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SELECTION = ROOT / "outputs" / "a5_heldout_d60_trajectory_selection_20260719" / "heldout_selection.json"
FULLWAVE = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "heldout_tr_report.json"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "bbb_acoustic_path_ranking" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "bbb_acoustic_path_ranking_20260721"
FREQUENCY_MHZ = 0.5


def minmax(values: list[float]) -> list[float]:
    low = min(values)
    high = max(values)
    if high == low:
        return [0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def standoff_penalty(standoff_mm: float) -> float:
    if 12.0 <= standoff_mm <= 25.0:
        return 0.0
    if standoff_mm < 12.0:
        return min(1.0, (12.0 - standoff_mm) / 12.0)
    return min(1.0, (standoff_mm - 25.0) / 25.0)


def transmission_loss(skull_path_mm: float, alpha_db_mhz_cm: float) -> float:
    attenuation_db = alpha_db_mhz_cm * FREQUENCY_MHZ * (skull_path_mm / 10.0)
    amplitude_transmission = 10.0 ** (-attenuation_db / 20.0)
    return 1.0 - amplitude_transmission


def hard_gate(candidate: dict[str, Any]) -> dict[str, bool]:
    labels = candidate.get("source_label_counts", {})
    source_points = candidate.get("source_points")
    return {
        "source_background_only": labels == {"0": source_points},
        "has_skull_crossing": candidate["entry_plan"].get("has_skull_crossing") is True,
        "no_post_skull_background_gap": candidate.get("post_skull_background_gap") is False,
    }


def build_proxy_records(selection: dict[str, Any], weights: dict[str, float]) -> list[dict[str, Any]]:
    candidates = selection["selected"]
    raw: list[dict[str, Any]] = []
    for candidate in candidates:
        entry = candidate["entry_plan"]
        skull_path = float(entry["skull_path_length_mm"])
        max_hu = float(candidate["max_hu"])
        checks = hard_gate(candidate)
        raw.append({
            "trajectory": candidate["candidate_id"],
            "eligible": all(checks.values()),
            "hard_gate": checks,
            "raw_terms": {
                "skull_path_length": skull_path,
                "incidence_angle": float(entry["incidence_angle_deg"]),
                "hu_burden": max_hu * skull_path,
                "transmission_loss": transmission_loss(skull_path, float(candidate["mean_alpha_db_mhz_cm"])),
                "standoff_penalty": standoff_penalty(float(entry["source_standoff_mm"])),
                "source_to_target_distance": float(entry["source_to_target_distance_mm"]),
                "geometry_difficulty": float(candidate["difficulty_score"]),
            },
            "geometry": {
                "source_to_target_mm": float(entry["source_to_target_distance_mm"]),
                "skull_path_mm": skull_path,
                "incidence_angle_deg": float(entry["incidence_angle_deg"]),
                "max_hu": max_hu,
                "source_standoff_mm": float(entry["source_standoff_mm"]),
            },
        })

    term_names = list(weights)
    normalized = {
        name: minmax([record["raw_terms"][name] for record in raw])
        for name in term_names
    }
    for index, record in enumerate(raw):
        record["normalized_terms"] = {name: normalized[name][index] for name in term_names}
        record["weighted_terms"] = {
            name: record["normalized_terms"][name] * weights[name] for name in term_names
        }
        record["proxy_acoustic_cost"] = float(sum(record["weighted_terms"].values()))
    return raw


def fullwave_risk(trajectory: dict[str, Any], weights: dict[str, float]) -> tuple[float, dict[str, float]]:
    pressure = trajectory["pressure"]
    material = trajectory["material"]
    terms = {
        "target_global_deficit": max(0.0, min(1.0, 1.0 - float(pressure["target_to_global_peak_ratio"]))),
        "skull_focus_scaled": max(0.0, min(1.0, float(trajectory["skull_focus_ratio"]) / 1.25)),
        "global_peak_in_skull": 1.0 if material["global_peak_material"] == "skull (label 2)" else 0.0,
        "peak_target_distance_scaled": max(0.0, min(1.0, float(pressure["global_peak_to_target_distance_mm"]) / 60.0)),
    }
    return float(sum(terms[name] * weights[name] for name in weights)), terms


def rank_paths(selection: dict[str, Any], fullwave: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    proxy_weights = evidence["proxy_weights"]
    risk_weights = evidence["fullwave_risk_weights"]
    mix = evidence["validated_cost_mix"]
    if abs(sum(proxy_weights.values()) - 1.0) > 1e-12 or abs(sum(risk_weights.values()) - 1.0) > 1e-12:
        raise ValueError("cost weights must sum to one")
    if abs(sum(mix.values()) - 1.0) > 1e-12:
        raise ValueError("validated cost mix must sum to one")

    records = build_proxy_records(selection, proxy_weights)
    fullwave_by_id = {row["trajectory"]: row for row in fullwave["trajectories"]}
    for record in records:
        observed = fullwave_by_id.get(record["trajectory"])
        if observed is None:
            record["fullwave_status"] = "not_available_proxy_only"
            record["fullwave_risk"] = None
            record["validated_acoustic_cost"] = None
            continue
        risk, terms = fullwave_risk(observed, risk_weights)
        record["fullwave_status"] = "available"
        record["fullwave_terms"] = terms
        record["fullwave_risk"] = risk
        record["validated_acoustic_cost"] = float(
            mix["proxy_cost"] * record["proxy_acoustic_cost"] + mix["fullwave_risk"] * risk
        )
        record["observed_verdict"] = observed["verdict"]

    eligible = [record for record in records if record["eligible"]]
    proxy_ranked = sorted(eligible, key=lambda row: (row["proxy_acoustic_cost"], row["trajectory"]))
    validated = [record for record in eligible if record["validated_acoustic_cost"] is not None]
    validated_ranked = sorted(validated, key=lambda row: (row["validated_acoustic_cost"], row["trajectory"]))
    shortest = min(eligible, key=lambda row: row["geometry"]["source_to_target_mm"])
    for rank, record in enumerate(proxy_ranked, 1):
        record["proxy_rank"] = rank
    for rank, record in enumerate(validated_ranked, 1):
        record["validated_rank"] = rank

    best_validated = validated_ranked[0] if validated_ranked else None
    return {
        "status": "validated_ranking_available" if best_validated else "proxy_ranking_only",
        "candidate_count": len(records),
        "eligible_count": len(eligible),
        "proxy_weights": proxy_weights,
        "fullwave_risk_weights": risk_weights,
        "validated_cost_mix": mix,
        "shortest_euclidean_path": shortest["trajectory"],
        "lowest_proxy_cost_path": proxy_ranked[0]["trajectory"],
        "lowest_validated_acoustic_cost_path": None if best_validated is None else best_validated["trajectory"],
        "shortest_is_not_lowest_validated_cost": best_validated is not None and shortest["trajectory"] != best_validated["trajectory"],
        "records": sorted(records, key=lambda row: row.get("validated_rank", 10_000)),
        "avoidance_labels_status": "dedicated_eye_sinus_implant_labels_unavailable",
        "pressure_executed": False,
        "claim_boundary": "within_case_engineering_ranking_not_safety_or_generalization",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank frozen BBB trajectories by proxy and validated acoustic cost.")
    parser.add_argument("--selection", type=Path, default=SELECTION)
    parser.add_argument("--fullwave", type=Path, default=FULLWAVE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = rank_paths(
        json.loads(args.selection.read_text(encoding="utf-8")),
        json.loads(args.fullwave.read_text(encoding="utf-8")),
        json.loads(EVIDENCE.read_text(encoding="utf-8")),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "path_ranking.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Case 079 BBB Acoustic Path Ranking",
        "",
        f"- Shortest Euclidean path: `{result['shortest_euclidean_path']}`",
        f"- Lowest proxy cost: `{result['lowest_proxy_cost_path']}`",
        f"- Lowest validated acoustic cost: `{result['lowest_validated_acoustic_cost_path']}`",
        f"- Shortest differs from validated optimum: `{result['shortest_is_not_lowest_validated_cost']}`",
        "",
        "| validated rank | trajectory | distance mm | proxy cost | full-wave risk | validated cost | observed |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for row in result["records"]:
        validated_cost = row.get("validated_acoustic_cost")
        risk = row.get("fullwave_risk")
        lines.append(
            f"| {row.get('validated_rank', '-')} | {row['trajectory']} | {row['geometry']['source_to_target_mm']:.3f} | "
            f"{row['proxy_acoustic_cost']:.4f} | {'-' if risk is None else f'{risk:.4f}'} | "
            f"{'-' if validated_cost is None else f'{validated_cost:.4f}'} | {row.get('observed_verdict', '-')} |"
        )
    lines.extend([
        "",
        "Proxy cost is a screening score. Validated cost incorporates existing matched full-wave results and is still not a clinical safety score.",
    ])
    (args.output_dir / "path_ranking.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "shortest": result["shortest_euclidean_path"],
        "best_validated": result["lowest_validated_acoustic_cost_path"],
        "counterexample": result["shortest_is_not_lowest_validated_cost"],
    }, indent=2))


if __name__ == "__main__":
    main()
