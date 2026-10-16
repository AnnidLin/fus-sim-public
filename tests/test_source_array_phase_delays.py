import unittest

import numpy as np

from simulate_source_array_focus import (
    LoadedModel,
    SourceArrayConfig,
    compute_patch_phase_offsets,
)


def make_model() -> LoadedModel:
    shape = (11, 1, 1)
    return LoadedModel(
        labels=None,
        sound_speed=np.full(shape, 1000.0, dtype=np.float32),
        density=np.full(shape, 1000.0, dtype=np.float32),
        alpha_coeff=np.zeros(shape, dtype=np.float32),
        dx_m=1e-3,
        target_index_ijk=np.array([10, 0, 0]),
        source_center_index_ijk=np.array([0, 0, 0]),
        entry_index_ijk=None,
        beam_axis=np.array([10, 0, 0]),
        entry_plan=None,
        crop_origin_ijk=np.zeros(3, dtype=np.int32),
        source_model_shape=shape,
    )


class SourceArrayPhaseDelayTests(unittest.TestCase):
    def test_farther_patch_emits_before_nearer_patch(self) -> None:
        model = make_model()
        source_mask = np.zeros(model.sound_speed.shape, dtype=bool)
        source_mask[0, 0, 0] = True
        source_mask[5, 0, 0] = True
        patch_ids = np.array([0, 1], dtype=int)
        config = SourceArrayConfig(
            array_elements_y=1,
            array_elements_z=2,
            phase_model="geometric_soft_tissue",
            phase_sound_speed_m_s=1000.0,
            simulation_time_s=20e-6,
        )

        offsets = compute_patch_phase_offsets(model, config, source_mask, patch_ids, 1e-6)

        np.testing.assert_array_equal(offsets, [0, 5])

    def test_single_patch_has_zero_relative_delay(self) -> None:
        model = make_model()
        source_mask = np.zeros(model.sound_speed.shape, dtype=bool)
        source_mask[0, 0, 0] = True
        config = SourceArrayConfig(
            array_elements_y=1,
            array_elements_z=1,
            phase_model="geometric_soft_tissue",
            phase_sound_speed_m_s=1000.0,
            simulation_time_s=20e-6,
        )

        offsets = compute_patch_phase_offsets(
            model,
            config,
            source_mask,
            np.array([0], dtype=int),
            1e-6,
        )

        np.testing.assert_array_equal(offsets, [0])


if __name__ == "__main__":
    unittest.main()
