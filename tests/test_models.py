"""Tests for core models."""

import unittest
from datetime import datetime
from syndicate.core.models.task import (
    Task,
    TaskStatus,
    ToolInputSchema,
    ToolCall,
    ToolResult,
)
from syndicate.core.models.tool import Tool


class TestTaskModels(unittest.TestCase):
    """Test Task model."""

    def test_task_creation(self):
        """Test task creation."""
        task = Task(
            task_id="test-1",
            description="Test task",
            available_tool_names=["tool1", "tool2"],
            success_criteria="Task must succeed",
        )

        self.assertEqual(task.task_id, "test-1")
        self.assertEqual(task.description, "Test task")
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(len(task.available_tool_names), 2)

    def test_task_status_enum(self):
        """Test TaskStatus enum values."""
        self.assertEqual(TaskStatus.PENDING.value, "pending")
        self.assertEqual(TaskStatus.COMPLETED.value, "completed")
        self.assertEqual(TaskStatus.FAILED.value, "failed")

    def test_task_timestamps(self):
        """Test task timestamps."""
        before = datetime.utcnow()
        task = Task(task_id="test-2", description="Test")
        after = datetime.utcnow()

        self.assertGreaterEqual(task.created_at, before)
        self.assertLessEqual(task.created_at, after)
        self.assertIsNone(task.started_at)
        self.assertIsNone(task.completed_at)


class TestToolInputSchema(unittest.TestCase):
    """Test ToolInputSchema model."""

    def test_schema_creation(self):
        """Test schema creation."""
        schema = ToolInputSchema(
            type="object",
            description="Test schema",
            required=["param1"],
            enum=["option1", "option2"],
        )

        self.assertEqual(schema.type, "object")
        self.assertEqual(schema.description, "Test schema")
        self.assertEqual(schema.required, ["param1"])
        self.assertEqual(schema.enum, ["option1", "option2"])


class TestToolCall(unittest.TestCase):
    """Test ToolCall model."""

    def test_tool_call_creation(self):
        """Test tool call creation."""
        call = ToolCall(tool_name="test_tool", input={"param": "value"})

        self.assertEqual(call.tool_name, "test_tool")
        self.assertEqual(call.input, {"param": "value"})
        self.assertIsNotNone(call.timestamp)


class TestToolResult(unittest.TestCase):
    """Test ToolResult model."""

    def test_tool_result_success(self):
        """Test successful tool result."""
        result = ToolResult(
            tool_name="test_tool",
            success=True,
            output={"data": "result"},
        )

        self.assertEqual(result.tool_name, "test_tool")
        self.assertTrue(result.success)
        self.assertEqual(result.output, {"data": "result"})
        self.assertIsNone(result.error)

    def test_tool_result_failure(self):
        """Test failed tool result."""
        result = ToolResult(
            tool_name="test_tool",
            success=False,
            error="Tool execution failed",
            output=None,
        )

        self.assertEqual(result.tool_name, "test_tool")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Tool execution failed")


class MockTool(Tool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing."

    @property
    def input_schema(self) -> ToolInputSchema:
        return ToolInputSchema(
            type="object",
            description="Test input schema",
            required=["param1"],
            properties={"param1": {"type": "string", "description": "Parameter 1"}},
        )

    def execute(self, input_data: dict) -> dict:
        return {"success": True, "output": input_data["param1"]}


class TestToolInterface(unittest.TestCase):
    """Test Tool abstraction."""

    def test_tool_interface(self):
        """Test tool interface implementation."""
        tool = MockTool()

        self.assertEqual(tool.name, "mock_tool")
        self.assertEqual(tool.description, "A mock tool for testing.")
        self.assertEqual(tool.input_schema.type, "object")

        # Test execute
        result = tool.execute({"param1": "value1"})
        self.assertTrue(result["success"])
        self.assertEqual(result["output"], "value1")


if __name__ == "__main__":
    unittest.main()
