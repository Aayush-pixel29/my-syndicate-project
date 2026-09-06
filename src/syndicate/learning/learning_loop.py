"""End-to-end Learning Loop for SkillFoundry."""

import copy
from dataclasses import dataclass
from typing import Any, Dict, Optional

from syndicate.core.models.task import Task, TaskStatus, ToolCall
from syndicate.core.executor.agent_executor import AgentExecutor
from syndicate.core.recorder.trajectory_recorder import TrajectoryRecorder
from syndicate.core.evaluator.trajectory_evaluator import TrajectoryEvaluator
from syndicate.learning.failure_analyzer import FailureAnalyzer, FailureAnalysis
from syndicate.learning.skill import Skill
from syndicate.learning.skill_synthesizer import SkillSynthesizer
from syndicate.learning.replay_engine import ReplayEngine, ReplayResult
from syndicate.learning.promotion_gate import PromotionGate, PromotionDecision


@dataclass
class LearningRunResult:
    """Complete result of an end-to-end learning run."""
    baseline_trajectory_id: str
    baseline_evaluation: Dict[str, Any]
    failure_analysis: FailureAnalysis
    skill: Skill
    replay_result: ReplayResult
    promotion_decision: PromotionDecision


def summarize(result: LearningRunResult) -> Dict[str, Any]:
    """
    Produce a compact JSON-serializable benchmark summary of a LearningRunResult.
    """
    score_delta = result.promotion_decision.score_delta
    tool_call_delta = result.promotion_decision.metrics.get(
        "tool_call_delta",
        result.promotion_decision.replay_tool_calls - result.promotion_decision.baseline_tool_calls
    )
    improved = result.promotion_decision.metrics.get("score_improved", score_delta > 0.0)

    return {
        "baseline_score": result.promotion_decision.baseline_score,
        "replay_score": result.promotion_decision.replay_score,
        "score_delta": score_delta,
        "baseline_tool_calls": result.promotion_decision.baseline_tool_calls,
        "replay_tool_calls": result.promotion_decision.replay_tool_calls,
        "tool_call_delta": tool_call_delta,
        "improved": improved,
        "promoted": result.promotion_decision.promoted,
        "failure_type": result.failure_analysis.failure_type,
        "skill_id": result.skill.skill_id,
        "baseline_trajectory_id": result.baseline_trajectory_id,
        "replay_trajectory_id": result.replay_result.trajectory_id,
    }


class LearningLoop:
    """Orchestrates baseline execution, failure analysis, skill synthesis, replay, and promotion."""

    def __init__(
        self,
        failure_analyzer: Optional[FailureAnalyzer] = None,
        skill_synthesizer: Optional[SkillSynthesizer] = None,
        replay_engine: Optional[ReplayEngine] = None,
        promotion_gate: Optional[PromotionGate] = None,
    ):
        self.failure_analyzer = failure_analyzer or FailureAnalyzer()
        self.skill_synthesizer = skill_synthesizer or SkillSynthesizer()
        self.replay_engine = replay_engine or ReplayEngine()
        self.promotion_gate = promotion_gate or PromotionGate()

    def summarize(self, result: LearningRunResult) -> Dict[str, Any]:
        """Convenience method to summarize a run result."""
        return summarize(result)

    def run(
        self,
        task: Task,
        executor: AgentExecutor,
        recorder: TrajectoryRecorder,
        evaluator: TrajectoryEvaluator,
    ) -> LearningRunResult:
        """
        Execute the end-to-end Learning Loop:
        1. Record & execute baseline task.
        2. Evaluate baseline trajectory.
        3. Analyze baseline trajectory for failure patterns.
        4. Synthesize a reusable Skill.
        5. Replay the Skill against the environment in a new trajectory.
        6. Compare baseline vs replay results via PromotionGate.
        7. Return a complete LearningRunResult.
        """
        # 1. Initialize and record baseline trajectory
        baseline_traj_id = recorder.record_trajectory_initialization(
            task_id=task.task_id,
            description=task.description,
            available_tools=task.available_tool_names,
            success_criteria=task.success_criteria or "",
        )

        executed_task = executor.execute_task(task)

        if executed_task.execution_history:
            for step in executed_task.execution_history:
                tc = ToolCall(tool_name=step.tool_name, input={})
                recorder.record_tool_call(baseline_traj_id, tc)
                recorder.record_tool_result(baseline_traj_id, step.result)

        recorder.record_final_answer(baseline_traj_id, executed_task.final_answer or "")
        status_str = "completed" if executed_task.status == TaskStatus.COMPLETED else "failed"
        recorder.record_trajectory_summary(
            trajectory_id=baseline_traj_id,
            summary={
                "status": status_str,
                "metadata": {
                    "task_description": task.description,
                    "task_id": task.task_id,
                },
            },
        )

        # 2. Evaluate baseline trajectory
        raw_baseline_eval = evaluator.evaluate(baseline_traj_id, recorder)
        baseline_eval = raw_baseline_eval if isinstance(raw_baseline_eval, dict) else {}

        # 3. Analyze baseline trajectory
        baseline_traj_data = recorder.get_trajectory(baseline_traj_id) or {}
        analysis = self.failure_analyzer.analyze(baseline_traj_data, baseline_eval)

        # 4. Synthesize Skill
        synthesized_skill = self.skill_synthesizer.synthesize(analysis, baseline_traj_data)

        # 5. Replay synthesized Skill
        replay_result = self.replay_engine.replay(
            skill=synthesized_skill,
            task=task,
            executor=executor,
            recorder=recorder,
            evaluator=evaluator,
        )

        # 6. Count baseline tool calls
        baseline_tool_calls = len(baseline_traj_data.get("tool_calls", []))
        if baseline_tool_calls == 0 and executed_task.execution_history:
            baseline_tool_calls = len(executed_task.execution_history)

        # 7. Evaluate promotion
        replay_eval = replay_result.evaluation if isinstance(replay_result.evaluation, dict) else {}
        decision = self.promotion_gate.decide(
            skill=synthesized_skill,
            baseline_evaluation=baseline_eval,
            replay_evaluation=replay_eval,
            baseline_tool_call_count=baseline_tool_calls,
            replay_tool_call_count=replay_result.tool_call_count,
        )

        # 8. Produce explicit Skill state copy without mutating original
        final_skill = copy.deepcopy(synthesized_skill)
        if decision.promoted:
            final_skill.promoted = True
            final_skill.validated = True

        return LearningRunResult(
            baseline_trajectory_id=baseline_traj_id,
            baseline_evaluation=baseline_eval,
            failure_analysis=analysis,
            skill=final_skill,
            replay_result=replay_result,
            promotion_decision=decision,
        )
