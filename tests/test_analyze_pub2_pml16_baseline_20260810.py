from __future__ import annotations

import unittest

import numpy as np

import analyze_pub2_pml16_baseline_20260810 as module
import validate_pub2_pml16_baseline_package_20260810 as validator


class Pml16BaselineAnalysisTests(unittest.TestCase):
    def test_common_views_align_by_full_model_origin(self) -> None:
        reference = {"field": np.ones((3, 2, 2)), "origin": np.array([4, 5, 6])}
        candidate = {"field": np.zeros((5, 2, 2)), "origin": np.array([2, 5, 6])}
        candidate["field"][2:, :, :] = 1
        left, right, alignment = module.common_views(reference, candidate)
        np.testing.assert_array_equal(left, right)
        self.assertEqual(alignment["shape"], [3, 2, 2])
        self.assertEqual(alignment["candidate_slices_start_ijk"], [2, 0, 0])

    def test_compare_configs_requires_only_pml_change(self) -> None:
        reference = {key: "same" for key in module.CONFIG_KEYS}
        candidate = dict(reference)
        reference["pml_size"] = 12
        candidate["pml_size"] = 16
        result = module.compare_configs(reference, candidate)
        self.assertTrue(result["only_pml_size_changed"])
        candidate["cfl"] = 0.1
        self.assertFalse(module.compare_configs(reference, candidate)["only_pml_size_changed"])

    def test_device_numeric_values_skip_sampler_warmup_null(self) -> None:
        rows = [{"equivalent_cores": None}, {"equivalent_cores": 0.9}]
        self.assertEqual(validator.numeric_values(rows, "equivalent_cores"), [0.9])


if __name__ == "__main__":
    unittest.main()
