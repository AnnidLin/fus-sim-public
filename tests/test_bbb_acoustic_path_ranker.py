from __future__ import annotations

import copy
import json
import unittest

from bbb_acoustic_path_ranker import EVIDENCE, FULLWAVE, SELECTION, minmax, rank_paths, standoff_penalty, transmission_loss


class BBBAcousticPathRankerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        cls.fullwave = json.loads(FULLWAVE.read_text(encoding="utf-8"))
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_helpers_have_expected_direction(self) -> None:
        self.assertEqual(minmax([2.0, 2.0]), [0.0, 0.0])
        self.assertEqual(minmax([1.0, 3.0]), [0.0, 1.0])
        self.assertEqual(standoff_penalty(15.0), 0.0)
        self.assertGreater(standoff_penalty(5.0), 0.0)
        self.assertGreater(transmission_loss(6.0, 8.0), transmission_loss(4.5, 8.0))

    def test_frozen_ranking_is_deterministic_and_has_counterexample(self) -> None:
        first = rank_paths(self.selection, self.fullwave, self.evidence)
        second = rank_paths(self.selection, self.fullwave, self.evidence)
        self.assertEqual(first, second)
        self.assertEqual(first["candidate_count"], 3)
        self.assertEqual(first["eligible_count"], 3)
        self.assertTrue(first["shortest_is_not_lowest_validated_cost"])
        self.assertEqual(first["lowest_validated_acoustic_cost_path"], "offset_y+12p5_z-15p0")

    def test_hard_gate_excludes_non_background_source(self) -> None:
        selection = copy.deepcopy(self.selection)
        selection["selected"][0]["source_label_counts"] = {"0": 5107, "1": 1}
        result = rank_paths(selection, self.fullwave, self.evidence)
        self.assertEqual(result["eligible_count"], 2)

    def test_invalid_weight_sum_is_rejected(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["proxy_weights"]["skull_path_length"] = 0.5
        with self.assertRaisesRegex(ValueError, "sum to one"):
            rank_paths(self.selection, self.fullwave, evidence)


if __name__ == "__main__":
    unittest.main()
