from __future__ import annotations

import unittest

import numpy as np

from bbb_element_plan import (
    ElementPlanError,
    aggregate_element_plan,
    quantize_complex_controls,
    reconstruction_metrics,
    virtual_patch_ids,
)


class BBBElementPlanTests(unittest.TestCase):
    def test_virtual_partition_is_deterministic_and_complete(self) -> None:
        points = np.array([[0, -1, -1], [0, -1, 1], [0, 1, -1], [0, 1, 1]])
        first = virtual_patch_ids(points, np.array([0, 0, 0]), np.array([1, 0, 0]), 2, 2)
        second = virtual_patch_ids(points, np.array([0, 0, 0]), np.array([1, 0, 0]), 2, 2)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first.shape, (4,))
        self.assertTrue(np.all(first >= 0))

    def test_identical_weights_reconstruct_exactly(self) -> None:
        points = np.array([[0, 0, 0], [0, 1, 0], [0, 2, 0]])
        weights = np.array([1 + 1j, 1 + 1j, 1 + 1j])
        records, expanded = aggregate_element_plan(weights, points, np.array([0, 0, 0]))
        np.testing.assert_allclose(expanded, weights)
        self.assertEqual(records[0]["point_count"], 3)
        self.assertAlmostEqual(reconstruction_metrics(weights, expanded)["relative_complex_l2_error"], 0.0)

    def test_point_counts_are_conserved(self) -> None:
        points = np.arange(18).reshape(6, 3)
        weights = np.exp(1j * np.arange(6))
        records, expanded = aggregate_element_plan(weights, points, np.array([0, 0, 1, 1, 2, 2]))
        self.assertEqual(sum(record["point_count"] for record in records), 6)
        self.assertEqual(expanded.shape, weights.shape)

    def test_quantization_is_bounded(self) -> None:
        value = quantize_complex_controls(np.array([0.2 + 0.3j, -1 + 0.2j]), 3, 4)
        self.assertLessEqual(float(np.max(np.abs(value))), 1.0 + 1e-12)
        self.assertTrue(np.all(np.isfinite(value)))

    def test_rejects_incompatible_shapes(self) -> None:
        with self.assertRaisesRegex(ElementPlanError, "incompatible"):
            aggregate_element_plan(np.ones(2), np.ones((3, 3)), np.zeros(2))


if __name__ == "__main__":
    unittest.main()
