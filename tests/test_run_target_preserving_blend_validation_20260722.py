from __future__ import annotations

import unittest

from run_target_preserving_blend_validation_20260722 import command


class TargetPreservingBlendRunnerTests(unittest.TestCase):
    def test_command_is_frozen_refocus(self) -> None:
        cmd = command(False)
        self.assertEqual(cmd[cmd.index("--stage") + 1], "refocus")
        self.assertEqual(cmd[cmd.index("--source-pressure-pa") + 1], "1000000")
        self.assertIn("--normalize", cmd)
        self.assertNotIn("--dry-run-quality", cmd)

    def test_dry_run_adds_only_quality_flag(self) -> None:
        self.assertEqual(command(True)[:-1], command(False))
        self.assertEqual(command(True)[-1], "--dry-run-quality")


if __name__ == "__main__":
    unittest.main()
