import unittest
from unittest.mock import patch

from syndicate.learning.skill_synthesizer import SkillSynthesizer
from syndicate.learning.failure_analyzer import FailureAnalysis


class TestSkillSynthesizer(unittest.TestCase):
    def setUp(self):
        self.synthesizer = SkillSynthesizer()
        self.failure_analysis = FailureAnalysis(
            failure_type="tool_failure",
            root_cause="Bad input",
            evidence=["Step 1 failed"],
            recommended_change="Check inputs",
            confidence=0.9
        )
        self.success_analysis = FailureAnalysis(
            failure_type="none",
            root_cause="Success",
            evidence=["Score 1.0"],
            recommended_change="None",
            confidence=1.0
        )

    def test_synthesis_realistic_ci_failure(self):
        trajectory = {
            "trajectory_id": "traj-123",
            "task_id": "task-456",
            "task": {"description": "Investigate CI failure in PR"},
            "steps": [
                {"tool_name": "github_search"},
                {"tool_name": "github_search"},  # consecutive duplicate
                {"tool_name": "read_logs"},
                {"tool_name": "read_logs"},  # consecutive duplicate
            ],
            "evaluation": {"overall_score": 0.2}
        }

        skill = self.synthesizer.synthesize(self.failure_analysis, trajectory)

        self.assertEqual(skill.source_trajectory_id, "traj-123")
        self.assertEqual(skill.procedure, ["github_search", "read_logs"])
        self.assertEqual(skill.metadata["source_task_id"], "task-456")
        self.assertEqual(skill.metadata["source_evaluation"]["overall_score"], 0.2)
        self.assertEqual(skill.metadata["failure_confidence"], 0.9)
        self.assertEqual(skill.metadata["generated_by"], "deterministic_skill_synthesizer")
        self.assertTrue(skill.skill_id.startswith("tool-failure-github-search-read-logs"))

    def test_parameter_extraction_from_trajectory_evidence(self):
        trajectory = {
            "trajectory_id": "traj-evidence-1",
            "steps": [
                {
                    "tool_name": "list_workflow_runs",
                    "output": [
                        {"id": 1, "commit": "sha_111", "conclusion": "success"},
                        {"id": 2, "commit": "sha_target_222", "conclusion": "success", "jobs": {"test": {"conclusion": "failure"}}},
                    ],
                    "success": True,
                },
                {
                    "tool_name": "inspect_job_logs",
                    "output": "Job: test\nStatus: failure\nRun ID: 2\nERROR: test failure",
                    "success": True,
                },
                {
                    "tool_name": "inspect_commit",
                    "input": {"sha": "wrong_sha"},
                    "error": "Commit not found",
                    "success": False,
                },
            ],
        }

        skill = self.synthesizer.synthesize(self.failure_analysis, trajectory)

        self.assertIn("parameters", skill.metadata)
        self.assertEqual(skill.metadata["parameters"]["inspect_commit"]["sha"], "sha_target_222")
        self.assertEqual(skill.metadata["parameters"]["inspect_job_logs"]["run_id"], 2)
        self.assertEqual(skill.metadata["parameters"]["inspect_job_logs"]["job_name"], "test")

        # Check provenance
        self.assertIn("parameter_provenance", skill.metadata)
        self.assertEqual(skill.metadata["parameter_provenance"]["inspect_commit.sha"]["value"], "sha_target_222")
        self.assertEqual(skill.metadata["parameter_provenance"]["inspect_commit.sha"]["source_tool"], "list_workflow_runs")

    def test_parameter_extraction_reflects_dynamic_evidence(self):
        # Changing the discovered commit in the evidence must change the synthesized parameter
        trajectory = {
            "trajectory_id": "traj-dynamic",
            "steps": [
                {
                    "tool_name": "inspect_workflow_run",
                    "output": {"id": 42, "sha": "dynamic_commit_999"},
                    "success": True,
                }
            ],
        }

        skill = self.synthesizer.synthesize(self.failure_analysis, trajectory)
        self.assertEqual(skill.metadata["parameters"]["inspect_commit"]["sha"], "dynamic_commit_999")

    def test_no_parameters_invented_without_evidence(self):
        trajectory = {
            "trajectory_id": "traj-clean",
            "steps": [
                {"tool_name": "random_tool", "output": "clean output", "success": True}
            ],
        }
        skill = self.synthesizer.synthesize(self.failure_analysis, trajectory)
        self.assertNotIn("parameters", skill.metadata)

    def test_successful_trajectory_synthesis(self):
        trajectory = {
            "trajectory_id": "traj-789",
            "tool_calls": [{"tool_name": "write_code"}],
        }
        skill = self.synthesizer.synthesize(self.success_analysis, trajectory)

        self.assertEqual(skill.name, "Successful Task Execution")
        self.assertEqual(skill.failure_type, "none")
        self.assertEqual(skill.procedure, ["write_code"])

    def test_deterministic_id(self):
        trajectory = {
            "trajectory_id": "traj-1",
            "steps": [{"tool_name": "test_tool"}],
        }
        skill1 = self.synthesizer.synthesize(self.failure_analysis, trajectory)
        skill2 = self.synthesizer.synthesize(self.failure_analysis, trajectory)
        self.assertEqual(skill1.skill_id, skill2.skill_id)

    def test_malformed_trajectory(self):
        trajectory = {}
        skill = self.synthesizer.synthesize(self.failure_analysis, trajectory)
        self.assertEqual(skill.procedure, ["unknown_action"])
        self.assertEqual(skill.source_trajectory_id, "unknown-traj")

    def test_validation_failure_raises(self):
        trajectory = {
            "trajectory_id": "traj-1",
            "steps": [{"tool_name": "test_tool"}],
        }
        with patch('syndicate.learning.skill.Skill.validate', return_value=False):
            with self.assertRaises(ValueError):
                self.synthesizer.synthesize(self.failure_analysis, trajectory)


if __name__ == "__main__":
    unittest.main()
