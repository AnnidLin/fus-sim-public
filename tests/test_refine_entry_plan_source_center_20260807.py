from __future__ import annotations

import unittest

import refine_entry_plan_source_center as refine


class SourceCenterRefinementTests(unittest.TestCase):
    def test_offsets_start_at_zero_and_cover_27_candidates(self) -> None:
        offsets = refine.candidate_offsets(1)
        self.assertEqual(offsets[0], (0, 0, 0))
        self.assertEqual(len(offsets), 27)
        self.assertEqual(len(set(offsets)), 27)

    def test_passing_candidates_rank_by_error_then_angle_then_offset(self) -> None:
        candidates = [
            {
                "passed": True,
                "source_physical_error_mm": 0.5,
                "beam_angle_delta_deg": 0.2,
                "offset_ijk": [1, 0, 0],
            },
            {
                "passed": True,
                "source_physical_error_mm": 0.25,
                "beam_angle_delta_deg": 0.4,
                "offset_ijk": [0, 1, 0],
            },
            {
                "passed": True,
                "source_physical_error_mm": 0.25,
                "beam_angle_delta_deg": 0.1,
                "offset_ijk": [0, 0, 1],
            },
            {
                "passed": False,
                "source_physical_error_mm": 0.0,
                "beam_angle_delta_deg": 0.0,
                "offset_ijk": [0, 0, 0],
            },
        ]
        ranked = refine.rank_passing_candidates(candidates)
        self.assertEqual(ranked[0]["offset_ijk"], [0, 0, 1])
        self.assertEqual(ranked[-1]["offset_ijk"], [1, 0, 0])
        self.assertEqual(len(ranked), 3)


if __name__ == "__main__":
    unittest.main()
