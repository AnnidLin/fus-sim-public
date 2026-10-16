from __future__ import annotations

import unittest

from windows_process_tree_guard import (
    GuardThresholds,
    breach_reasons,
)


class WindowsProcessTreeGuardTests(unittest.TestCase):
    def test_no_breach_at_or_below_limits(self) -> None:
        sample = {
            "equivalent_cores": 6.5,
            "working_set_gib": 12.0,
            "system_free_memory_gib": 4.0,
        }
        self.assertEqual(
            breach_reasons(sample, GuardThresholds()),
            [],
        )

    def test_each_limit_has_distinct_reason(self) -> None:
        sample = {
            "equivalent_cores": 6.6,
            "working_set_gib": 12.1,
            "system_free_memory_gib": 3.9,
        }
        self.assertEqual(
            breach_reasons(sample, GuardThresholds()),
            [
                "equivalent_cpu_cores",
                "process_tree_working_set",
                "system_free_memory",
            ],
        )

    def test_first_cpu_sample_can_be_none(self) -> None:
        sample = {
            "equivalent_cores": None,
            "working_set_gib": 1.0,
            "system_free_memory_gib": 10.0,
        }
        self.assertEqual(
            breach_reasons(sample, GuardThresholds()),
            [],
        )


if __name__ == "__main__":
    unittest.main()
