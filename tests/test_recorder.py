"""Tests for trajectory recorder."""

import unittest
import json
from datetime import datetime
from syndicate.core.models.task import (
    Task,
    TaskStatus,
    ToolCall,
    ToolResult,
)
from syndicate.core.executor.agent_executor import AgentExecutor
from syndicate.core.recorder.trajectory_recorder import (
    TrajectoryRecorder,
    generate_trajectory_id,
)


class TestTrajectoryRecorder(unittest.TestCase):
    """Test TrajectoryRecorder."""

    def setUp(self):
        """Set up test fixtures."""
        self.recorder = TrajectoryRecorder()
        self.task = Task(
            task_id="record-test",
            description="Test trajectory recording",
            available_tool_names=["test_tool"],
            success_criteria="Task must succeed"
        )

    def test_generate_trajectory_id(self):
        """Test trajectory ID generation."""
        id1 = generate_trajectory_id()
        id2 = generate_trajectory_id()

        self.assertIsNotNone(id1)
        self.assertIsNotNone(id2)
        self.assertNotEqual(id1, id2)
        self.assertTrue(id1.startswith("trajectory-"))
        self.assertTrue(id2.startswith("trajectory-"))

    def test_record_trajectory_initialization(self):
        """Test recording initial trajectory state."""
        recorder = TrajectoryRecorder()
        trajectory_id = generate_trajectory_id()

        recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        # Verify storage
        trajectories = recorder.get_trajectories()
        self.assertIn(trajectory_id, trajectories)

    def test_record_tool_call(self):
        """Test recording tool calls."""
        recorder = TrajectoryRecorder()
        trajectory_id = generate_trajectory_id()

        # Initialize
        recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        # Record tool calls
        tool_call = ToolCall(
            tool_name="test_tool",
            input={"param": "value"}
        )

        recorder.record_tool_call(
            trajectory_id=trajectory_id,
            tool_call=tool_call
        )

        # Verify
        trajectories = recorder.get_trajectories()
        self.assertEqual(len(trajectories[trajectory_id]["tool_calls"]), 1)
        self.assertEqual(
            trajectories[trajectory_id]["tool_calls"][0]["tool_name"],
            "test_tool"
        )

    def test_record_tool_result(self):
        """Test recording tool results."""
        recorder = TrajectoryRecorder()
        trajectory_id = generate_trajectory_id()

        # Initialize
        recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        # Record tool result
        tool_result = ToolResult(
            tool_name="test_tool",
            success=True,
            output={"result": "success"}
        )

        recorder.record_tool_result(
            trajectory_id=trajectory_id,
            tool_result=tool_result
        )

        # Verify
        trajectories = recorder.get_trajectories()
        self.assertEqual(len(trajectories[trajectory_id]["tool_results"]), 1)
        self.assertEqual(
            trajectories[trajectory_id]["tool_results"][0]["tool_name"],
            "test_tool"
        )

    def test_record_final_answer(self):
        """Test recording final answer."""
        recorder = TrajectoryRecorder()
        trajectory_id = generate_trajectory_id()

        # Initialize
        recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        # Record final answer
        final_answer = "The task was completed successfully."
        recorder.record_final_answer(trajectory_id, final_answer)

        # Verify
        trajectories = recorder.get_trajectories()
        self.assertEqual(
            trajectories[trajectory_id]["final_answer"],
            final_answer
        )

    def test_record_trajectory_summary(self):
        """Test recording trajectory summary."""
        recorder = TrajectoryRecorder()
        trajectory_id = generate_trajectory_id()

        # Initialize
        recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        # Record summary
        summary = {
            "duration": "10s",
            "cost": "0.001",
            "reliability": 0.9
        }
        recorder.record_trajectory_summary(trajectory_id, summary)

        # Verify
        trajectories = recorder.get_trajectories()
        self.assertEqual(
            trajectories[trajectory_id]["summary"]["duration"],
            "10s"
        )
        self.assertEqual(
            trajectories[trajectory_id]["summary"]["reliability"],
            0.9
        )

    def test_get_trajectory(self):
        """Test retrieving trajectory."""
        recorder = TrajectoryRecorder()
        trajectory_id = generate_trajectory_id()

        # Initialize and populate
        recorder.record_trajectory_initialization(
            task_id=self.task.task_id,
            description=self.task.description,
            available_tools=self.task.available_tool_names,
            success_criteria=self.task.success_criteria,
            trajectory_id=trajectory_id
        )

        tool_call = ToolCall(tool_name="test_tool", input={"param": "value"})
        recorder.record_tool_call(trajectory_id, tool_call)

        # Retrieve
        trajectory = recorder.get_trajectory(trajectory_id)

        self.assertIsNotNone(trajectory)
        self.assertEqual(trajectory["task_id"], self.task.task_id)
        self.assertEqual(len(trajectory["tool_calls"]), 1)

    def test_get_trajectories(self):
        """Test getting all trajectories."""
        recorder = TrajectoryRecorder()
        id1 = generate_trajectory_id()
        id2 = generate_trajectory_id()

        recorder.record_trajectory_initialization(
            task_id="task1",
            description="Task 1",
            available_tools=["tool1"],
            success_criteria="Success",
            trajectory_id=id1
        )

        recorder.record_trajectory_initialization(
            task_id="task2",
            description="Task 2",
            available_tools=["tool2"],
            success_criteria="Success",
            trajectory_id=id2
        )

        trajectories = recorder.get_trajectories()

        self.assertEqual(len(trajectories), 2)
        self.assertIn(id1, trajectories)
        self.assertIn(id2, trajectories)

    def test_clear_trajectories(self):
        """Test clearing all trajectories."""
        recorder = TrajectoryRecorder()
        id1 = generate_trajectory_id()

        recorder.record_trajectory_initialization(
            task_id="task1",
            description="Task 1",
            available_tools=["tool1"],
            success_criteria="Success",
            trajectory_id=id1
        )

        recorder.clear_trajectories()

        trajectories = recorder.get_trajectories()
        self.assertEqual(len(trajectories), 0)


class TestTrajectoryRecorderIntegration(unittest.TestCase):
    """Integration tests for TrajectoryRecorder."""

    def test_full_trajectory_record(self):
        """Test recording a complete trajectory."""
        recorder = TrajectoryRecorder()
        task_id = "integration-test"
        trajectory_id = generate_trajectory_id()

        # Initialize
        recorder.record_trajectory_initialization(
            task_id=task_id,
            description="Integration test",
            available_tools=["echo"],
            success_criteria="Should succeed",
            trajectory_id=trajectory_id
        )

        # Record tool calls and results
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

        # Record final answer and summary
        recorder.record_final_answer(trajectory_id, "Task completed.")
        recorder.record_trajectory_summary(
            trajectory_id,
            {"duration": "5s", "reliability": 0.95}
        )

        # Retrieve and verify
        trajectory = recorder.get_trajectory(trajectory_id)

        self.assertEqual(trajectory["task_id"], task_id)
        self.assertEqual(len(trajectory["tool_calls"]), 1)
        self.assertEqual(len(trajectory["tool_results"]), 1)
        self.assertEqual(trajectory["final_answer"], "Task completed.")
        self.assertIn("summary", trajectory)


if __name__ == "__main__":
    unittest.main()
