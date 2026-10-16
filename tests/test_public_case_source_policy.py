from __future__ import annotations

import unittest

from public_case_source_policy import (
    BACKGROUND_ONLY,
    MIXED_MEDIUM,
    SKULL_INVALID,
    classify_source_materials,
    enforce_source_material_policy,
)


class PublicCaseSourcePolicyTests(unittest.TestCase):
    def test_classifies_background_only_source(self) -> None:
        self.assertEqual(classify_source_materials({"0": 347}), BACKGROUND_ONLY)

    def test_classifies_mixed_medium_source(self) -> None:
        self.assertEqual(
            classify_source_materials({"0": 180, "1": 169}),
            MIXED_MEDIUM,
        )

    def test_classifies_skull_overlap_as_invalid(self) -> None:
        self.assertEqual(
            classify_source_materials({"0": 341, "1": 503, "2": 5}),
            SKULL_INVALID,
        )

    def test_default_policy_rejects_soft_tissue_points(self) -> None:
        with self.assertRaisesRegex(ValueError, "explicit mixed-medium"):
            enforce_source_material_policy(
                {"0": 180, "1": 169},
                preset="quick",
            )

    def test_explicit_quick_screening_accepts_mixed_medium(self) -> None:
        self.assertEqual(
            enforce_source_material_policy(
                {"0": 180, "1": 169},
                preset="quick",
                allow_mixed_medium_screening=True,
            ),
            MIXED_MEDIUM,
        )

    def test_standard_rejects_mixed_medium_even_when_explicit(self) -> None:
        with self.assertRaisesRegex(ValueError, "quick engineering screening"):
            enforce_source_material_policy(
                {"0": 180, "1": 169},
                preset="standard",
                allow_mixed_medium_screening=True,
            )

    def test_skull_overlap_is_always_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlaps skull"):
            enforce_source_material_policy(
                {"0": 341, "1": 503, "2": 5},
                preset="quick",
                allow_mixed_medium_screening=True,
            )


if __name__ == "__main__":
    unittest.main()
