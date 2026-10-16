from __future__ import annotations

import copy
import unittest

from bbb_planning_contract import ContractError, load_json
from bbb_public_case_input_contract import DEFAULT_EXAMPLE, DEFAULT_SCHEMA, validate_contract


class BBBPublicCaseInputContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(DEFAULT_SCHEMA)
        cls.example = load_json(DEFAULT_EXAMPLE)

    def changed(self) -> dict:
        return copy.deepcopy(self.example)

    def test_current_public_example_passes_with_file_hashes(self) -> None:
        validate_contract(self.changed(), self.schema, verify_file_hashes=True)

    def test_expert_is_not_required_for_engineering_sandbox(self) -> None:
        contract = self.changed()
        validate_contract(contract, self.schema)
        self.assertFalse(contract["readiness_gates"]["expert_required_for_engineering_sandbox"])
        self.assertNotIn(
            "expert_human_registration_qc_missing",
            contract["readiness_gates"]["engineering_blockers"],
        )
        self.assertIn(
            "expert_human_registration_qc_missing",
            contract["readiness_gates"]["anatomical_or_clinical_blockers"],
        )

    def test_rejects_clinical_patient_claim(self) -> None:
        contract = self.changed()
        contract["subject"]["clinical_patient_data"] = True
        with self.assertRaisesRegex(ContractError, "expected constant False"):
            validate_contract(contract, self.schema)

    def test_rejects_proxy_called_a_lesion(self) -> None:
        contract = self.changed()
        contract["target_roi"]["semantic_boundary"] = "tumor"
        with self.assertRaisesRegex(ContractError, "expected constant"):
            validate_contract(contract, self.schema)

    def test_rejects_proxy_target_coordinate_mismatch(self) -> None:
        contract = self.changed()
        contract["trajectory_screening"]["target_ijk"][0] += 1
        with self.assertRaisesRegex(ContractError, "must equal proxy ROI center"):
            validate_contract(contract, self.schema)

    def test_rejects_missing_hardware_blocker(self) -> None:
        contract = self.changed()
        contract["readiness_gates"]["engineering_blockers"].remove("hardware_geometry_missing")
        with self.assertRaisesRegex(ContractError, "too few items|missing required safety gates"):
            validate_contract(contract, self.schema)

    def test_rejects_mixed_source_claimed_as_background_only(self) -> None:
        contract = self.changed()
        contract["trajectory_screening"]["source_material_semantics"] = (
            "background_only_external_source"
        )
        with self.assertRaisesRegex(ContractError, "expected constant"):
            validate_contract(contract, self.schema)

    def test_rejects_skull_count_in_mixed_source(self) -> None:
        contract = self.changed()
        contract["trajectory_screening"]["source_label_counts"]["skull"] = 1
        with self.assertRaisesRegex(ContractError, "expected constant 0"):
            validate_contract(contract, self.schema)

    def test_rejects_new_simulation_permission(self) -> None:
        contract = self.changed()
        contract["readiness_gates"]["standard_simulation_execution_permitted"] = True
        with self.assertRaisesRegex(ContractError, "expected constant False"):
            validate_contract(contract, self.schema)

    def test_rejects_model_hash_mismatch(self) -> None:
        contract = self.changed()
        contract["acoustic_model"]["model_sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "SHA256 mismatch"):
            validate_contract(contract, self.schema, verify_file_hashes=True)

    def test_rejects_dry_run_count_drift(self) -> None:
        contract = self.changed()
        contract["trajectory_screening"]["source_label_counts"]["soft_tissue"] += 1
        with self.assertRaisesRegex(ContractError, "do not match"):
            validate_contract(contract, self.schema, verify_file_hashes=True)


if __name__ == "__main__":
    unittest.main()
