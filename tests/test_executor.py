"""Tests for agent executor."""

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
from syndicate.core.executor.agent_executor import (
    ModelInterface,
    AgentExecutor,
)


class MockSimpleTool(Tool):
    """Simple mock tool for testing executor."""

    @property
    def name(self) -> str:
        return "simple_tool"

    @property
    def description(self) -> str:
        return "A simple mock tool."

    @property
    def input_schema(self) -> ToolInputSchema:
        return ToolInputSchema(
            type="object",
            description="Test input schema",
            required=["message"],
            properties={
                "message": {
                    "type": "string",
                    "description": "Message to echo",
                }
            },
        )

    def execute(self, input_data: dict) -> dict:
        return {"output": input_data["message"], "success": True}


class MockFailingTool(Tool):
    """Mock tool that fails for testing error handling."""

    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "A tool that fails."

    @property
    def input_schema(self) -> ToolInputSchema:
        return ToolInputSchema(
            type="object",
            description="Test input schema",
            required=["param"],
            properties={
                "param": {
                    "type": "string",
                    "description": "Parameter",
                }
            },
        )

    def execute(self, input_data: dict) -> dict:
        return {"success": False, "error": "Intentional failure"}


class TestModelInterface(unittest.TestCase):
    """Test ModelInterface placeholder."""

    def test_model_interface_initialization(self):
        """Test model interface initialization."""
        # This is a placeholder, should not error
        model = ModelInterface()
        self.assertIsNotNone(model)

    def test_generate_answer_placeholder(self):
        """Test generate_answer placeholder."""
        model = ModelInterface()
        result = model.generate_answer(
            question="Test question",
            tools=["tool1", "tool2"],
            context="Test context"
        )
        # Placeholder should return a dict
        self.assertIsInstance(result, dict)

    def test_parse_action_placeholder(self):
        """Test parse_action placeholder."""
        model = ModelInterface()
        action = model.parse_action(
            current_state="test",
            available_tools=["tool1", "tool2"]
        )
        # Placeholder should return a dict
        self.assertIsInstance(action, dict)


class TestAgentExecutor(unittest.TestCase):
    """Test AgentExecutor."""

    def setUp(self):
        """Set up test fixtures."""
        self.model = ModelInterface()
        self.executor = AgentExecutor(model=self.model)
        self.executor.register_tool("simple_tool", MockSimpleTool())
        self.executor.register_tool("failing_tool", MockFailingTool())

    def test_executor_initialization(self):
        """Test executor initialization."""
        self.assertIsNotNone(self.executor.model)
        self.assertEqual(len(self.executor._tools), 2)

    def test_register_tool(self):
        """Test registering tools."""
        self.assertIn("simple_tool", self.executor._tools)
        self.assertIn("failing_tool", self.executor._tools)

    def test_plan_task_with_simple_tools(self):
        """Test planning task with simple tools."""
        task = Task(
            task_id="plan-test",
            description="Echo 'hello' using simple_tool",
            available_tool_names=["simple_tool"],
            success_criteria="Output should be 'hello'"
        )

        plan = self.executor.plan_task(task)

        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.tool_calls), 1)
        self.assertEqual(plan.tool_calls[0].tool_name, "simple_tool")
        self.assertEqual(plan.tool_calls[0].input["message"], "hello")

    def test_execute_task_success(self):
        """Test successful task execution."""
        task = Task(
            task_id="exec-test",
            description="Echo 'success' using simple_tool",
            available_tool_names=["simple_tool"],
            success_criteria="Output should be 'success'"
        )

        result = self.executor.execute_task(task)

        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(result.execution_history)
        self.assertEqual(len(result.execution_history), 1)
        self.assertEqual(result.execution_history[0].tool_name, "simple_tool")
        self.assertEqual(result.execution_history[0].result.output, "success")

    def test_execute_task_failure(self):
        """Test task execution with failing tool."""
        task = Task(
            task_id="fail-test",
            description="Use failing_tool",
            available_tool_names=["failing_tool"],
            success_criteria="Tool should succeed"
        )

        result = self.executor.execute_task(task)

        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertIsNotNone(result.error)
        self.assertIn("Intentional failure", result.error)

    def test_task_with_multiple_steps(self):
        """Test task execution with multiple tool calls."""
        # Register another simple tool
        self.executor.register_tool("tool_b", MockSimpleTool())

        task = Task(
            task_id="multi-test",
            description="Echo 'a' then echo 'b'",
            available_tool_names=["simple_tool", "tool_b"],
            success_criteria="Both echoes should complete"
        )

        result = self.executor.execute_task(task)

        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertEqual(len(result.execution_history), 2)
        self.assertEqual(result.execution_history[0].result.output, "a")
        self.assertEqual(result.execution_history[1].result.output, "b")

    def test_final_answer_generation(self):
        """Test final answer generation."""
        task = Task(
            task_id="answer-test",
            description="Echo 'final' using simple_tool",
            available_tool_names=["simple_tool"],
            success_criteria="Output should be 'final'"
        )

        result = self.executor.execute_task(task)

        self.assertIsNotNone(result.final_answer)
        self.assertIn("final", result.final_answer)

    def test_execution_timestamps(self):
        """Test that execution timestamps are recorded."""
        before = datetime.utcnow()

        task = Task(
            task_id="time-test",
            description="Simple task",
            available_tool_names=["simple_tool"],
            success_criteria="Task should complete"
        )

        result = self.executor.execute_task(task)

        after = datetime.utcnow()

        self.assertIsNotNone(result.started_at)
        self.assertGreaterEqual(result.started_at, before)
        self.assertLessEqual(result.started_at, after)
        self.assertIsNotNone(result.completed_at)
        self.assertGreaterEqual(result.completed_at, result.started_at)


class TestAgentExecutorIntegration(unittest.TestCase):
    """Integration tests for AgentExecutor."""

    def test_full_workflow(self):
        """Test complete workflow from task to result."""
        model = ModelInterface()
        executor = AgentExecutor(model=model)
        executor.register_tool("echo", MockSimpleTool())

        task = Task(
            task_id="integration-test",
            description="Echo 'integration'",
            available_tool_names=["echo"],
            success_criteria="Output should be 'integration'"
        )

        result = executor.execute_task(task)

        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(result.execution_history)
        self.assertEqual(len(result.execution_history), 1)
        self.assertEqual(result.execution_history[0].result.output, "integration")
        self.assertIsNotNone(result.final_answer)


if __name__ == "__main__":
    unittest.main()
