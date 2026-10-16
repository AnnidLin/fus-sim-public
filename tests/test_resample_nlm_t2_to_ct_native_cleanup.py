from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from resample_nlm_t2_to_ct_native import close_memmap


class ResampleNlmT2CleanupTests(unittest.TestCase):
    def test_close_memmap_releases_file_for_deletion(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "work.dat"
            data = np.memmap(path, mode="w+", dtype=np.float32, shape=(4, 4, 4))
            data[:] = 1.0
            close_memmap(data)
            path.unlink()
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
