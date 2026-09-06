"""Tests for trajectory evaluator."""

import unittest
from datetime import datetime
from syndicate.core.models.task import (
    Task,
    TaskStatus,
    ToolCall,
    ToolResult,
)
from syndicate.core.recorder.trajectory_recorder import TrajectoryRecorder, generate_trajectory_id
from syndicate.core.evaluator.trajectory_evaluator import TrajectoryEvaluator


class TestTrajectoryEvaluator(unittest.TestCase):
    """Test TrajectoryEvaluator."""

    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = TrajectoryEvaluator()
        self.recorder = TrajectoryRecorder()
        self.task = Task(
            task_id="eval-test",
            description="Test evaluation",
            available_tool_names=["tool1"],
            success_criteria="Task must succeed"
        )

    def test_initialize(self):
        """Test evaluator initialization."""
        self.assertIsNotNone(self.evaluator)

    def test_evaluate_trajectory_completed(self):
        """Test evaluating completed trajectory."""
        trajectory_id = generate_trajectory_id()

        self.recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        self.recorder.record_tool_call(
            trajectory_id=trajectory_id,
            tool_call=ToolCall(tool_name="tool1", input={"param": "value"})
        )

        self.recorder.record_tool_result(
            trajectory_id=trajectory_id,
            tool_result=ToolResult(
                tool_name="tool1",
                success=True,
                output={"result": "success"}
            )
        )

        self.recorder.record_final_answer(trajectory_id, "Task completed.")

        result = self.evaluator.evaluate(trajectory_id, self.recorder)

        self.assertIsNotNone(result)
        self.assertIn("overall_score", result)
        self.assertIn("category", result)
        self.assertIn("details", result)

    def test_evaluate_trajectory_failed(self):
        """Test evaluating failed trajectory."""
        trajectory_id = generate_trajectory_id()

        self.recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        self.recorder.record_tool_result(
            trajectory_id=trajectory_id,
            tool_result=ToolResult(
                tool_name="tool1",
                success=False,
                error="Task failed"
            )
        )

        result = self.evaluator.evaluate(trajectory_id, self.recorder)

        self.assertIsNotNone(result)
        self.assertIn("overall_score", result)
        self.assertIn("category", result)
        self.assertIn("error", result)

    def test_evaluate_trajectory_incomplete(self):
        """Test evaluating incomplete trajectory."""
        trajectory_id = generate_trajectory_id()

        self.recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        self.recorder.record_tool_call(
            trajectory_id=trajectory_id,
            tool_call=ToolCall(tool_name="tool1", input={"param": "value"})
        )

        # Not recording final answer

        result = self.evaluator.evaluate(trajectory_id, self.recorder)

        self.assertIsNotNone(result)
        self.assertIn("overall_score", result)
        self.assertIn("category", result)
        self.assertIn("details", result)

    def test_evaluate_no_trajectory(self):
        """Test evaluating non-existent trajectory."""
        with self.assertRaises(KeyError):
            self.evaluator.evaluate("nonexistent", self.recorder)

    def test_evaluate_details_structure(self):
        """Test that evaluation includes expected details."""
        trajectory_id = generate_trajectory_id()

        self.recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        self.recorder.record_tool_call(
            trajectory_id=trajectory_id,
            tool_call=ToolCall(tool_name="tool1", input={"param": "value"})
        )

        self.recorder.record_tool_result(
            trajectory_id=trajectory_id,
            tool_result=ToolResult(
                tool_name="tool1",
                success=True,
                output={"result": "success"}
            )
        )

        self.recorder.record_final_answer(trajectory_id, "Task completed.")

        result = self.evaluator.evaluate(trajectory_id, self.recorder)

        # Check that details are structured appropriately
        self.assertIn("task_completeness", result["details"])
        self.assertIn("correctness", result["details"])
        self.assertIn("efficiency", result["details"])
        self.assertIn("reliability", result["details"])


class TestTrajectoryEvaluatorIntegration(unittest.TestCase):
    """Integration tests for TrajectoryEvaluator."""

    def test_full_evaluate_workflow(self):
        """Test complete evaluation workflow."""
        recorder = TrajectoryRecorder()
        evaluator = TrajectoryEvaluator()
        task_id = "integration-eval"
        trajectory_id = generate_trajectory_id()

        # Record a complete trajectory
        recorder.record_trajectory_initialization(
            task_id=task_id,
            description="Integration evaluation test",
            available_tools=["echo", "calculator"],
            success_criteria="Should complete successfully"
        )

        recorder.record_tool_call(
            trajectory_id=trajectory_id,
            tool_call=ToolCall(tool_name="echo", input={"message": "hello"})
        )

        recorder.record_tool_result(
            trajectory_id=trajectory_id,
            tool_result=ToolResult(
                tool_name="echo",
                success=True,
                output={"output": "hello"}
            )
        )

        recorder.record_tool_call(
            trajectory_id=trajectory_id,
            tool_call=ToolCall(tool_name="calculator", input={"operation": "add", "a": 1, "b": 2})
        )

        recorder.record_tool_result(
            trajectory_id=trajectory_id,
            tool_result=ToolResult(
                tool_name="calculator",
                success=True,
                output={"result": 3}
            )
        )

        recorder.record_final_answer(
            trajectory_id,
            "Both operations completed successfully."
        )

        # Evaluate
        result = evaluator.evaluate(trajectory_id, recorder)

        # Verify results
        self.assertIsNotNone(result)
        self.assertIn("overall_score", result)
        self.assertIn("category", result)
        self.assertIn("details", result)
        self.assertIn("task_completeness", result["details"])
        self.assertIn("correctness", result["details"])
        self.assertIn("efficiency", result["details"])
        self.assertIn("reliability", result["details"])


if __name__ == "__main__":
    unittest.main()
