"""Tests for syndicate core engine."""

from .test_models import (
    TestTaskModels,
    TestToolInputSchema,
    TestToolCall,
    TestToolResult,
    TestToolInterface,
)

from .test_simulator import (
    TestGithubSimulator,
    TestGithubTool,
)

from .test_executor import (
    TestModelInterface,
    TestAgentExecutor,
    TestAgentExecutorIntegration,
)

from .test_recorder import (
    TestTrajectoryRecorder,
    TestTrajectoryRecorderIntegration,
)

from .test_evaluator import (
    TestTrajectoryEvaluator,
    TestTrajectoryEvaluatorIntegration,
)

__all__ = [
    "TestTaskModels",
    "TestToolInputSchema",
    "TestToolCall",
    "TestToolResult",
    "TestToolInterface",
    "TestGithubSimulator",
    "TestGithubTool",
    "TestModelInterface",
    "TestAgentExecutor",
    "TestAgentExecutorIntegration",
    "TestTrajectoryRecorder",
    "TestTrajectoryRecorderIntegration",
    "TestTrajectoryEvaluator",
    "TestTrajectoryEvaluatorIntegration",
]
