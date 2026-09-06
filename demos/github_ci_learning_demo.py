#!/usr/bin/env python3
"""
SkillFoundry Benchmark Demo: GitHub CI Investigation
Demonstrates Run 1 (Baseline Failure) -> Learn (Skill Synthesis) -> Run 2 (Guided Replay) -> Promotion Gate.
"""

import json
import os
import sys
from typing import Any, Dict

# Ensure src/ is in the Python search path for standalone execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from syndicate.core.models.task import Task, ToolInputSchema
from syndicate.core.models.tool import Tool as AbstractTool
from syndicate.core.simulator.github_simulator import GithubSimulator, GithubTool
from syndicate.core.executor.agent_executor import AgentExecutor
from syndicate.core.recorder.trajectory_recorder import TrajectoryRecorder
from syndicate.core.evaluator.trajectory_evaluator import TrajectoryEvaluator
from syndicate.learning.learning_loop import LearningLoop, summarize


class ListWorkflowRunsTool(AbstractTool):
    """Tool to list workflow runs for a repository."""

    def __init__(self, simulator: GithubSimulator, default_repo: str = "repocli/test-ci"):
        self._simulator = simulator
        self.default_repo = default_repo

    @property
    def name(self) -> str:
        return "list_workflow_runs"

    @property
    def description(self) -> str:
        return "List workflow runs for the repository"

    @property
    def input_schema(self) -> ToolInputSchema:
        return ToolInputSchema(
            type="object",
            description="List workflow runs",
            properties={
                "repo": {"type": "string", "description": "Repository name"},
                "branch": {"type": "string", "description": "Branch name", "default": "main"},
            },
        )

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        data = input_data or {}
        repo = data.get("repo", self.default_repo)
        branch = data.get("branch", "main")
        runs = self._simulator.list_workflow_runs(repo, branch)
        if isinstance(runs, list):
            return {"success": True, "output": runs}
        return {"success": False, "error": str(runs)}


class InspectWorkflowRunTool(AbstractTool):
    """Tool to inspect a specific workflow run."""

    def __init__(self, simulator: GithubSimulator, default_repo: str = "repocli/test-ci"):
        self._simulator = simulator
        self.default_repo = default_repo

    @property
    def name(self) -> str:
        return "inspect_workflow_run"

    @property
    def description(self) -> str:
        return "Inspect details and jobs for a specific workflow run"

    @property
    def input_schema(self) -> ToolInputSchema:
        return ToolInputSchema(
            type="object",
            description="Inspect workflow run details",
            required=["run_id"],
            properties={
                "repo": {"type": "string", "description": "Repository name"},
                "run_id": {"type": "integer", "description": "Workflow run ID"},
            },
        )

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        data = input_data or {}
        repo = data.get("repo", self.default_repo)
        raw_run_id = data.get("run_id")
        if raw_run_id is None:
            return {"success": False, "error": "run_id is required"}
        try:
            run_id = int(raw_run_id)
        except (ValueError, TypeError):
            return {"success": False, "error": f"Invalid run_id: {raw_run_id}"}

        result = self._simulator.inspect_workflow_run(repo, run_id)
        if isinstance(result, dict) and "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "output": result}


class InspectJobLogsTool(AbstractTool):
    """Tool to inspect logs for a specific workflow job."""

    def __init__(
        self,
        simulator: GithubSimulator,
        default_repo: str = "repocli/test-ci",
    ):
        self._simulator = simulator
        self.default_repo = default_repo

    @property
    def name(self) -> str:
        return "inspect_job_logs"

    @property
    def description(self) -> str:
        return "Inspect logs for a specific CI job"

    @property
    def input_schema(self) -> ToolInputSchema:
        return ToolInputSchema(
            type="object",
            description="Inspect job logs",
            properties={
                "repo": {"type": "string", "description": "Repository name"},
                "run_id": {"type": "integer", "description": "Workflow run ID"},
                "job_name": {"type": "string", "description": "Job name"},
            },
        )

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        data = input_data or {}
        repo = data.get("repo", self.default_repo)
        raw_run_id = data.get("run_id", 2)
        try:
            run_id = int(raw_run_id)
        except (ValueError, TypeError):
            return {"success": False, "error": f"Invalid run_id: {raw_run_id}"}
        job_name = data.get("job_name", "test")

        logs = self._simulator.inspect_job_logs(repo, run_id, job_name)
        if logs.startswith("Error:") or logs.startswith("Job '"):
            return {"success": False, "error": logs}
        return {"success": True, "output": logs}


class InspectCommitTool(AbstractTool):
    """Tool to inspect details of a specific commit without hard-coded fallbacks."""

    def __init__(
        self,
        simulator: GithubSimulator,
        default_repo: str = "repocli/test-ci",
    ):
        self._simulator = simulator
        self.default_repo = default_repo

    @property
    def name(self) -> str:
        return "inspect_commit"

    @property
    def description(self) -> str:
        return "Inspect commit metadata and changes"

    @property
    def input_schema(self) -> ToolInputSchema:
        return ToolInputSchema(
            type="object",
            description="Inspect commit details",
            required=["sha"],
            properties={
                "repo": {"type": "string", "description": "Repository name"},
                "sha": {"type": "string", "description": "Commit SHA"},
            },
        )

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        data = input_data or {}
        repo = data.get("repo", self.default_repo)
        sha = data.get("sha")
        if not sha:
            return {"success": False, "error": "sha is required"}

        result = self._simulator.inspect_commit(repo, sha)
        if isinstance(result, dict) and "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "output": result}


def create_demo_executor(simulator: GithubSimulator) -> AgentExecutor:
    """Create and configure an AgentExecutor with granular GitHub tools."""
    executor = AgentExecutor()
    executor.register_tool("list_workflow_runs", ListWorkflowRunsTool(simulator))
    executor.register_tool("inspect_workflow_run", InspectWorkflowRunTool(simulator))
    executor.register_tool("inspect_job_logs", InspectJobLogsTool(simulator))
    executor.register_tool("inspect_commit", InspectCommitTool(simulator))
    executor.register_tool("github", GithubTool(simulator))
    return executor


def run_demo():
    print("=== SKILLFOUNDRY LEARNING DEMO ===")

    # 1. Initialize the deterministic GitHub simulator
    simulator = GithubSimulator()
    simulator.initialize()

    # 2. Register granular GitHub tools with AgentExecutor
    executor = create_demo_executor(simulator)

    # 3. Create a realistic task where Run 1 attempts an investigation with an invalid commit SHA
    task = Task(
        task_id="ci-investigation-task",
        description="Use list_workflow_runs then Use inspect_job_logs then Use inspect_commit 'invalid_sha_000'",
        available_tool_names=["list_workflow_runs", "inspect_workflow_run", "inspect_job_logs", "inspect_commit"],
        success_criteria="Identify and investigate CI failure in repocli/test-ci",
    )

    # 4. Initialize LearningLoop with in-memory recorder and evaluator
    recorder = TrajectoryRecorder("memory")
    evaluator = TrajectoryEvaluator()
    loop = LearningLoop()

    # 5. Execute complete LearningLoop
    result = loop.run(
        task=task,
        executor=executor,
        recorder=recorder,
        evaluator=evaluator,
    )

    # 6. Extract baseline tool sequence
    baseline_traj = recorder.get_trajectory(result.baseline_trajectory_id) or {}
    baseline_tool_calls = baseline_traj.get("tool_calls", [])
    baseline_tool_sequence = [tc.get("tool_name", "unknown") for tc in baseline_tool_calls]

    # Print structured report
    print("\nBASELINE / RUN 1")
    print(f"- trajectory id:          {result.baseline_trajectory_id}")
    print(f"- evaluation score:       {result.baseline_evaluation.get('overall_score', 0.0):.4f}")
    print(f"- failure type:           {result.failure_analysis.failure_type}")
    print(f"- observed tool sequence: {baseline_tool_sequence}")
    print(f"- tool call count:        {len(baseline_tool_sequence)}")

    print("\nLEARNING")
    print(f"- synthesized skill id:   {result.skill.skill_id}")
    print(f"- skill name:             {result.skill.name}")
    print(f"- skill trigger:          {result.skill.trigger}")
    print(f"- skill procedure:        {result.skill.procedure}")
    learned_params = result.skill.metadata.get("parameters", {})
    print(f"- learned parameters:")
    for tool_name, params in learned_params.items():
        for param_k, param_v in params.items():
            print(f"  {tool_name}.{param_k} = {param_v}")
    param_prov = result.skill.metadata.get("parameter_provenance", {})
    if "inspect_commit.sha" in param_prov:
        prov = param_prov["inspect_commit.sha"]
        print(f"  source = prior successful {prov.get('source_tool')} output ({prov.get('source_field')})")
    print(f"- root cause:             {result.failure_analysis.root_cause}")
    print(f"- recommended change:     {result.failure_analysis.recommended_change}")
    print(f"- skill provenance:       source_trajectory_id = {result.skill.source_trajectory_id}")

    print("\nREPLAY / RUN 2")
    print(f"- replay trajectory id:   {result.replay_result.trajectory_id}")
    print(f"- replay score:           {result.replay_result.evaluation.get('overall_score', 0.0):.4f}")
    print(f"- replay tool sequence:   {result.replay_result.tool_sequence}")
    print(f"- replay tool call count: {result.replay_result.tool_call_count}")

    print("\nPROMOTION")
    print(f"- score delta:            {result.promotion_decision.score_delta:+.4f}")
    print(f"- tool call delta:        {result.promotion_decision.metrics.get('tool_call_delta', 0):+d}")
    print(f"- improved:               {result.promotion_decision.metrics.get('score_improved', False)}")
    print(f"- promoted:               {result.promotion_decision.promoted}")
    print(f"- promotion reason:       {result.promotion_decision.reason}")

    print("\nFINAL")
    conclusion = (
        "Skill promoted: replay improved quality without increasing tool usage."
        if result.promotion_decision.promoted
        else "Skill rejected: replay did not meet promotion criteria."
    )
    print(f"- {conclusion}")

    print("\nSUMMARY (JSON)")
    summary_data = summarize(result)
    print(json.dumps(summary_data, indent=2))

    return result


if __name__ == "__main__":
    run_demo()
