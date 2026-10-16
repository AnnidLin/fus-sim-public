#!/usr/bin/env python3
"""Compare pressure-amplitude fields using the ITRUSST Phase-I definitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import h5py
import numpy as np
from scipy import ndimage
from scipy.io import loadmat


ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = ROOT / "benchmarking" / "itrusst_phase1_contract.json"
DEFAULT_DATASET_KEY = "p_amp"


def _json_dump(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "itrusst_phase1_v1_20260803":
        raise ValueError(f"Unsupported or missing contract_id in {path}")
    return contract


def _find_hdf5_dataset(handle: h5py.File, key: str) -> h5py.Dataset:
    normalized = key.lstrip("/")
    if normalized in handle and isinstance(handle[normalized], h5py.Dataset):
        return handle[normalized]
    matches: list[h5py.Dataset] = []

    def visitor(name: str, obj: Any) -> None:
        if isinstance(obj, h5py.Dataset) and name.split("/")[-1] == normalized:
            matches.append(obj)

    handle.visititems(visitor)
    if len(matches) != 1:
        raise KeyError(
            f"Expected exactly one HDF5 dataset named {key!r}; found {len(matches)}"
        )
    return matches[0]


def load_array(path: Path, key: str = DEFAULT_DATASET_KEY) -> np.ndarray:
    """Load an array without applying implicit axis permutation or resampling."""
    suffix = path.suffix.lower()
    if suffix == ".npz":
        with np.load(path, allow_pickle=False) as archive:
            if key not in archive:
                raise KeyError(f"{path} does not contain {key!r}")
            array = np.asarray(archive[key])
    elif suffix in {".h5", ".hdf5"}:
        with h5py.File(path, "r") as handle:
            array = np.asarray(_find_hdf5_dataset(handle, key))
    elif suffix == ".mat":
        try:
            with h5py.File(path, "r") as handle:
                array = np.asarray(_find_hdf5_dataset(handle, key))
        except OSError:
            values = loadmat(path)
            if key not in values:
                raise KeyError(f"{path} does not contain {key!r}")
            array = np.asarray(values[key])
    else:
        raise ValueError(f"Unsupported field format: {path.suffix}")
    return array


def validate_amplitude(field: np.ndarray, name: str) -> np.ndarray:
    field = np.asarray(field, dtype=np.float64)
    if field.ndim not in (2, 3):
        raise ValueError(f"{name} must be 2-D or 3-D, got shape {field.shape}")
    if not np.all(np.isfinite(field)):
        raise ValueError(f"{name} contains NaN or infinite values")
    if np.any(field < 0):
        raise ValueError(f"{name} contains negative pressure amplitudes")
    if float(np.max(field)) <= 0:
        raise ValueError(f"{name} has no positive pressure amplitude")
    return field


def parse_axis_order(text: str | None) -> tuple[int, int, int] | None:
    if text is None:
        return None
    order = tuple(int(item.strip()) for item in text.split(","))
    if sorted(order) != [0, 1, 2]:
        raise ValueError("Axis order must be a permutation such as 2,1,0")
    return order  # type: ignore[return-value]


def build_analysis_mask(
    shape: tuple[int, ...],
    benchmark: int,
    source: int,
    contract: dict[str, Any],
    brain_mask: np.ndarray | None = None,
) -> np.ndarray:
    if benchmark not in range(1, 10):
        raise ValueError("benchmark must be between 1 and 9")
    if source not in (1, 2):
        raise ValueError("source must be 1 or 2")
    conventions = contract["index_conventions"]
    exit_index = int(conventions[f"source_{source}_exit_plane_python"])
    if benchmark <= 6 and len(shape) != 2:
        raise ValueError(f"BM{benchmark} requires a 2-D lateral-by-axial field")
    if benchmark >= 7 and len(shape) != 3:
        raise ValueError(f"BM{benchmark} requires a 3-D field")
    if exit_index >= shape[-1]:
        raise ValueError("source-exit index is outside the axial field extent")
    mask = np.zeros(shape, dtype=bool)
    mask[..., exit_index:] = True
    if benchmark == 1:
        return mask
    if benchmark <= 6:
        brain_start = int(conventions["bm1_bm6_brain_start_python"])
        mask[..., :brain_start] = False
        return mask
    if brain_mask is None:
        raise ValueError(f"BM{benchmark} requires the official 3-D brain mask")
    brain_mask = np.asarray(brain_mask).squeeze()
    if brain_mask.shape != shape:
        raise ValueError(
            f"brain mask shape {brain_mask.shape} does not match field {shape}"
        )
    return mask & brain_mask.astype(bool)


def relative_errors(
    reference: np.ndarray,
    candidate: np.ndarray,
    mask: np.ndarray,
) -> dict[str, float]:
    if not np.any(mask):
        raise ValueError("comparison mask is empty")
    reference_values = reference[mask]
    candidate_values = candidate[mask]
    reference_peak = float(np.max(np.abs(reference_values)))
    reference_energy = float(np.sum(reference_values**2))
    if reference_peak == 0 or reference_energy == 0:
        raise ValueError("reference is zero inside the comparison mask")
    difference = candidate_values - reference_values
    return {
        "relative_linf_percent": 100.0
        * float(np.max(np.abs(difference)))
        / reference_peak,
        "relative_l2_percent": 100.0
        * math.sqrt(float(np.sum(difference**2)) / reference_energy),
    }


def masked_peak(field: np.ndarray, mask: np.ndarray) -> tuple[float, tuple[int, ...]]:
    masked = np.where(mask, field, -np.inf)
    flat_index = int(np.argmax(masked))
    position = tuple(int(item) for item in np.unravel_index(flat_index, field.shape))
    return float(field[position]), position


def validate_candidate_region(
    field: np.ndarray,
    mask: np.ndarray,
) -> dict[str, Any]:
    field = validate_amplitude(field, "candidate")
    if mask.shape != field.shape or not np.any(mask):
        raise ValueError("validation mask is empty or does not match the field")
    values = field[mask]
    positive_voxels = int(np.count_nonzero(values > 0))
    peak, position = masked_peak(field, mask)
    passed = bool(
        np.all(np.isfinite(values))
        and positive_voxels > 0
        and peak > 0
    )
    return {
        "status": "passed" if passed else "failed",
        "mask_voxels": int(values.size),
        "positive_voxels": positive_voxels,
        "peak_pa": peak,
        "peak_index": list(position),
        "finite": bool(np.all(np.isfinite(values))),
    }


def interpolated_fwhm(values: Iterable[float], peak_index: int) -> float:
    """Return FWHM in samples, matching the interpolation used by fwhm2.m."""
    profile = np.asarray(list(values), dtype=np.float64)
    if profile.ndim != 1 or profile.size < 3:
        return math.nan
    if not 0 <= peak_index < profile.size:
        raise IndexError("peak_index is outside the profile")
    peak = float(profile[peak_index])
    if not np.isfinite(peak) or peak <= 0:
        return math.nan
    half = peak / 2.0

    left = peak_index
    while left > 0 and profile[left] > half:
        left -= 1
    right = peak_index
    while right < profile.size - 1 and profile[right] > half:
        right += 1
    if left == 0 and profile[left] > half:
        return math.nan
    if right == profile.size - 1 and profile[right] > half:
        return math.nan

    left_denom = profile[left + 1] - profile[left]
    right_denom = profile[right] - profile[right - 1]
    if left_denom == 0 or right_denom == 0:
        return math.nan
    left_crossing = left + (half - profile[left]) / left_denom
    right_crossing = (right - 1) + (half - profile[right - 1]) / right_denom
    return float(right_crossing - left_crossing)


def profile_widths(
    field: np.ndarray,
    reference_peak_position: tuple[int, ...],
    dx_mm: float,
) -> dict[str, float]:
    if field.ndim == 2:
        x, z = reference_peak_position
        lateral = field[:, z]
        axial = field[x, :]
    elif field.ndim == 3:
        x, y, z = reference_peak_position
        lateral = field[:, y, z]
        axial = field[x, y, :]
    else:
        raise ValueError("profile widths require a 2-D or 3-D field")
    return {
        "lateral_minus_3db_mm": dx_mm * interpolated_fwhm(lateral**2, x),
        "lateral_minus_6db_mm": dx_mm * interpolated_fwhm(lateral, x),
        "axial_minus_3db_mm": dx_mm * interpolated_fwhm(axial**2, z),
        "axial_minus_6db_mm": dx_mm * interpolated_fwhm(axial, z),
    }


def largest_minus_6db_volume_mm3(
    field: np.ndarray,
    mask: np.ndarray,
    dx_mm: float,
) -> float:
    if field.ndim != 3:
        raise ValueError("-6 dB focal volume requires a 3-D field")
    peak, _ = masked_peak(field, mask)
    thresholded = mask & (field >= 0.5 * peak)
    structure = ndimage.generate_binary_structure(3, 3)
    labels, count = ndimage.label(thresholded, structure=structure)
    if count == 0:
        return 0.0
    counts = np.bincount(labels.ravel())[1:]
    return float(np.max(counts)) * dx_mm**3


def compare_fields(
    reference: np.ndarray,
    candidate: np.ndarray,
    mask: np.ndarray,
    dx_mm: float,
    include_volume: bool,
) -> dict[str, Any]:
    reference = validate_amplitude(reference, "reference")
    candidate = validate_amplitude(candidate, "candidate")
    if reference.shape != candidate.shape:
        raise ValueError(
            f"shape mismatch: reference {reference.shape}, candidate {candidate.shape}; "
            "implicit resampling is prohibited"
        )
    if mask.shape != reference.shape:
        raise ValueError("mask shape does not match fields")
    errors = relative_errors(reference, candidate, mask)
    reference_peak, reference_position = masked_peak(reference, mask)
    candidate_peak, candidate_position = masked_peak(candidate, mask)
    position_distance = math.dist(reference_position, candidate_position) * dx_mm
    result: dict[str, Any] = {
        **errors,
        "reference_peak": reference_peak,
        "candidate_peak": candidate_peak,
        "peak_difference_percent": 100.0
        * abs(candidate_peak - reference_peak)
        / abs(reference_peak),
        "reference_peak_index": list(reference_position),
        "candidate_peak_index": list(candidate_position),
        "focal_position_difference_mm": position_distance,
        "reference_widths": profile_widths(
            reference, reference_position, dx_mm
        ),
        "candidate_widths_at_reference_peak": profile_widths(
            candidate, reference_position, dx_mm
        ),
    }
    if include_volume:
        result["reference_minus_6db_volume_mm3"] = largest_minus_6db_volume_mm3(
            reference, mask, dx_mm
        )
        result["candidate_minus_6db_volume_mm3"] = largest_minus_6db_volume_mm3(
            candidate, mask, dx_mm
        )
    return result


def build_dry_run(
    contract: dict[str, Any],
    reference_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    grid = contract["official_discretization"][
        "protocol_bm1_bm7_grid_including_pml"
    ]
    voxel_count = int(np.prod(np.asarray(grid, dtype=np.int64)))
    archive_size = int(contract["dataset"]["size_bytes"])
    subset_acquired = bool(
        reference_manifest
        and reference_manifest.get("payload_files_downloaded") is True
        and reference_manifest.get("matched_entry_count") == 3
        and len(reference_manifest.get("extracted_entries", [])) == 3
    )
    blockers = [
        "source_normalization_and_coordinate_parity_not_demonstrated",
        "solver_peak_memory_and_runtime_not_measured_for_this_grid",
    ]
    if not subset_acquired:
        blockers.insert(0, "official_reference_subset_not_acquired")
    return {
        "schema_version": "1.0",
        "contract_id": contract["contract_id"],
        "status": "blocked_before_pressure_execution",
        "claim_level": "resource_and_parameter_gate_only",
        "official_bm1_bm7_grid_including_pml": grid,
        "official_bm1_bm7_voxel_count": voxel_count,
        "single_float32_field_bytes": voxel_count * 4,
        "single_float64_field_bytes": voxel_count * 8,
        "official_archive_size_bytes": archive_size,
        "official_archive_size_gib": archive_size / (1024**3),
        "official_bm1_bm3_bm4_reference_subset_acquired": subset_acquired,
        "reference_subset_sha256": (
            {
                entry["archive_name"]: entry["sha256"]
                for entry in reference_manifest["extracted_entries"]
            }
            if subset_acquired
            else {}
        ),
        "pressure_execution_allowed_now": False,
        "blockers": blockers,
        "next_safe_action": (
            "Implement and verify the exact focused-bowl source and comparison-grid "
            "export, then run a case-specific solver dry-run."
            if subset_acquired
            else "Acquire only the named BM1/BM3/BM4 reference files or authorize "
            "the full archive, then run a case-specific solver dry-run."
        ),
        "prohibited_inferences": contract["blocked_claims"],
    }


def command_compare(args: argparse.Namespace) -> int:
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    if args.source != 1:
        raise NotImplementedError(
            "This PUB.1 checkpoint is frozen to the focused-bowl source (source=1). "
            "The piston profile conventions must be implemented and tested separately."
        )
    reference_path = Path(args.reference).resolve()
    candidate_path = Path(args.candidate).resolve()
    reference = load_array(reference_path, args.dataset_key)
    candidate = load_array(candidate_path, args.dataset_key)
    order = parse_axis_order(args.candidate_axis_order)
    if order is not None:
        candidate = np.transpose(candidate, order)
    brain_mask = None
    if args.brain_mask:
        brain_mask = load_array(Path(args.brain_mask).resolve(), args.mask_key)
    reference = validate_amplitude(reference, "reference")
    candidate = validate_amplitude(candidate, "candidate")
    if reference.shape != candidate.shape:
        raise ValueError(
            f"shape mismatch: reference {reference.shape}, candidate {candidate.shape}"
        )
    mask = build_analysis_mask(
        reference.shape,
        args.benchmark,
        args.source,
        contract,
        brain_mask,
    )
    dx_mm = float(contract["official_discretization"]["comparison_dx_mm"])
    report = {
        "schema_version": "1.0",
        "contract_id": contract["contract_id"],
        "claim_level": "engineering_benchmark_comparison",
        "benchmark": f"BM{args.benchmark}",
        "source": args.source,
        "supported_source_scope": "focused_bowl_source_1_only",
        "reference_model": args.reference_model,
        "candidate_model": args.candidate_model,
        "comparison_dx_mm": dx_mm,
        "shape": list(reference.shape),
        "mask_voxels": int(np.count_nonzero(mask)),
        "candidate_axis_order": list(order) if order is not None else [0, 1, 2],
        "inputs": {
            "reference": {
                "path": str(reference_path),
                "sha256": sha256_file(reference_path),
                "dataset_key": args.dataset_key,
            },
            "candidate": {
                "path": str(candidate_path),
                "sha256": sha256_file(candidate_path),
                "dataset_key": args.dataset_key,
            },
        },
        "metrics": compare_fields(
            reference,
            candidate,
            mask,
            dx_mm,
            include_volume=args.benchmark >= 7,
        ),
        "limitations": [
            "Agreement is an engineering benchmark result, not clinical validation.",
            "No implicit resampling or coordinate correction was applied.",
        ],
    }
    output = Path(args.output).resolve()
    _json_dump(output, report)
    print(json.dumps({"status": "completed", "report": str(output)}))
    return 0


def command_dry_run(args: argparse.Namespace) -> int:
    contract = load_contract(Path(args.contract).resolve())
    reference_manifest = None
    if args.reference_manifest:
        reference_manifest = json.loads(
            Path(args.reference_manifest).resolve().read_text(encoding="utf-8")
        )
    output = Path(args.output).resolve()
    _json_dump(output, build_dry_run(contract, reference_manifest))
    print(json.dumps({"status": "blocked_before_pressure_execution", "report": str(output)}))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    candidate_path = Path(args.candidate).resolve()
    candidate = validate_amplitude(
        load_array(candidate_path, args.dataset_key),
        "candidate",
    )
    mask = build_analysis_mask(
        candidate.shape,
        args.benchmark,
        args.source,
        contract,
    )
    validation = validate_candidate_region(candidate, mask)
    report = {
        "schema_version": "1.0",
        "contract_id": contract["contract_id"],
        "claim_level": args.claim_level,
        "benchmark": f"BM{args.benchmark}",
        "source": args.source,
        "candidate": {
            "path": str(candidate_path),
            "sha256": sha256_file(candidate_path),
            "dataset_key": args.dataset_key,
            "shape": list(candidate.shape),
        },
        "validation": validation,
        "limitations": [
            "This validates field integrity and transmitted-region presence only.",
            "It is not an official-reference agreement or convergence result.",
        ],
    }
    output = Path(args.output).resolve()
    _json_dump(output, report)
    print(json.dumps({"status": validation["status"], "report": str(output)}))
    return 0 if validation["status"] == "passed" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--reference", required=True)
    compare_parser.add_argument("--candidate", required=True)
    compare_parser.add_argument("--benchmark", type=int, required=True)
    compare_parser.add_argument("--source", type=int, choices=(1, 2), required=True)
    compare_parser.add_argument("--reference-model", required=True)
    compare_parser.add_argument("--candidate-model", required=True)
    compare_parser.add_argument("--dataset-key", default=DEFAULT_DATASET_KEY)
    compare_parser.add_argument("--brain-mask")
    compare_parser.add_argument("--mask-key", default="brain_mask")
    compare_parser.add_argument("--candidate-axis-order")
    compare_parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    compare_parser.add_argument("--output", required=True)
    compare_parser.set_defaults(function=command_compare)

    dry_parser = subparsers.add_parser("dry-run")
    dry_parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    dry_parser.add_argument("--reference-manifest")
    dry_parser.add_argument("--output", required=True)
    dry_parser.set_defaults(function=command_dry_run)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--candidate", required=True)
    validate_parser.add_argument("--benchmark", type=int, required=True)
    validate_parser.add_argument("--source", type=int, choices=(1, 2), required=True)
    validate_parser.add_argument("--dataset-key", default=DEFAULT_DATASET_KEY)
    validate_parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    validate_parser.add_argument(
        "--claim-level",
        default="workflow_smoke_only",
    )
    validate_parser.add_argument("--output", required=True)
    validate_parser.set_defaults(function=command_validate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.function(args))


if __name__ == "__main__":
    raise SystemExit(main())
