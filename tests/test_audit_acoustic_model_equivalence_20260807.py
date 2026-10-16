from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

import audit_acoustic_model_equivalence as audit


def write_model(
    path: Path,
    *,
    sound_speed_delta: float = 0.0,
    status: str = "inferred_from_binary_materials",
) -> None:
    np.savez_compressed(
        path,
        labels=np.array([[0, 2]], dtype=np.uint8),
        hu=np.array([[-1000.0, 500.0]], dtype=np.float32),
        sound_speed=np.array(
            [[1500.0, 2800.0 + sound_speed_delta]], dtype=np.float32
        ),
        density=np.array([[1000.0, 1900.0]], dtype=np.float32),
        alpha_coeff=np.array([[0.002, 8.0]], dtype=np.float32),
        dx_m=np.array(0.00075, dtype=np.float32),
        target_index_ijk=np.array([1, 2, 3], dtype=np.int32),
        original_spacing_m_xyz=np.array(
            [0.000390625, 0.000390625, 0.005], dtype=np.float32
        ),
        alpha_power=np.array(1.5, dtype=np.float32),
        alpha_mode=np.array("", dtype="<U1"),
        alpha_unit_semantics=np.array("dB/MHz^1.5/cm", dtype="<U16"),
        alpha_coeff_kind=np.array("binary_threshold_alpha0", dtype="<U32"),
        alpha_source_route=np.array("simple_hu300", dtype="<U16"),
        alpha_semantics_status=np.array(status, dtype="<U40"),
        alpha_pressure_allowed=np.array(False, dtype=np.bool_),
        alpha_pressure_allowed_state=np.array("unspecified", dtype="<U16"),
    )


class AcousticModelEquivalenceAuditTests(unittest.TestCase):
    def test_equal_physical_arrays_and_expected_metadata_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = root / "reference.npz"
            candidate = root / "candidate.npz"
            write_model(reference)
            write_model(candidate)
            report = audit.audit_model_equivalence(reference, candidate)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["physical_arrays_equal"])
        self.assertTrue(report["candidate_alpha_metadata_matches"])
        self.assertFalse(report["pressure_execution_authorized"])

    def test_physical_array_difference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = root / "reference.npz"
            candidate = root / "candidate.npz"
            write_model(reference)
            write_model(candidate, sound_speed_delta=1.0)
            report = audit.audit_model_equivalence(reference, candidate)
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["arrays"]["sound_speed"]["equal"])
        self.assertEqual(
            report["arrays"]["sound_speed"]["max_abs_difference"],
            1.0,
        )

    def test_metadata_difference_fails_without_hiding_array_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = root / "reference.npz"
            candidate = root / "candidate.npz"
            write_model(reference)
            write_model(candidate, status="review_pending")
            report = audit.audit_model_equivalence(reference, candidate)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["physical_arrays_equal"])
        self.assertFalse(report["candidate_alpha_metadata_matches"])


if __name__ == "__main__":
    unittest.main()
