"""Agent executor for Syndicate."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.task import Task, ToolCall, ToolResult, TaskStatus


@dataclass
class ExecutionStep:
    """A single step in the execution history."""
    tool_name: str
    result: ToolResult


@dataclass
class TaskPlan:
    """A plan of tool calls for a task."""
    tool_calls: List[ToolCall] = field(default_factory=list)


class ModelInterface:
    """
    Interface for LLM model integration.

    This interface keeps model integration isolated for testability.
    """

    @staticmethod
    def chat(
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """
        Send a chat request to the model.

        Args:
            system_prompt: System prompt for the model.
            messages: List of messages in the chat.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            Model response containing generated text.
        """
        # Placeholder for actual model integration
        # In production, this would call the TensorMux GLM-4.7-Flash API
        return {
            "content": "placeholder_response",
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "total_tokens": 30,
            "model": "placeholder",
        }

    def generate_answer(
        self,
        question: str,
        tools: List[str],
        context: str,
    ) -> Dict[str, Any]:
        """
        Generate an answer to a question.

        Args:
            question: The question to answer.
            tools: Available tools for the answer.
            context: Context information.

        Returns:
            Dictionary containing the generated answer.
        """
        # Placeholder for actual model integration
        return {
            "answer": "placeholder_answer",
            "reasoning": "Placeholder reasoning",
        }

    def parse_action(
        self,
        current_state: str,
        available_tools: List[str],
    ) -> Dict[str, Any]:
        """
        Parse the model's action from the current state.

        Args:
            current_state: Current state description.
            available_tools: List of available tools.

        Returns:
            Dictionary containing parsed action.
        """
        # Placeholder for actual model integration
        return {
            "action_type": "tool",
            "tool_name": "unknown_tool",
            "parameters": {},
        }


class AgentExecutor:
    """
    Minimal agent executor that selects and executes tools.

    The executor uses the configured LLM to choose tools and execute
    them sequentially to complete tasks.
    """

    def __init__(
        self,
        model_interface: Optional[ModelInterface] = None,
        model: Optional[ModelInterface] = None,
    ):
        """
        Initialize the executor.

        Args:
            model_interface: Model interface for LLM integration.
                            If None, uses default interface.
            model: Alias for model_interface for backward compatibility.
                  If model is provided but model_interface is None, uses model.
        """
        if model is not None and model_interface is None:
            self.model = model
        else:
            self.model = model_interface or ModelInterface()
        self._tools: Dict[str, Any] = {}

    @property
    def tools(self) -> Dict[str, Any]:
        """Backward-compatible access to registered tools."""
        return self._tools

    def register_tool(self, name: str, tool_obj: Any):
        """
        Register a tool for the executor.

        Args:
            name: Tool name.
            tool_obj: Tool object with execute method.
        """
        self._tools[name] = tool_obj

    def plan_task(self, task: Task) -> TaskPlan:
        """
        Plan tool calls for a task based on its description.

        Parses the task description to determine which tools to invoke
        and with what parameters.

        Args:
            task: Task to plan.

        Returns:
            TaskPlan containing ordered tool calls.
        """
        description = task.description
        available = list(task.available_tool_names)

        # Split by "then" to get sub-tasks
        parts = re.split(r'\s+then\s+', description, flags=re.IGNORECASE)

        tool_calls: List[ToolCall] = []
        tool_idx = 0

        for part in parts:
            # Extract quoted values
            quotes = re.findall(r"'([^']*)'", part)

            # Check for "using TOOL_NAME" pattern
            using_match = re.search(r'using\s+(\S+)', part, re.IGNORECASE)
            # Check for "Use TOOL_NAME" pattern
            use_match = re.search(r'\bUse\s+(\S+)', part.strip(), re.IGNORECASE)

            if using_match and using_match.group(1) in self._tools:
                tool_name = using_match.group(1)
            elif use_match and use_match.group(1) in self._tools:
                tool_name = use_match.group(1)
            elif tool_idx < len(available):
                tool_name = available[tool_idx]
                tool_idx += 1
            else:
                continue

            # Build input based on tool schema
            tool_obj = self._tools.get(tool_name)
            input_data: Dict[str, Any] = {}

            if tool_obj and hasattr(tool_obj, 'input_schema'):
                schema = tool_obj.input_schema
                required = schema.required if schema.required else []
                if quotes and required:
                    input_data[required[0]] = quotes[0]
                elif required:
                    input_data[required[0]] = part.strip()
            elif quotes:
                input_data["message"] = quotes[0]

            tool_calls.append(ToolCall(tool_name=tool_name, input=input_data))

        return TaskPlan(tool_calls=tool_calls)

    def execute_task(self, task: Task) -> Task:
        """
        Execute a task using available tools.

        Args:
            task: Task to execute.

        Returns:
            The Task object with status, execution_history, final_answer,
            started_at, and completed_at populated.
        """
        task.started_at = datetime.utcnow()
        task.status = TaskStatus.IN_PROGRESS

        try:
            plan = self.plan_task(task)
            execution_history: List[ExecutionStep] = []

            for tc in plan.tool_calls:
                tool_obj = self._tools.get(tc.tool_name)
                if not tool_obj:
                    task.status = TaskStatus.FAILED
                    task.error = f"Tool '{tc.tool_name}' not found"
                    task.execution_history = execution_history
                    task.completed_at = datetime.utcnow()
                    return task

                raw_result = tool_obj.execute(tc.input)

                success = raw_result.get("success", True)
                output = raw_result.get("output")
                error = raw_result.get("error")

                tool_result = ToolResult(
                    tool_name=tc.tool_name,
                    success=success,
                    output=output,
                    error=error,
                )

                step = ExecutionStep(tool_name=tc.tool_name, result=tool_result)
                execution_history.append(step)

                if not success:
                    task.status = TaskStatus.FAILED
                    task.error = error or "Tool execution failed"
                    task.execution_history = execution_history
                    task.completed_at = datetime.utcnow()
                    return task

            # All tools succeeded
            task.status = TaskStatus.COMPLETED
            task.execution_history = execution_history

            # Generate final answer
            outputs = [
                str(s.result.output)
                for s in execution_history
                if s.result.output is not None
            ]
            task.final_answer = (
                f"Task completed successfully. Output: {', '.join(outputs)}"
                if outputs
                else "Task completed successfully."
            )

            task.completed_at = datetime.utcnow()
            return task

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            return task

    # ------------------------------------------------------------------
    # Legacy internal methods preserved for backward compatibility
    # ------------------------------------------------------------------

    def _plan_and_execute(self, task: Task) -> List[Dict[str, Any]]:
        """
        Plan and execute tool calls to complete the task.

        Args:
            task: Task to execute.

        Returns:
            List of execution steps.
        """
        steps = []
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Generate action based on task and current state
            action = self._decide_action(task)

            if action["type"] == "finish":
                steps.append(action)
                break

            # Execute the action
            result = self._execute_action(action)
            steps.append(result)

            if result["status"] == "error":
                break

        return steps

    def _decide_action(self, task: Task) -> Dict[str, Any]:
        """
        Decide what action to take next.

        Args:
            task: Current task state.

        Returns:
            Dictionary with action type and parameters.
        """
        # Build prompt for the model
        prompt = self._build_action_prompt(task)

        # Call the model
        response = self.model.chat(
            system_prompt="You are an AI assistant that helps troubleshoot CI issues. Choose actions to execute tools.",
            messages=[
                {"role": "system", "content": "You are an AI assistant that helps troubleshoot CI issues. Choose actions to execute tools."},
                {"role": "user", "content": prompt},
            ],
        )

        # Parse the action (simplified parsing - would use structured output in production)
        response_text = response.get("content", "")

        if "finish" in response_text.lower() or "complete" in response_text.lower():
            return {"type": "finish", "reason": "Task completed"}

        # Default: execute a tool
        tool_name = response_text.split()[0] if response_text else ""
        return {
            "type": "tool",
            "tool_name": tool_name,
            "tool_input": {"operation": tool_name, **self._extract_tool_params(response_text)},
        }

    def _extract_tool_params(self, response_text: str) -> Dict[str, Any]:
        """
        Extract tool parameters from response text.

        Args:
            response_text: Response from the model.

        Returns:
            Dictionary of extracted parameters.
        """
        params = {}
        words = response_text.split()

        # Simple parameter extraction logic
        if len(words) >= 2:
            if "repo" in response_text.lower():
                params["repo"] = words[1]
            if "branch" in response_text.lower():
                params["branch"] = words[1]
            if "run_id" in response_text.lower() and any(char.isdigit() for char in response_text):
                # Find the number in the response
                for i, word in enumerate(words):
                    if word.isdigit():
                        params["run_id"] = int(word)
                        break

        return params

    def _build_action_prompt(self, task: Task) -> str:
        """
        Build a prompt for the model to decide actions.

        Args:
            task: Current task state.

        Returns:
            Formatted prompt string.
        """
        available_tools = "\n".join(
            [f"- {name}: {tool.description}" for name, tool in self._tools.items()]
        )

        return f"""Current task: {task.description}
Success criteria: {task.success_criteria or 'Not specified'}

Available tools:
{available_tools}

What action should I take to complete this task?
Options: list [tool_name] [params] or finish task.

Respond with your action decision."""

    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an action.

        Args:
            action: Action dictionary.

        Returns:
            Execution result.
        """
        if action["type"] == "finish":
            return {"type": "finish", "status": "success", "reason": action["reason"]}

        if action["type"] == "tool":
            tool_name = action["tool_name"]
            tool_input = action["tool_input"]

            if tool_name not in self._tools:
                return {
                    "type": "tool",
                    "status": "error",
                    "tool_name": tool_name,
                    "error": f"Tool '{tool_name}' not found",
                }

            tool = self._tools[tool_name]
            result = tool.execute(tool_input)

            return {
                "type": "tool",
                "status": "success",
                "tool_name": tool_name,
                "input": tool_input,
                "output": result,
            }

        return {"type": "error", "status": "error", "error": "Unknown action type"}

    def _generate_final_answer(
        self, task: Task, steps: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a final answer based on task completion.

        Args:
            task: Completed task.
            steps: Execution steps.

        Returns:
            Final answer string.
        """
        tool_steps = [s for s in steps if s["type"] == "tool"]
        success_steps = [s for s in tool_steps if s["status"] == "success"]

        if not success_steps:
            return "I was unable to complete the task. Please check the error messages."

        return f"Task completed with {len(success_steps)} successful tool executions."
