from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "outputs" / "nlm_ct_acoustic_model_simple_hu300_dx0p75_20260723" / "acoustic_model_3d.npz"
DEFAULT_SUMMARY = ROOT / "outputs" / "nlm_ct_acoustic_model_simple_hu300_dx0p75_20260723" / "summary.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "nlm_ct_acoustic_model_audit_20260723"


class AcousticModelAuditError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(model_path: Path, summary_path: Path) -> dict:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with np.load(model_path, allow_pickle=False) as model:
        required = {"labels", "hu", "sound_speed", "density", "alpha_coeff", "dx_m"}
        missing = sorted(required - set(model.files))
        if missing:
            raise AcousticModelAuditError(f"model is missing required arrays: {missing}")
        labels = np.asarray(model["labels"])
        unique, counts = np.unique(labels, return_counts=True)
        label_counts = {str(int(label)): int(count) for label, count in zip(unique, counts)}
        common_shape = tuple(labels.shape)
        fields_match = all(tuple(model[name].shape) == common_shape for name in ("hu", "sound_speed", "density", "alpha_coeff"))
        dx_m = float(model["dx_m"])
        has_affine = "affine_ijk_to_world_mm" in model.files
    checks = {
        "profile_is_simple_hu300": summary.get("mapping_profile", {}).get("profile_id") == "simple_hu300",
        "profile_review_status_is_baseline_compatible": summary.get("mapping_profile", {}).get("review_status") == "baseline_compatible",
        "shape_matches_summary": list(common_shape) == summary.get("grid_shape"),
        "field_shapes_match": fields_match,
        "dx_is_0p75_mm": abs(dx_m - 0.00075) <= 1e-9,
        "labels_exactly_0_1_2": sorted(int(value) for value in unique) == [0, 1, 2],
        "all_material_classes_nonempty": all(label_counts.get(str(label), 0) > 0 for label in (0, 1, 2)),
        "output_affine_preserved_in_npz": has_affine,
    }
    candidate_ready = all(value for key, value in checks.items() if key != "output_affine_preserved_in_npz")
    return {
        "audit_version": "1.0.1", "case_id": "nlm_additional_head_72m",
        "model_path": str(model_path.relative_to(ROOT)), "model_sha256": sha256_file(model_path),
        "summary_path": str(summary_path.relative_to(ROOT)), "summary_sha256": sha256_file(summary_path),
        "grid_shape": list(common_shape), "dx_m": dx_m, "label_counts": label_counts, "checks": checks,
        "acoustic_model_candidate_ready": candidate_ready,
        "world_mapping": {"status": "available" if has_affine else "unavailable",
                          "reason": None if has_affine else "resampled acoustic NPZ does not preserve authoritative voxel-to-world affine"},
        "registered_anatomical_roi_ready": False, "pressure_executed": False, "clinical_safety_claim": False,
        "claim_boundary": "postmortem_public_binary_screening_acoustic_model_not_paper_grade_or_clinical",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the NLM public CT screening acoustic model without simulation.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = audit(args.model.resolve(), args.summary.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "acoustic_model_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
