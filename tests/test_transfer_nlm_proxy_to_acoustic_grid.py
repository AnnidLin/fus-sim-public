from __future__ import annotations

import unittest

import numpy as np

from transfer_nlm_proxy_to_acoustic_grid import world_to_index


class TransferNlmProxyToAcousticGridTests(unittest.TestCase):
    def test_world_to_index_roundtrip(self) -> None:
        affine = np.asarray([[0.75, 0, 0, -120], [0, 0.75, 0, -190], [0, 0, 0.75, -230], [0, 0, 0, 1]])
        index = np.asarray([100.25, 120.5, 80.75])
        world = (affine @ np.asarray([*index, 1.0]))[:3]
        np.testing.assert_allclose(world_to_index(world, affine), index, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
