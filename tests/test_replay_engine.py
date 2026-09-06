import unittest
from syndicate.learning.replay_engine import ReplayEngine, ReplayResult
from syndicate.learning.skill import Skill
from syndicate.core.models.task import Task, ToolCall
from syndicate.core.executor.agent_executor import AgentExecutor
from syndicate.core.recorder.trajectory_recorder import TrajectoryRecorder
from syndicate.core.evaluator.trajectory_evaluator import TrajectoryEvaluator


class MockTool:
    def __init__(self, name, success=True):
        self.name = name
        self.success = success
        self.received_inputs = []

    def execute(self, input_data):
        self.received_inputs.append(input_data)
        if not self.success:
            return {"success": False, "error": f"{self.name} mock failure"}
        return {"success": True, "output": f"{self.name} success"}


class TestReplayEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ReplayEngine()
        self.executor = AgentExecutor()
        self.tool1 = MockTool("tool1")
        self.tool2 = MockTool("tool2")
        self.tool3 = MockTool("tool3")
        self.executor.register_tool("tool1", self.tool1)
        self.executor.register_tool("tool2", self.tool2)
        self.executor.register_tool("tool3", self.tool3)

        # Use an in-memory db for testing the recorder
        self.recorder = TrajectoryRecorder("memory")
        self.evaluator = TrajectoryEvaluator()

        self.skill = Skill(
            skill_id="test-skill",
            name="Test Skill",
            description="A test skill",
            trigger="TestTrigger",
            procedure=["tool1", "tool2"],
            source_trajectory_id="source-1",
            failure_type="tool_failure",
            evidence=["None"]
        )
        self.task = Task(
            task_id="task-1",
            description="Arbitrary original task description",
            available_tool_names=["tool1", "tool2", "tool3"]
        )

    def test_successful_replay(self):
        result = self.engine.replay(self.skill, self.task, self.executor, self.recorder, self.evaluator)

        self.assertTrue(result.success)
        self.assertEqual(result.skill_id, "test-skill")
        self.assertEqual(result.tool_sequence, ["tool1", "tool2"])
        self.assertEqual(result.tool_call_count, 2)
        self.assertIsNotNone(result.trajectory_id)
        self.assertNotEqual(result.trajectory_id, "source-1")

        # Verify recorded correctly
        traj = self.recorder.get_trajectory(result.trajectory_id)
        self.assertEqual(traj["summary"]["metadata"]["replayed_skill_id"], "test-skill")
        self.assertEqual(traj["summary"]["metadata"]["source_trajectory_id"], "source-1")
        self.assertEqual(traj["summary"]["metadata"]["original_task_description"], "Arbitrary original task description")

    def test_build_execution_plan_derives_directly_from_skill(self):
        plan = self.engine._build_execution_plan(self.skill)
        self.assertEqual(len(plan), 2)
        self.assertEqual([tc.tool_name for tc in plan], ["tool1", "tool2"])
        self.assertIsInstance(plan[0], ToolCall)
        self.assertIsInstance(plan[1], ToolCall)

    def test_build_execution_plan_incorporates_learned_parameters(self):
        self.skill.metadata["parameters"] = {
            "tool1": {"param_a": 123},
            "tool2": {"param_b": "value_b"}
        }

        plan = self.engine._build_execution_plan(self.skill)
        self.assertEqual(plan[0].input, {"param_a": 123})
        self.assertEqual(plan[1].input, {"param_b": "value_b"})

        # Run replay and verify tools receive the learned inputs
        result = self.engine.replay(self.skill, self.task, self.executor, self.recorder, self.evaluator)
        self.assertTrue(result.success)
        self.assertEqual(self.tool1.received_inputs[-1], {"param_a": 123})
        self.assertEqual(self.tool2.received_inputs[-1], {"param_b": "value_b"})

    def test_missing_parameters_default_to_empty_dict(self):
        self.skill.metadata["parameters"] = {
            "tool1": {"param_a": 123}
            # tool2 missing
        }
        plan = self.engine._build_execution_plan(self.skill)
        self.assertEqual(plan[0].input, {"param_a": 123})
        self.assertEqual(plan[1].input, {})

    def test_skill_procedure_directly_controls_tool_sequence_and_ignores_task_description(self):
        # Task description explicitly mentions tool2 first or commands something else
        self.task.description = "Use tool2 then Use tool1"
        self.skill.procedure = ["tool1", "tool2"]

        result = self.engine.replay(self.skill, self.task, self.executor, self.recorder, self.evaluator)

        self.assertTrue(result.success)
        # The procedure in skill dictates the order, NOT the text in task.description
        self.assertEqual(result.tool_sequence, ["tool1", "tool2"])
        # Ensure task.description was not mutated or overwritten
        self.assertEqual(self.task.description, "Use tool2 then Use tool1")

    def test_task_description_not_used_for_ordering(self):
        # Even with text completely lacking tool references, procedure still drives execution
        self.task.description = "Unrelated natural language text"
        self.skill.procedure = ["tool3", "tool1"]

        result = self.engine.replay(self.skill, self.task, self.executor, self.recorder, self.evaluator)

        self.assertTrue(result.success)
        self.assertEqual(result.tool_sequence, ["tool3", "tool1"])

    def test_unavailable_tool_fails_safely_without_overwriting_source(self):
        self.skill.procedure = ["tool1", "missing_tool"]
        result = self.engine.replay(self.skill, self.task, self.executor, self.recorder, self.evaluator)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Tool 'missing_tool' not available in executor")
        self.assertEqual(result.tool_call_count, 0)
        self.assertEqual(result.tool_sequence, [])
        # Trajectory ID should not be source trajectory
        self.assertNotEqual(result.trajectory_id, "source-1")

    def test_invalid_skill_raises(self):
        self.skill.skill_id = ""  # Invalid
        with self.assertRaises(ValueError):
            self.engine.replay(self.skill, self.task, self.executor, self.recorder, self.evaluator)

    def test_replay_is_deterministic(self):
        result1 = self.engine.replay(self.skill, self.task, self.executor, self.recorder, self.evaluator)
        result2 = self.engine.replay(self.skill, self.task, self.executor, self.recorder, self.evaluator)

        self.assertEqual(result1.tool_sequence, result2.tool_sequence)
        self.assertEqual(result1.success, result2.success)
        self.assertEqual(result1.final_answer, result2.final_answer)

    def test_tool_failure_during_replay_handled_safely(self):
        failing_executor = AgentExecutor()
        failing_executor.register_tool("tool1", MockTool("tool1", success=False))
        failing_executor.register_tool("tool2", MockTool("tool2"))

        result = self.engine.replay(self.skill, self.task, failing_executor, self.recorder, self.evaluator)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "tool1 mock failure")
        self.assertEqual(result.tool_sequence, ["tool1"])
        self.assertEqual(result.tool_call_count, 1)

    def test_compare_improved(self):
        baseline = {"overall_score": 0.4}
        replay = {"overall_score": 0.9}
        comp = self.engine.compare(baseline, replay)

        self.assertEqual(comp["baseline_score"], 0.4)
        self.assertEqual(comp["replay_score"], 0.9)
        self.assertAlmostEqual(comp["score_delta"], 0.5)
        self.assertTrue(comp["improved"])

    def test_compare_not_improved(self):
        baseline = {"overall_score": 0.9}
        replay = {"overall_score": 0.4}
        comp = self.engine.compare(baseline, replay)

        self.assertFalse(comp["improved"])
        self.assertAlmostEqual(comp["score_delta"], -0.5)


if __name__ == "__main__":
    unittest.main()
