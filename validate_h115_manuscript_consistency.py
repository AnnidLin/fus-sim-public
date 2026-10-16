from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


def required_tokens() -> dict[str, str]:
    dx05 = load_json("outputs/ucl_h115_source_registration_audit_20260825/effective_dx0p5_coordinate_audit.json")
    dx03 = load_json("outputs/ucl_h115_source_registration_audit_20260825/effective_dx0p3_coordinate_audit.json")
    source = load_json("outputs/ucl_h115_source_registration_audit_20260825/source_registration_sensitivity.json")
    effective_zero = next(row for row in source["simulations"]["effective"]["registration"] if row["offset_mm"] == 0.0)
    nominal_zero = next(row for row in source["simulations"]["nominal"]["registration"] if row["offset_mm"] == 0.0)
    aperture_02 = next(row for row in source["simulations"]["effective"]["hydrophone_aperture"] if row["diameter_mm"] == 0.2)
    return {
        "dx05_axial_peak_error_mm": f'{dx05["axial_held_out"]["peak_position_difference_mm"]:.3f}',
        "dx03_axial_peak_error_mm": f'{dx03["axial_held_out"]["peak_position_difference_mm"]:.3f}',
        "dx05_transverse_l2_percent": f'{dx05["transverse_held_out"]["normalized_relative_l2_percent"]:.3f}',
        "dx03_transverse_l2_percent": f'{dx03["transverse_held_out"]["normalized_relative_l2_percent"]:.3f}',
        "dx05_y_width_error_percent": f'{dx05["transverse_held_out"]["y_width_error_percent"]:.3f}',
        "dx03_y_width_error_percent": f'{dx03["transverse_held_out"]["y_width_error_percent"]:.3f}',
        "nominal_axial_peak_error_mm": f'{nominal_zero["peak_position_difference_mm"]:.3f}',
        "nominal_axial_l2_percent": f'{nominal_zero["normalized_relative_l2_percent"]:.3f}',
        "nominal_transverse_l2_percent": f'{source["simulations"]["nominal"]["hydrophone_aperture"][0]["normalized_relative_l2_percent"]:.3f}',
        "effective_axial_l2_percent": f'{effective_zero["normalized_relative_l2_percent"]:.3f}',
        "aperture_02_transverse_l2_percent": f'{aperture_02["normalized_relative_l2_percent"]:.3f}',
    }


def validate(documents: list[Path]) -> dict:
    tokens = required_tokens()
    document_checks = {}
    for path in documents:
        text = path.read_text(encoding="utf-8-sig")
        checks = {name: value in text for name, value in tokens.items()}
        checks.update(
            {
                "nonpassing_boundary": "nonpassing" in text.lower(),
                "formal_convergence_blocked": "formal convergence" in text.lower(),
                "post_hoc_registration_blocked": "post-hoc" in text.lower(),
                "positive_overclaim_absent": not any(
                    phrase in text.lower()
                    for phrase in (
                        "h115 was successfully validated",
                        "external validation passed",
                        "formal convergence was achieved",
                        "grid convergence was established",
                        "validated the case079",
                    )
                ),
                "historical_grid_figure_not_used": "paper/figures/ucl_h115_grid_sensitivity_20260823" not in text,
                "three_failure_wording_absent": "three remaining nonpassing" not in text.lower() and "three failed endpoints" not in text.lower(),
            }
        )
        if path.name == "PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md":
            cited = {
                int(number)
                for group in re.findall(r"\[(\d+(?:,\d+)*)\]", text)
                for number in group.split(",")
            }
            defined = {int(number) for number in re.findall(r"(?m)^(\d+)\. ", text)}
            checks.update(
                {
                    "ucl_dataset_doi_cited": "10.5522/04/28025240.v2" in text,
                    "hydrophone_review_doi_cited": "10.1109/TUFFC.2022.3213185" in text,
                    "h115_method_has_dataset_citation": "[5,8]" in text,
                    "hydrophone_limit_has_review_citation": "[9]" in text,
                    "reference_numbers_contiguous": defined == set(range(1, 12)),
                    "all_references_are_cited": defined == cited,
                    "all_citations_are_defined": cited <= defined,
                    "ucl_dataset_license_reported": "CC BY 4.0" in text,
                    "ucl_input_sha256_reported": "0275af014151ca972c0c7799af2735e345554c460f797f217bd8ceb4f3dfa0ad" in text,
                    "two_remaining_failures_reported": "two remaining nonpassing endpoints" in text.lower(),
                    "old_widths_explicitly_superseded": "not the previously reported +26.608% and +28.144%" in text,
                    "case079_dataset_doi_reported": "10.13026/4nae-zg36" in text,
                    "case079_raw_ct_not_redistributed": "raw ct is therefore not redistributed" in text.lower(),
                    "binary_mapping_constants_reported": "2800 m s−1, 1900 kg m−3" in text,
                    "engineering_target_boundary": "engineering geometric candidate" in text.lower(),
                    "title_retains_simulation_scope": text.splitlines()[0].lower().endswith("simulation workflow"),
                    "abstract_retains_single_case_scope": "one frozen computational case" in text,
                    "abstract_blocks_accuracy_generalization_safety": "They do not establish numerical convergence, absolute-pressure accuracy, cross-subject generalization, efficacy or safety." in text,
                    "data_availability_reports_136_file_candidate": "contains 136 compact files" in text,
                    "submission_ready_not_implied": "ready for submission" not in text.lower() and "submission-ready" not in text.lower(),
                }
            )
        if path.name == "UCL_H115_PAPER_READINESS_20260823.md":
            checks.update(
                {
                    "two_remaining_failures_reported": "two remaining nonpassing" in text.lower(),
                    "corrected_widths_pass": "so both width checks pass" in text.lower(),
                }
            )
        document_checks[str(path.relative_to(ROOT))] = checks
    decision_path = ROOT / "paper/UCL_H115_VALIDATION_DECISION_BRIEF_ZH_20260826.md"
    decision_text = decision_path.read_text(encoding="utf-8-sig")
    document_checks[str(decision_path.relative_to(ROOT))] = {
        "effective_dx0p5_pass_count": "6/8" in decision_text,
        "effective_dx0p3_pass_count": decision_text.count("6/8") >= 2,
        "nominal_pass_count": "0/8" in decision_text,
        "corrected_widths": "+5.989%" in decision_text and "+7.160%" in decision_text,
        "aperture_sensitivity": "15.004%" in decision_text and "15.039%" in decision_text,
        "nonpassing_boundary": "非通过外部验证" in decision_text,
        "clinical_boundary": "不构成临床、安全、疗效、剂量或跨受试者结论" in decision_text,
    }
    failed = [f"{path}:{name}" for path, checks in document_checks.items() for name, passed in checks.items() if not passed]
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not failed else "failed",
        "source_tokens": tokens,
        "document_checks": document_checks,
        "document_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in documents + [decision_path]
        },
        "failed_checks": failed,
        "claim_boundary": "Text-to-artifact consistency only; not successful external validation or formal convergence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/ucl_h115_source_registration_audit_20260825/manuscript_consistency.json")
    args = parser.parse_args()
    docs = [
        ROOT / "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md",
        ROOT / "paper/PUB2_METHODS_RESULTS_EVIDENCE_20260812.md",
        ROOT / "paper/UCL_H115_PAPER_READINESS_20260823.md",
    ]
    report = validate(docs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed_check_count": len(report["failed_checks"])}))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
