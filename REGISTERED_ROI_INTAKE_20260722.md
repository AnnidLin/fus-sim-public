# Registered Anatomical ROI Intake Gate

## Purpose

`bbb_registered_roi_intake.py` prevents a same-shaped mask or a manually relabelled contract from being treated as registered anatomy. The gate is offline and creates no pressure field.

## Required evidence

A registered ROI contract must declare:

- `target_roi.anatomical_status = registered_anatomical`;
- `target_roi.generation.method = loaded_mask` and a project-relative mask path;
- `patient_model.world_mapping.status = available` with a finite, invertible 4x4 affine;
- a registration sidecar binding the case ID, ROI ID, mask path, mask SHA-256, mask affine, source image, interpolation method, and transform provenance.

Label masks require nearest-neighbour interpolation. Native-grid masks require an identity transform record. Resampled masks require an applied transform file and matching SHA-256.

Example sidecar structure:

```json
{
  "registration_version": "1.0.0",
  "case_id": "CASE_ID",
  "roi_id": "ROI_ID",
  "roi_mask_path": "project/relative/roi_mask.npz",
  "roi_mask_sha256": "64-lowercase-hex-characters",
  "mask_affine_ijk_to_world_mm": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
  "registration_method": "native_patient_grid",
  "interpolation": "nearest_neighbor",
  "source_image_id": "source_mri_or_segmentation_id",
  "transform": {"status": "identity", "path": null, "sha256": null}
}
```

For NPZ/NPY masks the sidecar supplies the authoritative affine. For NIfTI masks, the embedded affine must also match the patient-model affine.

## Validation behavior

The gate verifies contract semantics, path containment, mask and transform hashes, affine equivalence, array shape, binary values, voxel count, and inclusion of the declared target center. Structural or provenance mismatches fail explicitly.

The current Case 079 fixture returns `registered_roi_intake_blocked` because it is a synthetic sphere, has no registered mask path, and the acoustic model does not retain an authoritative world affine. Canonical result: `outputs/bbb_registered_roi_intake_20260722/`.

The stricter result is consumed by `bbb_cohort_readiness.py`; cohort anatomical readiness no longer relies only on a contract label or ROI summary.

## Commands

```powershell
D:\AIprogram\python-envs\kwave312\Scripts\python.exe bbb_registered_roi_intake.py --plan planning_contracts\examples\case079_h1_bbb_simulation_plan.json --output-dir outputs\bbb_registered_roi_intake_20260722
D:\AIprogram\python-envs\kwave312\Scripts\python.exe bbb_registered_roi_intake.py --plan PATH_TO_REGISTERED_PLAN.json --registration-sidecar PATH_TO_SIDECAR.json --output-dir OUTPUT_DIRECTORY
```

Passing this gate means the anatomical input is traceable enough for research simulation. It does not establish device readiness, exposure readiness, treatment suitability, or clinical safety.
