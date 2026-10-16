from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


PHYSICAL_ARRAY_KEYS = (
    "labels",
    "hu",
    "sound_speed",
    "density",
    "alpha_coeff",
    "dx_m",
    "target_index_ijk",
    "original_spacing_m_xyz",
)

EXPECTED_ALPHA_METADATA: dict[str, Any] = {
    "alpha_power": 1.5,
    "alpha_mode": "",
    "alpha_unit_semantics": "dB/MHz^1.5/cm",
    "alpha_coeff_kind": "binary_threshold_alpha0",
    "alpha_source_route": "simple_hu300",
    "alpha_semantics_status": "inferred_from_binary_materials",
    "alpha_pressure_allowed": False,
    "alpha_pressure_allowed_state": "unspecified",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def array_sha256(array: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("utf-8"))
    digest.update(json.dumps(list(array.shape)).encode("utf-8"))
    digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def scalar_value(archive: Any, key: str) -> Any:
    if key not in archive.files:
        return None
    value = archive[key]
    if value.shape != ():
        return value.tolist()
    scalar = value.item()
    if isinstance(scalar, np.generic):
        scalar = scalar.item()
    return scalar


def audit_model_equivalence(
    reference_path: Path,
    candidate_path: Path,
    *,
    physical_keys: tuple[str, ...] = PHYSICAL_ARRAY_KEYS,
    expected_metadata: dict[str, Any] = EXPECTED_ALPHA_METADATA,
) -> dict[str, Any]:
    reference_path = reference_path.resolve()
    candidate_path = candidate_path.resolve()
    with np.load(reference_path, allow_pickle=False) as reference, np.load(
        candidate_path, allow_pickle=False
    ) as candidate:
        arrays: dict[str, dict[str, Any]] = {}
        for key in physical_keys:
            reference_present = key in reference.files
            candidate_present = key in candidate.files
            entry: dict[str, Any] = {
                "reference_present": reference_present,
                "candidate_present": candidate_present,
                "equal": False,
            }
            if reference_present and candidate_present:
                left = reference[key]
                right = candidate[key]
                equal = bool(
                    left.shape == right.shape
                    and left.dtype == right.dtype
                    and np.array_equal(left, right, equal_nan=True)
                )
                entry.update(
                    {
                        "reference_shape": list(left.shape),
                        "candidate_shape": list(right.shape),
                        "reference_dtype": str(left.dtype),
                        "candidate_dtype": str(right.dtype),
                        "reference_sha256": array_sha256(left),
                        "candidate_sha256": array_sha256(right),
                        "equal": equal,
                    }
                )
                if (
                    not equal
                    and left.shape == right.shape
                    and np.issubdtype(left.dtype, np.number)
                    and np.issubdtype(right.dtype, np.number)
                ):
                    difference = np.abs(
                        left.astype(np.float64) - right.astype(np.float64)
                    )
                    finite = difference[np.isfinite(difference)]
                    entry["max_abs_difference"] = (
                        float(np.max(finite)) if finite.size else None
                    )
            arrays[key] = entry

        metadata: dict[str, dict[str, Any]] = {}
        for key, expected in expected_metadata.items():
            actual = scalar_value(candidate, key)
            metadata[key] = {
                "expected": expected,
                "actual": actual,
                "matches": actual == expected,
            }

    arrays_equal = all(entry["equal"] for entry in arrays.values())
    metadata_matches = all(entry["matches"] for entry in metadata.values())
    return {
        "schema_version": "1.0",
        "status": "passed" if arrays_equal and metadata_matches else "failed",
        "claim_level": "model_build_equivalence_only_no_pressure",
        "reference": {
            "path": str(reference_path),
            "sha256": sha256_file(reference_path),
        },
        "candidate": {
            "path": str(candidate_path),
            "sha256": sha256_file(candidate_path),
        },
        "physical_arrays_equal": arrays_equal,
        "candidate_alpha_metadata_matches": metadata_matches,
        "arrays": arrays,
        "candidate_alpha_metadata": metadata,
        "pressure_execution_authorized": False,
        "claim_boundary": (
            "Passing proves physical-array identity plus the expected explicit "
            "alpha metadata. It does not validate pressure, convergence, "
            "accuracy, efficacy or safety."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    rows = [
        "| Array | Shape | Dtype | Equal |",
        "|---|---|---|---|",
    ]
    for key, item in report["arrays"].items():
        rows.append(
            f"| {key} | {item.get('candidate_shape')} | "
            f"{item.get('candidate_dtype')} | {item['equal']} |"
        )
    metadata_rows = [
        "| Field | Expected | Actual | Match |",
        "|---|---|---|---|",
    ]
    for key, item in report["candidate_alpha_metadata"].items():
        metadata_rows.append(
            f"| {key} | `{item['expected']}` | `{item['actual']}` | "
            f"{item['matches']} |"
        )
    return "\n".join(
        [
            "# Acoustic model equivalence audit",
            "",
            f"- Status: **{report['status']}**",
            f"- Physical arrays equal: `{report['physical_arrays_equal']}`",
            (
                "- Candidate alpha metadata matches: "
                f"`{report['candidate_alpha_metadata_matches']}`"
            ),
            "- Pressure execution authorized: **no**",
            "",
            *rows,
            "",
            *metadata_rows,
            "",
            report["claim_boundary"],
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit physical-array identity between two acoustic models."
    )
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_model_equivalence(args.reference, args.candidate)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "model_equivalence_audit.json"
    markdown_path = args.output_dir / "model_equivalence_audit.md"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "json": str(json_path.resolve()),
                "markdown": str(markdown_path.resolve()),
            }
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
