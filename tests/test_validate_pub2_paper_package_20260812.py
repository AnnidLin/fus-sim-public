import unittest

from validate_pub2_paper_package_20260812 import sha256


class Pub2PaperPackageValidatorTests(unittest.TestCase):
    def test_sha256_is_deterministic(self):
        from pathlib import Path
        path = Path(__file__)
        self.assertEqual(sha256(path), sha256(path))


if __name__ == "__main__":
    unittest.main()
