import json
import math
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import h5py
import numpy as np
from scipy.io import savemat

import analyze_itrusst_benchmark as itr


class ItrusstComparatorTests(unittest.TestCase):
    def setUp(self):
        self.contract = itr.load_contract()
        self.dx = 0.5

    @staticmethod
    def gaussian(shape=(31, 29, 35), center=(15, 14, 18), sigma=3.0):
        coordinates = np.indices(shape)
        radius2 = sum(
            (coordinates[axis] - center[axis]) ** 2 for axis in range(3)
        )
        return np.exp(-radius2 / (2.0 * sigma**2))

    def test_identical_fields_have_zero_errors(self):
        field = self.gaussian()
        mask = np.ones(field.shape, dtype=bool)
        result = itr.compare_fields(field, field.copy(), mask, self.dx, True)
        self.assertEqual(result["relative_linf_percent"], 0.0)
        self.assertEqual(result["relative_l2_percent"], 0.0)
        self.assertEqual(result["peak_difference_percent"], 0.0)
        self.assertEqual(result["focal_position_difference_mm"], 0.0)
        self.assertEqual(
            result["reference_minus_6db_volume_mm3"],
            result["candidate_minus_6db_volume_mm3"],
        )

    def test_scaled_candidate_has_expected_errors(self):
        field = self.gaussian()
        mask = np.ones(field.shape, dtype=bool)
        result = itr.compare_fields(field, 1.1 * field, mask, self.dx, False)
        self.assertAlmostEqual(result["relative_linf_percent"], 10.0, places=10)
        self.assertAlmostEqual(result["relative_l2_percent"], 10.0, places=10)
        self.assertAlmostEqual(result["peak_difference_percent"], 10.0, places=10)
        self.assertEqual(result["focal_position_difference_mm"], 0.0)

    def test_shifted_candidate_reports_half_millimeter(self):
        reference = self.gaussian()
        candidate = self.gaussian(center=(16, 14, 18))
        mask = np.ones(reference.shape, dtype=bool)
        result = itr.compare_fields(reference, candidate, mask, self.dx, False)
        self.assertEqual(result["reference_peak_index"], [15, 14, 18])
        self.assertEqual(result["candidate_peak_index"], [16, 14, 18])
        self.assertAlmostEqual(result["focal_position_difference_mm"], 0.5)

    def test_interpolated_fwhm(self):
        profile = [0.0, 0.25, 1.0, 0.25, 0.0]
        self.assertAlmostEqual(itr.interpolated_fwhm(profile, 2), 4.0 / 3.0)
        self.assertTrue(math.isnan(itr.interpolated_fwhm([1, 1, 1], 1)))

    def test_bm1_excludes_source_side_and_bm3_uses_brain_start(self):
        shape = (5, 100)
        bm1 = itr.build_analysis_mask(shape, 1, 1, self.contract)
        self.assertFalse(np.any(bm1[:, :19]))
        self.assertTrue(np.all(bm1[:, 19:]))
        bm3 = itr.build_analysis_mask(shape, 3, 1, self.contract)
        self.assertFalse(np.any(bm3[:, :74]))
        self.assertTrue(np.all(bm3[:, 74:]))

    def test_bm4_contract_freezes_all_planar_layers(self):
        layers = self.contract["benchmark_geometry"]["BM4"]["layers"]
        self.assertEqual(
            [
                (
                    layer["material"],
                    layer["start_mm"],
                    layer["stop_mm"],
                )
                for layer in layers
            ],
            [
                ("water", 0.0, 26.0),
                ("skin", 26.0, 30.0),
                ("cortical_bone", 30.0, 31.5),
                ("trabecular_bone", 31.5, 35.5),
                ("cortical_bone", 35.5, 36.5),
                ("brain", 36.5, 120.0),
            ],
        )
        self.assertEqual(layers[2]["role"], "outer_table")
        self.assertEqual(layers[4]["role"], "inner_table")

    def test_planar_field_metrics(self):
        x, z = np.indices((41, 61))
        reference = np.exp(-((x - 20) ** 2 + (z - 35) ** 2) / 18.0)
        candidate = np.exp(-((x - 21) ** 2 + (z - 35) ** 2) / 18.0)
        mask = np.ones(reference.shape, dtype=bool)
        result = itr.compare_fields(reference, candidate, mask, self.dx, False)
        self.assertEqual(result["reference_peak_index"], [20, 35])
        self.assertEqual(result["candidate_peak_index"], [21, 35])
        self.assertEqual(result["focal_position_difference_mm"], 0.5)
        self.assertGreater(result["reference_widths"]["axial_minus_6db_mm"], 0)

    def test_candidate_region_validation_requires_transmitted_pressure(self):
        field = np.zeros((5, 100), dtype=float)
        field[2, 80] = 4.0
        mask = itr.build_analysis_mask(field.shape, 4, 1, self.contract)
        report = itr.validate_candidate_region(field, mask)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["positive_voxels"], 1)
        self.assertEqual(report["peak_pa"], 4.0)
        self.assertEqual(report["peak_index"], [2, 80])

    def test_candidate_region_validation_fails_when_pressure_is_prebrain_only(self):
        field = np.zeros((5, 100), dtype=float)
        field[2, 50] = 4.0
        mask = itr.build_analysis_mask(field.shape, 4, 1, self.contract)
        report = itr.validate_candidate_region(field, mask)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["positive_voxels"], 0)

    def test_planar_benchmark_rejects_3d_field(self):
        with self.assertRaisesRegex(ValueError, "2-D"):
            itr.build_analysis_mask((5, 6, 100), 3, 1, self.contract)

    def test_bm7_requires_and_applies_brain_mask(self):
        shape = (4, 5, 100)
        with self.assertRaisesRegex(ValueError, "requires"):
            itr.build_analysis_mask(shape, 7, 1, self.contract)
        external = np.zeros(shape, dtype=np.uint8)
        external[1:3, 2:4, 80:90] = 1
        result = itr.build_analysis_mask(shape, 7, 1, self.contract, external)
        self.assertEqual(np.count_nonzero(result), 40)

    def test_largest_component_volume_ignores_smaller_component(self):
        field = np.zeros((8, 8, 8), dtype=float)
        field[1:3, 1:3, 1:3] = 1.0
        field[6, 6, 6] = 1.0
        mask = np.ones(field.shape, dtype=bool)
        volume = itr.largest_minus_6db_volume_mm3(field, mask, 0.5)
        self.assertEqual(volume, 8 * 0.5**3)

    def test_shape_mismatch_is_not_resampled(self):
        with self.assertRaisesRegex(ValueError, "shape mismatch"):
            itr.compare_fields(
                np.ones((3, 3, 3)),
                np.ones((4, 3, 3)),
                np.ones((3, 3, 3), dtype=bool),
                self.dx,
                False,
            )

    def test_load_npz_hdf5_and_mat(self):
        field = self.gaussian(shape=(7, 8, 9), center=(3, 4, 4))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            npz_path = root / "field.npz"
            h5_path = root / "field.h5"
            mat_path = root / "field.mat"
            np.savez_compressed(npz_path, p_amp=field)
            with h5py.File(h5_path, "w") as handle:
                handle.create_dataset("p_amp", data=field)
            savemat(mat_path, {"p_amp": field})
            np.testing.assert_allclose(itr.load_array(npz_path), field)
            np.testing.assert_allclose(itr.load_array(h5_path), field)
            np.testing.assert_allclose(itr.load_array(mat_path), field)

    def test_dry_run_is_explicitly_blocked(self):
        report = itr.build_dry_run(self.contract)
        self.assertFalse(report["pressure_execution_allowed_now"])
        self.assertEqual(report["status"], "blocked_before_pressure_execution")
        self.assertEqual(
            report["official_bm1_bm7_voxel_count"], 305 * 305 * 521
        )
        json.dumps(report)

    def test_dry_run_records_verified_reference_subset(self):
        manifest = {
            "payload_files_downloaded": True,
            "matched_entry_count": 3,
            "extracted_entries": [
                {"archive_name": f"BM{bm}", "sha256": str(bm)}
                for bm in (1, 3, 4)
            ],
        }
        report = itr.build_dry_run(self.contract, manifest)
        self.assertTrue(
            report["official_bm1_bm3_bm4_reference_subset_acquired"]
        )
        self.assertNotIn(
            "official_reference_subset_not_acquired", report["blockers"]
        )
        self.assertFalse(report["pressure_execution_allowed_now"])

    def test_piston_cli_is_rejected_until_profile_contract_is_implemented(self):
        arguments = Namespace(contract=str(itr.DEFAULT_CONTRACT), source=2)
        with self.assertRaisesRegex(NotImplementedError, "focused-bowl"):
            itr.command_compare(arguments)


if __name__ == "__main__":
    unittest.main()
