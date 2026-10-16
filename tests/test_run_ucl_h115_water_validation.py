import unittest
from pathlib import Path

import run_ucl_h115_water_validation as runner


class UclH115RunnerTests(unittest.TestCase):
    def test_command_is_single_h115_cpp_configuration(self) -> None:
        runner.configure(runner.ROOT / "outputs" / "ucl_h115_water_model_dx0p5_20260812", runner.ROOT / "outputs" / "evidence_briefs" / "ucl_h115_water_validation_20260818" / "evidence_brief.json", 16)
        value = runner.command(Path("test-output"), dry_run=True)
        self.assertIn("--backend", value)
        self.assertIn("cpp", value)
        self.assertIn("--dry-run-quality", value)
        self.assertEqual(value[value.index("--frequency-hz") + 1], "270000")
        self.assertEqual(value[value.index("--pml-size") + 1], "16")
        self.assertEqual(value[value.index("--cfl") + 1], "0.1")

    def test_command_accepts_grid_sensitivity_configuration(self) -> None:
        runner.configure(Path("candidate-model"), Path("candidate-brief.json"), 27, full_model=True)
        value = runner.command(Path("candidate-output"), dry_run=True)
        self.assertEqual(value[value.index("--pml-size") + 1], "27")
        self.assertTrue(value[value.index("--model") + 1].endswith("candidate-model\\acoustic_model_3d.npz"))
        self.assertIn("--full", value)

    def test_command_accepts_frozen_nominal_source_geometry(self) -> None:
        runner.configure(
            Path("nominal-model"), Path("nominal-brief.json"), 16,
            full_model=True, radius_mm=64.0, aperture_mm=64.0,
        )
        value = runner.command(Path("nominal-output"), dry_run=True)
        self.assertEqual(value[value.index("--radius-mm") + 1], "64")
        self.assertEqual(value[value.index("--aperture-mm") + 1], "64")


if __name__ == "__main__":
    unittest.main()
