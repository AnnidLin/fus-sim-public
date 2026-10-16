from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs" / "250khz_h3_wide_comparability_audit_20260729"
RUNS = {
    "default_baseline": ROOT / "outputs" / "case079_kwave_quick_250khz_20260724",
    "h3_baseline": ROOT / "outputs" / "case079_h3_250khz_baseline_20260728",
    "default_tr": ROOT / "outputs" / "case079_tr_250khz_20260724",
    "h3_tr": ROOT / "outputs" / "case079_h3_tr_250khz_20260728",
    "nlm_quick_tr": ROOT / "outputs" / "nlm_tr_72m_250khz_20260724",
    "nlm_wide_tr": ROOT / "outputs" / "nlm_tr_wide_250khz_20260728",
}
IGNORED_EXECUTION_FIELDS = {"stage"}
H3_INTENDED_FIELDS = {
    "entry_plan_path",
    "transducer_radius_m",
    "aperture_diameter_m",
}
DOMAIN_INTENDED_FIELDS = {
    "quick_lateral_half_width_m",
    "quick_post_target_margin_m",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def load_run(name: str) -> dict[str, Any]:
    directory = RUNS[name]
    summary = load_json(directory / "summary.json")
    config = summary.get("config")
    quality = summary.get("simulation_quality")
    source = summary.get("source")
    if not all(isinstance(item, dict) for item in (config, quality, source)):
        raise ValueError(f"{directory}: missing config/quality/source")
    counts = source.get("source_label_counts")
    background_only = (
        isinstance(counts, dict)
        and set(counts) == {"0"}
        and isinstance(counts.get("0"), int)
        and counts["0"] > 0
    )
    core_files = {
        filename: (directory / filename).is_file()
        for filename in ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json")
    }
    return {
        "directory": str(directory.relative_to(ROOT)).replace("\\", "/"),
        "config": config,
        "grid_size": quality.get("grid_size"),
        "dt_s": quality.get("dt_s"),
        "nt": quality.get("nt"),
        "source_label_counts": counts,
        "source_background_only": background_only,
        "core_files": core_files,
        "core_complete": all(core_files.values()),
    }


def compare(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    intended_fields: set[str],
) -> dict[str, Any]:
    fields = sorted(set(left["config"]) | set(right["config"]))
    mismatches = {
        field: {
            "left": left["config"].get(field),
            "right": right["config"].get(field),
        }
        for field in fields
        if left["config"].get(field) != right["config"].get(field)
        and field not in IGNORED_EXECUTION_FIELDS
    }
    intended = sorted(field for field in mismatches if field in intended_fields)
    confounded = sorted(field for field in mismatches if field not in intended_fields)
    return {
        "config_mismatches": mismatches,
        "intended_changed_fields": intended,
        "confounded_config_fields": confounded,
        "single_variable_comparison": len(confounded) == 0,
        "source_background_only": (
            left["source_background_only"] and right["source_background_only"]
        ),
        "core_complete": left["core_complete"] and right["core_complete"],
    }


def build_audit() -> dict[str, Any]:
    runs = {name: load_run(name) for name in RUNS}
    comparisons = {
        "h3_vs_default_baseline": compare(
            runs["default_baseline"],
            runs["h3_baseline"],
            intended_fields=H3_INTENDED_FIELDS,
        ),
        "h3_vs_default_tr": compare(
            runs["default_tr"],
            runs["h3_tr"],
            intended_fields=H3_INTENDED_FIELDS,
        ),
        "nlm_wide_vs_quick_tr": compare(
            runs["nlm_quick_tr"],
            runs["nlm_wide_tr"],
            intended_fields=DOMAIN_INTENDED_FIELDS,
        ),
    }
    raw_complete = all(run["core_complete"] for run in runs.values())
    geometry_supported = (
        comparisons["h3_vs_default_baseline"]["single_variable_comparison"]
        and comparisons["h3_vs_default_tr"]["single_variable_comparison"]
    )
    wide_supported = (
        comparisons["nlm_wide_vs_quick_tr"]["single_variable_comparison"]
        and comparisons["nlm_wide_vs_quick_tr"]["source_background_only"]
    )
    return {
        "audit_version": "1.0.0",
        "module": "250khz_h3_wide_comparability_audit_20260729",
        "runs": runs,
        "comparisons": comparisons,
        "decision": {
            "status": (
                "comparable"
                if geometry_supported and wide_supported
                else "comparability_blocked"
            ),
            "raw_outputs_complete": raw_complete,
            "geometry_causal_claim_supported": geometry_supported,
            "wide_domain_only_claim_supported": wide_supported,
            "allowed_claim": (
                "Raw H3 and wide-domain observations are reproducible, but causal "
                "attribution is blocked by protocol drift and NLM source placement."
            ),
        },
        "recommended_matched_protocol": {
            "frequency_hz": 250000,
            "source_pressure_pa": 1000000,
            "tone_burst_cycles": 2,
            "cfl": 0.2,
            "pml_size": 12,
            "simulation_time_us": 100,
            "preset": "quick",
            "quick_lateral_mm": 17,
            "quick_post_target_mm": 8,
            "allow_entry_plan_resolution_mismatch": False,
            "required_source_labels": {"0": "all source points"},
            "design": "2 trajectories x 2 transducers, four matched baseline cells",
        },
        "blocked_claims": [
            "the H3 improvement is caused by trajectory alone",
            "the H3 improvement is caused by transducer alone",
            "the NLM wide run isolates domain extent",
            "the NLM quick crop is source-safe",
            "paper-grade or clinical interpretation",
        ],
    }


def write_audit(audit: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "comparability_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# 250 kHz H3 / Wide-Domain Comparability Audit",
        "",
        f"- Status: `{audit['decision']['status']}`",
        f"- Raw outputs complete: `{str(audit['decision']['raw_outputs_complete']).lower()}`",
        f"- Geometry causal claim supported: `{str(audit['decision']['geometry_causal_claim_supported']).lower()}`",
        f"- Wide-domain-only claim supported: `{str(audit['decision']['wide_domain_only_claim_supported']).lower()}`",
        "",
        "## Comparison gates",
        "",
        "| Comparison | Confounded fields | Source background-only | Single-variable |",
        "|---|---|---|---|",
    ]
    for name, comparison in audit["comparisons"].items():
        fields = ", ".join(comparison["confounded_config_fields"]) or "none"
        lines.append(
            f"| {name} | {fields} | "
            f"{str(comparison['source_background_only']).lower()} | "
            f"{str(comparison['single_variable_comparison']).lower()} |"
        )
    lines += [
        "",
        "## Correct interpretation",
        "",
        audit["decision"]["allowed_claim"],
        "",
        "The observed pressure fields remain valid engineering observations. The",
        "current pairwise deltas cannot isolate trajectory, transducer, or domain",
        "extent because other protocol fields changed simultaneously.",
        "",
        "## Required next design",
        "",
        "Run a matched four-cell baseline factorial: two trajectories × two",
        "transducers under the same 250 kHz, two-cycle, PML12, 100 us, quick",
        "17/8 mm crop protocol, with resolution mismatch disabled and every",
        "source point in background label 0.",
    ]
    (OUTPUT_DIR / "comparability_audit.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    audit = build_audit()
    write_audit(audit)
    print(json.dumps({
        "status": audit["decision"]["status"],
        "raw_outputs_complete": audit["decision"]["raw_outputs_complete"],
        "geometry_causal_claim_supported": audit["decision"][
            "geometry_causal_claim_supported"
        ],
        "wide_domain_only_claim_supported": audit["decision"][
            "wide_domain_only_claim_supported"
        ],
        "output_dir": str(OUTPUT_DIR),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
