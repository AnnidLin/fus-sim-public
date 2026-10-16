from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_project_file(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8-sig")


class PaperExecutionMasterPlanTests(unittest.TestCase):
    def test_controlling_documents_exist_and_freeze_primary_endpoints(self) -> None:
        master_plan = read_project_file("PAPER_EXECUTION_MASTER_PLAN.md")
        analysis_freeze = read_project_file("paper/PAPER_ANALYSIS_FREEZE_20260731.md")
        evidence_map = read_project_file("paper/MANUSCRIPT_EVIDENCE_MAP.md")

        self.assertIn("当前唯一主动执行计划", master_plan)
        self.assertIn("target_window_peak / global_peak", master_plan)
        self.assertIn("global peak 到预定目标的欧氏距离", master_plan)
        self.assertIn("Target-window peak divided by global peak", analysis_freeze)
        self.assertIn("Euclidean distance from the global peak", analysis_freeze)
        self.assertIn("Figure 2", evidence_map)
        self.assertIn("PUB.1", evidence_map)

    def test_entry_documents_enforce_the_paper_plan(self) -> None:
        agents = read_project_file("AGENTS.md")
        snapshot = read_project_file("AI_PROJECT_SNAPSHOT.md")
        todo = read_project_file("AI_TODO.md")
        readme = read_project_file("README.md")

        for content in (agents, snapshot, todo, readme):
            self.assertIn("PAPER_EXECUTION_MASTER_PLAN.md", content)

        self.assertIn("Every new task must map to a `PUB.x` gate", agents)
        self.assertIn("The only active execution plan", todo)
        self.assertIn("| PUB.0 |", todo)
        self.assertIn("🟢 done", todo)
        self.assertIn("PUB.1 is complete", snapshot)
        self.assertIn("PUB.2 fresh reference pair", snapshot)
        self.assertIn("dx0.75/PML16 baseline observation", snapshot)
        self.assertIn("Do not execute another matrix cell", snapshot)

    def test_superseded_plans_are_marked_historical(self) -> None:
        acoustic_plan = read_project_file("ACOUSTIC_PAPER_GRADE_EXECUTION_PLAN.md")
        bbb_plan = read_project_file("BBB_SIMULATION_STAGE_PLAN_20260720.md")
        next_phase_plan = read_project_file("NEXT_PHASE_EXECUTION_PLAN.md")

        self.assertIn("Historical supporting plan", acoustic_plan)
        self.assertIn("历史阶段计划", bbb_plan)
        self.assertIn("Historical plan only", next_phase_plan)
        for content in (acoustic_plan, bbb_plan, next_phase_plan):
            self.assertIn("PAPER_EXECUTION_MASTER_PLAN.md", content)


if __name__ == "__main__":
    unittest.main()
