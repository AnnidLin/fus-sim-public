from __future__ import annotations

import copy
import unittest

from bbb_planning_contract import (
    ContractError,
    DEFAULT_EXAMPLE,
    DEFAULT_SCHEMA,
    load_json,
    validate_contract,
)


class BBBPlanningContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(DEFAULT_SCHEMA)
        cls.example = load_json(DEFAULT_EXAMPLE)

    def changed(self) -> dict:
        return copy.deepcopy(self.example)

    def test_frozen_example_passes_with_file_hashes(self) -> None:
        validate_contract(self.changed(), self.schema, verify_file_hashes=True)

    def test_rejects_unknown_top_level_field(self) -> None:
        plan = self.changed()
        plan["unexpected"] = True
        with self.assertRaisesRegex(ContractError, "unexpected fields"):
            validate_contract(plan, self.schema)

    def test_rejects_coordinate_mismatch(self) -> None:
        plan = self.changed()
        plan["target_roi"]["center_local_ijk"][0] += 1
        with self.assertRaisesRegex(ContractError, "coordinate mismatch"):
            validate_contract(plan, self.schema)

    def test_rejects_out_of_bounds_roi(self) -> None:
        plan = self.changed()
        plan["target_roi"]["center_full_ijk"] = [267, 136, 105]
        plan["target_roi"]["center_local_ijk"] = [230, 36, 26]
        plan["transducer_plan"]["target_full_ijk"] = [267, 136, 105]
        with self.assertRaisesRegex(ContractError, "outside"):
            validate_contract(plan, self.schema)

    def test_rejects_empty_roi(self) -> None:
        plan = self.changed()
        plan["target_roi"]["voxel_count"] = 0
        with self.assertRaisesRegex(ContractError, "below minimum"):
            validate_contract(plan, self.schema)

    def test_rejects_synthetic_roi_claimed_as_anatomical(self) -> None:
        plan = self.changed()
        plan["target_roi"]["anatomical_status"] = "registered_anatomical"
        with self.assertRaisesRegex(ContractError, "cannot be marked as anatomical"):
            validate_contract(plan, self.schema)

    def test_rejects_uncomputed_non_null_metric(self) -> None:
        plan = self.changed()
        plan["plan_metrics"]["mechanical_index"] = 0.5
        with self.assertRaisesRegex(ContractError, "must all be null"):
            validate_contract(plan, self.schema)

    def test_rejects_clinical_claim_flags(self) -> None:
        plan = self.changed()
        plan["exposure_protocol"]["clinical_dose_claim"] = True
        with self.assertRaisesRegex(ContractError, "expected constant False"):
            validate_contract(plan, self.schema)

    def test_rejects_nonpositive_frequency(self) -> None:
        plan = self.changed()
        plan["transducer_plan"]["frequency_hz"] = 0
        with self.assertRaisesRegex(ContractError, "exclusive minimum"):
            validate_contract(plan, self.schema)

    def test_rejects_fabricated_pulse_train_on_calibration_reference(self) -> None:
        plan = self.changed()
        plan["exposure_protocol"]["prf_hz"] = 10.0
        with self.assertRaisesRegex(ContractError, "must not invent"):
            validate_contract(plan, self.schema)


if __name__ == "__main__":
    unittest.main()
