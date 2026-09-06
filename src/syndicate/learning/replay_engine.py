from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from syndicate.learning.skill import Skill
from syndicate.core.models.task import Task, TaskStatus, ToolCall, ToolResult
from syndicate.core.executor.agent_executor import AgentExecutor
from syndicate.core.recorder.trajectory_recorder import TrajectoryRecorder
from syndicate.core.evaluator.trajectory_evaluator import TrajectoryEvaluator


@dataclass
class ReplayResult:
    """The result of replaying a skill against a deterministic task."""
    success: bool
    skill_id: str
    trajectory_id: str
    final_answer: Optional[str]
    evaluation: Dict[str, Any]
    tool_sequence: List[str]
    tool_call_count: int
    error: Optional[str] = None


class ReplayEngine:
    """Orchestrates the replay of a synthesized skill against a task."""

    def _build_execution_plan(self, skill: Skill) -> List[ToolCall]:
        """
        Derive the guided execution plan directly from the Skill object and its learned metadata.

        Args:
            skill: The skill providing the deterministic tool procedure and learned parameters.

        Returns:
            Ordered list of ToolCall objects derived from skill.procedure and skill.metadata.
        """
        learned_params = skill.metadata.get("parameters", {}) if isinstance(skill.metadata, dict) else {}
        plan: List[ToolCall] = []
        for tool_name in skill.procedure:
            tool_input = learned_params.get(tool_name, {})
            input_data = dict(tool_input) if isinstance(tool_input, dict) else {}
            plan.append(ToolCall(tool_name=tool_name, input=input_data))
        return plan

    def replay(
        self,
        skill: Skill,
        task: Task,
        executor: AgentExecutor,
        recorder: TrajectoryRecorder,
        evaluator: TrajectoryEvaluator,
    ) -> ReplayResult:
        if not skill.validate():
            raise ValueError(f"Invalid skill: {skill.skill_id}")

        # 1. Build the execution plan directly from skill.procedure
        plan = self._build_execution_plan(skill)

        # 2. Check if all tools in the procedure are available in executor
        for tc in plan:
            if tc.tool_name not in executor.tools:
                return ReplayResult(
                    success=False,
                    skill_id=skill.skill_id,
                    trajectory_id="unknown-traj",
                    final_answer=None,
                    evaluation={},
                    tool_sequence=[],
                    tool_call_count=0,
                    error=f"Tool '{tc.tool_name}' not available in executor",
                )

        # 3. Create a NEW trajectory to record the replay (without mutating task.description)
        traj_id = recorder.record_trajectory_initialization(
            task_id=task.task_id,
            description=task.description,
            available_tools=task.available_tool_names,
            success_criteria=task.success_criteria or "",
        )

        # 4. Explicitly execute the guided execution plan
        tool_sequence: List[str] = []
        outputs: List[str] = []
        execution_error: Optional[str] = None
        replay_success = True

        for tc in plan:
            tool_obj = executor.tools.get(tc.tool_name)
            if not tool_obj:
                execution_error = f"Tool '{tc.tool_name}' not available in executor"
                replay_success = False
                break

            recorder.record_tool_call(traj_id, tc)
            tool_sequence.append(tc.tool_name)

            try:
                raw_result = tool_obj.execute(tc.input)
            except Exception as e:
                raw_result = {"success": False, "error": str(e)}

            if isinstance(raw_result, dict):
                success = raw_result.get("success", True)
                output = raw_result.get("output")
                error = raw_result.get("error")
            else:
                success = True
                output = str(raw_result)
                error = None

            tool_result = ToolResult(
                tool_name=tc.tool_name,
                success=success,
                output=output,
                error=error,
            )
            recorder.record_tool_result(traj_id, tool_result)

            if output is not None:
                outputs.append(str(output))

            if not success:
                replay_success = False
                execution_error = error or "Tool execution failed"
                break

        # 5. Record final answer and trajectory summary
        final_answer: Optional[str] = None
        if replay_success:
            final_answer = (
                f"Task completed successfully. Output: {', '.join(outputs)}"
                if outputs
                else "Task completed successfully."
            )
        recorder.record_final_answer(traj_id, final_answer or "")

        status_str = "completed" if replay_success else "failed"
        recorder.record_trajectory_summary(
            trajectory_id=traj_id,
            summary={
                "status": status_str,
                "metadata": {
                    "replayed_skill_id": skill.skill_id,
                    "source_trajectory_id": skill.source_trajectory_id,
                    "original_task_description": task.description,
                },
            },
        )

        # 6. Evaluate the replayed trajectory
        eval_result = evaluator.evaluate(traj_id, recorder)

        return ReplayResult(
            success=replay_success,
            skill_id=skill.skill_id,
            trajectory_id=traj_id,
            final_answer=final_answer,
            evaluation=eval_result,
            tool_sequence=tool_sequence,
            tool_call_count=len(tool_sequence),
            error=execution_error,
        )

    def compare(self, baseline_evaluation: Dict[str, Any], replay_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare the baseline execution against the replay execution.
        """
        baseline_score = baseline_evaluation.get("overall_score", 0.0)
        replay_score = replay_evaluation.get("overall_score", 0.0)

        delta = replay_score - baseline_score
        improved = delta > 0.0

        return {
            "baseline_score": baseline_score,
            "replay_score": replay_score,
            "score_delta": delta,
            "improved": improved,
        }

