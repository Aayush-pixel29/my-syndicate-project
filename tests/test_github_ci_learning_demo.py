import unittest
from syndicate.core.simulator.github_simulator import GithubSimulator
from syndicate.core.executor.agent_executor import AgentExecutor
from syndicate.learning.learning_loop import LearningRunResult
from demos.github_ci_learning_demo import (
    ListWorkflowRunsTool,
    InspectWorkflowRunTool,
    InspectJobLogsTool,
    InspectCommitTool,
    create_demo_executor,
    run_demo,
)


class TestGithubCiLearningDemo(unittest.TestCase):
    def setUp(self):
        self.simulator = GithubSimulator()
        self.simulator.initialize()

    def test_granular_tools_registered(self):
        executor = create_demo_executor(self.simulator)
        required_tools = [
            "list_workflow_runs",
            "inspect_workflow_run",
            "inspect_job_logs",
            "inspect_commit",
            "github",
        ]
        for tool_name in required_tools:
            self.assertIn(tool_name, executor.tools)
            tool = executor.tools[tool_name]
            self.assertEqual(tool.name, tool_name)

    def test_inspect_commit_requires_sha_without_hidden_fallback(self):
        commit_tool = InspectCommitTool(self.simulator)
        res_empty = commit_tool.execute({})
        self.assertFalse(res_empty["success"])
        self.assertEqual(res_empty["error"], "sha is required")

        res_none = commit_tool.execute({"sha": ""})
        self.assertFalse(res_none["success"])
        self.assertEqual(res_none["error"], "sha is required")

    def test_valid_operation_wrapper_calls_real_simulator(self):
        list_tool = ListWorkflowRunsTool(self.simulator)
        res = list_tool.execute({"repo": "repocli/test-ci", "branch": "main"})
        self.assertTrue(res["success"])
        self.assertIsInstance(res["output"], list)
        self.assertEqual(len(res["output"]), 3)
        self.assertEqual(res["output"][0]["id"], 1)

        logs_tool = InspectJobLogsTool(self.simulator)
        log_res = logs_tool.execute({"repo": "repocli/test-ci", "run_id": 2, "job_name": "test"})
        self.assertTrue(log_res["success"])
        self.assertIn("Assertion failed", log_res["output"])

        commit_tool = InspectCommitTool(self.simulator)
        commit_res = commit_tool.execute({"repo": "repocli/test-ci", "sha": "def456ghi789"})
        self.assertTrue(commit_res["success"])
        self.assertEqual(commit_res["output"]["author"], "bob")

    def test_invalid_parameters_fail_honestly(self):
        commit_tool = InspectCommitTool(self.simulator)
        res = commit_tool.execute({"repo": "repocli/test-ci", "sha": "nonexistent_sha"})
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])

        logs_tool = InspectJobLogsTool(self.simulator)
        res_log = logs_tool.execute({"repo": "repocli/test-ci", "run_id": 999, "job_name": "test"})
        self.assertFalse(res_log["success"])
        self.assertIn("not found", res_log["error"])

        run_tool = InspectWorkflowRunTool(self.simulator)
        res_run = run_tool.execute({"repo": "repocli/test-ci", "run_id": "invalid_id"})
        self.assertFalse(res_run["success"])
        self.assertIn("Invalid run_id", res_run["error"])

    def test_no_hidden_fallback_on_empty_input_for_generic_tool(self):
        from syndicate.core.simulator.github_simulator import GithubTool
        generic_tool = GithubTool(self.simulator)
        res = generic_tool.execute({})
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "Operation not specified")

    def test_end_to_end_demo_execution_is_dynamic_and_promoted(self):
        result = run_demo()
        self.assertIsInstance(result, LearningRunResult)

        # Confirm the sequence includes granular tools, not generic 'github'
        expected_seq = ["list_workflow_runs", "inspect_job_logs", "inspect_commit"]
        self.assertEqual(result.skill.procedure, expected_seq)
        self.assertEqual(result.replay_result.tool_sequence, expected_seq)

        # Confirm learned parameters were extracted into metadata
        self.assertIn("parameters", result.skill.metadata)
        self.assertEqual(result.skill.metadata["parameters"]["inspect_commit"]["sha"], "def456ghi789")

        # Confirm parameter provenance is explicitly tracked
        self.assertIn("parameter_provenance", result.skill.metadata)
        self.assertEqual(result.skill.metadata["parameter_provenance"]["inspect_commit.sha"]["value"], "def456ghi789")
        self.assertEqual(result.skill.metadata["parameter_provenance"]["inspect_commit.sha"]["source_tool"], "list_workflow_runs")

        # Baseline failed honestly on invalid commit SHA
        self.assertEqual(result.failure_analysis.failure_type, "tool_failure")
        self.assertLess(result.baseline_evaluation["overall_score"], 1.0)

        # Replay succeeded dynamically because it received the learned parameter
        self.assertTrue(result.replay_result.success)
        self.assertEqual(result.replay_result.evaluation["overall_score"], 1.0)

        # Promotion decision strictly derived from comparison
        self.assertTrue(result.promotion_decision.promoted)
        self.assertGreater(result.promotion_decision.score_delta, 0.0)
        self.assertEqual(result.promotion_decision.metrics["tool_call_delta"], 0)


if __name__ == "__main__":
    unittest.main()
