import unittest
from syndicate.learning.learning_loop import LearningLoop, LearningRunResult, summarize
from syndicate.core.models.task import Task
from syndicate.core.executor.agent_executor import AgentExecutor
from syndicate.core.recorder.trajectory_recorder import TrajectoryRecorder
from syndicate.core.evaluator.trajectory_evaluator import TrajectoryEvaluator
from syndicate.learning.failure_analyzer import FailureAnalyzer
from syndicate.learning.skill_synthesizer import SkillSynthesizer
from syndicate.learning.replay_engine import ReplayEngine, ReplayResult
from syndicate.learning.promotion_gate import PromotionGate


class MockTool:
    def __init__(self, name: str, success: bool = True, output: str = "success"):
        self.name = name
        self.success = success
        self.output = output

    def execute(self, input_data):
        if not self.success:
            return {"success": False, "error": f"{self.name} failed"}
        return {"success": True, "output": self.output}


class TestLearningLoop(unittest.TestCase):
    def setUp(self):
        self.recorder = TrajectoryRecorder("memory")
        self.evaluator = TrajectoryEvaluator()
        self.learning_loop = LearningLoop()

        self.executor = AgentExecutor()
        self.executor.register_tool("check_ci_status", MockTool("check_ci_status"))
        self.executor.register_tool("inspect_logs", MockTool("inspect_logs"))
        self.executor.register_tool("restart_workflow", MockTool("restart_workflow"))

        self.task = Task(
            task_id="task-investigate-ci",
            description="Use check_ci_status then Use inspect_logs then Use restart_workflow",
            available_tool_names=["check_ci_status", "inspect_logs", "restart_workflow"]
        )

    def test_complete_learning_loop_workflow(self):
        result = self.learning_loop.run(
            task=self.task,
            executor=self.executor,
            recorder=self.recorder,
            evaluator=self.evaluator
        )

        self.assertIsInstance(result, LearningRunResult)
        self.assertTrue(result.baseline_trajectory_id.startswith("trajectory-"))
        self.assertTrue(result.replay_result.trajectory_id.startswith("trajectory-"))

        # 1. Baseline and Replay must have different trajectory IDs
        self.assertNotEqual(result.baseline_trajectory_id, result.replay_result.trajectory_id)

        # 2. Skill provenance is preserved
        self.assertEqual(result.skill.source_trajectory_id, result.baseline_trajectory_id)

        # 3. Both trajectories exist in recorder
        baseline_traj = self.recorder.get_trajectory(result.baseline_trajectory_id)
        replay_traj = self.recorder.get_trajectory(result.replay_result.trajectory_id)
        self.assertIsNotNone(baseline_traj)
        self.assertIsNotNone(replay_traj)
        self.assertEqual(
            replay_traj["summary"]["metadata"]["source_trajectory_id"],
            result.baseline_trajectory_id
        )

        # 4. Summary verification
        summary = summarize(result)
        required_fields = [
            "baseline_score",
            "replay_score",
            "score_delta",
            "baseline_tool_calls",
            "replay_tool_calls",
            "tool_call_delta",
            "improved",
            "promoted",
            "failure_type",
            "skill_id",
            "baseline_trajectory_id",
            "replay_trajectory_id",
        ]
        for field in required_fields:
            self.assertIn(field, summary)

        # Verify summary reflects actual result values
        self.assertEqual(summary["baseline_trajectory_id"], result.baseline_trajectory_id)
        self.assertEqual(summary["replay_trajectory_id"], result.replay_result.trajectory_id)
        self.assertEqual(summary["skill_id"], result.skill.skill_id)
        self.assertEqual(summary["failure_type"], result.failure_analysis.failure_type)

    def test_successful_improvement_promotes_skill(self):
        # Configure a custom evaluator or setup where replay improves score over baseline
        class BaselineLowReplayHighEvaluator(TrajectoryEvaluator):
            def evaluate(self, trajectory_id: str, recorder: TrajectoryRecorder):
                traj = recorder.get_trajectory(trajectory_id)
                # If it's the replay (has replayed_skill_id in summary metadata)
                if traj and traj.get("summary", {}).get("metadata", {}).get("replayed_skill_id"):
                    return {"overall_score": 0.95, "category": "excellent", "details": {}}
                return {"overall_score": 0.40, "category": "poor", "details": {}}

        loop = LearningLoop()
        custom_evaluator = BaselineLowReplayHighEvaluator()

        result = loop.run(
            task=self.task,
            executor=self.executor,
            recorder=self.recorder,
            evaluator=custom_evaluator
        )

        self.assertTrue(result.promotion_decision.promoted)
        self.assertTrue(result.skill.promoted)
        self.assertTrue(result.skill.validated)
        self.assertGreater(result.promotion_decision.score_delta, 0.0)

        summary = loop.summarize(result)
        self.assertTrue(summary["improved"])
        self.assertTrue(summary["promoted"])
        self.assertAlmostEqual(summary["score_delta"], 0.55)

    def test_non_improving_replay_rejects_promotion(self):
        # Configure an evaluator where baseline and replay scores are equal
        class FlatEvaluator(TrajectoryEvaluator):
            def evaluate(self, trajectory_id: str, recorder: TrajectoryRecorder):
                return {"overall_score": 0.50, "category": "fair", "details": {}}

        loop = LearningLoop()
        flat_eval = FlatEvaluator()

        result = loop.run(
            task=self.task,
            executor=self.executor,
            recorder=self.recorder,
            evaluator=flat_eval
        )

        self.assertFalse(result.promotion_decision.promoted)
        self.assertFalse(result.skill.promoted)
        self.assertEqual(result.promotion_decision.score_delta, 0.0)

        summary = summarize(result)
        self.assertFalse(summary["improved"])
        self.assertFalse(summary["promoted"])

    def test_replay_failure_handled_safely(self):
        # Setup an executor that fails during replay (e.g. tool fails)
        failing_executor = AgentExecutor()
        failing_executor.register_tool("check_ci_status", MockTool("check_ci_status", success=False))

        task = Task(
            task_id="task-failing",
            description="Use check_ci_status",
            available_tool_names=["check_ci_status"]
        )

        loop = LearningLoop()
        result = loop.run(
            task=task,
            executor=failing_executor,
            recorder=self.recorder,
            evaluator=self.evaluator
        )

        self.assertIsInstance(result, LearningRunResult)
        self.assertFalse(result.replay_result.success)
        self.assertFalse(result.promotion_decision.promoted)
        self.assertFalse(result.skill.promoted)

        summary = summarize(result)
        self.assertFalse(summary["promoted"])

    def test_deterministic_result_structure(self):
        result1 = self.learning_loop.run(self.task, self.executor, self.recorder, self.evaluator)
        s1 = summarize(result1)

        recorder2 = TrajectoryRecorder("memory")
        result2 = self.learning_loop.run(self.task, self.executor, recorder2, self.evaluator)
        s2 = summarize(result2)

        # Excluding random trajectory IDs, deterministic metrics must match
        self.assertEqual(s1["baseline_score"], s2["baseline_score"])
        self.assertEqual(s1["replay_score"], s2["replay_score"])
        self.assertEqual(s1["score_delta"], s2["score_delta"])
        self.assertEqual(s1["baseline_tool_calls"], s2["baseline_tool_calls"])
        self.assertEqual(s1["replay_tool_calls"], s2["replay_tool_calls"])
        self.assertEqual(s1["tool_call_delta"], s2["tool_call_delta"])
        self.assertEqual(s1["improved"], s2["improved"])
        self.assertEqual(s1["promoted"], s2["promoted"])
        self.assertEqual(s1["failure_type"], s2["failure_type"])
        self.assertEqual(s1["skill_id"], s2["skill_id"])


if __name__ == "__main__":
    unittest.main()
