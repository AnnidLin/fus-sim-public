from __future__ import annotations

import unittest

from analyze_trajectory_geometry_reuse_gate_20260722 import (
    by_key,
    fractional_reduction,
    source_background_only,
)


class TrajectoryGeometryReuseGateTests(unittest.TestCase):
    def test_by_key_requires_one_match(self) -> None:
        rows = [{"id": "a", "value": 1}, {"id": "b", "value": 2}]
        self.assertEqual(by_key(rows, "id", "b")["value"], 2)
        with self.assertRaises(ValueError):
            by_key(rows, "id", "c")

    def test_fractional_reduction(self) -> None:
        self.assertAlmostEqual(fractional_reduction(2.0, 1.5), 0.25)
        with self.assertRaises(ValueError):
            fractional_reduction(0.0, 1.0)

    def test_source_background_only(self) -> None:
        self.assertTrue(source_background_only({"0": 100}))
        self.assertFalse(source_background_only({"0": 99, "1": 1}))
        self.assertFalse(source_background_only({}))


if __name__ == "__main__":
    unittest.main()
