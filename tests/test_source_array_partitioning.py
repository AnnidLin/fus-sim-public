import unittest

import numpy as np

from simulate_source_array_focus import (
    LoadedModel,
    SourceArrayConfig,
    build_source_array_mask,
    normalize_alpha_pressure_permission,
)


class SourceArrayPartitioningTests(unittest.TestCase):
    def test_shallow_bowl_uses_two_dimensional_patch_grid(self) -> None:
        shape = (126, 54, 47)
        model = LoadedModel(
            labels=np.zeros(shape, dtype=np.uint8),
            sound_speed=np.full(shape, 1500.0, dtype=np.float32),
            density=np.full(shape, 1000.0, dtype=np.float32),
            alpha_coeff=np.zeros(shape, dtype=np.float32),
            dx_m=0.75e-3,
            target_index_ijk=np.array([115, 23, 23]),
            source_center_index_ijk=np.array([16, 30, 23]),
            entry_index_ijk=np.array([37, 30, 23]),
            beam_axis=np.array([99, -7, 0]),
            entry_plan=None,
            crop_origin_ijk=np.zeros(3, dtype=np.int32),
            source_model_shape=shape,
        )
        config = SourceArrayConfig(
            transducer_radius_m=74.4353753e-3,
            aperture_diameter_m=30e-3,
            array_elements_y=15,
            array_elements_z=15,
        )

        _, patch_ids, metadata, _ = build_source_array_mask(model, config)
        active_patch_ids = np.unique(patch_ids)

        self.assertGreater(len(active_patch_ids), 100)
        self.assertGreater(len(np.unique(active_patch_ids // 15)), 1)
        self.assertGreater(len(np.unique(active_patch_ids % 15)), 1)
        self.assertEqual(sum(metadata["patch_sizes"]), metadata["source_points"])

    def test_legacy_unspecified_false_permission_is_not_explicit_denial(self) -> None:
        self.assertIsNone(
            normalize_alpha_pressure_permission(
                "missing_alpha_semantics", "unspecified", False
            )
        )

    def test_explicit_false_permission_remains_denied(self) -> None:
        self.assertFalse(
            normalize_alpha_pressure_permission("validated_profile", "denied", False)
        )


if __name__ == "__main__":
    unittest.main()
