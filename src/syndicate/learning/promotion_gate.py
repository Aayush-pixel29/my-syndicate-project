from dataclasses import dataclass
from typing import Any, Dict

from syndicate.learning.skill import Skill


@dataclass
class PromotionDecision:
    """The outcome of deciding whether a synthesized Skill should be promoted."""
    promoted: bool
    reason: str
    baseline_score: float
    replay_score: float
    score_delta: float
    baseline_tool_calls: int
    replay_tool_calls: int
    metrics: Dict[str, Any]


class PromotionGate:
    """Decides deterministically whether a synthesized Skill should be promoted."""

    def decide(
        self,
        skill: Skill,
        baseline_evaluation: Dict[str, Any],
        replay_evaluation: Dict[str, Any],
        baseline_tool_call_count: int,
        replay_tool_call_count: int,
    ) -> PromotionDecision:
        """
        Evaluate baseline vs replay evidence to determine if a skill should be promoted.

        Args:
            skill: The synthesized Skill to evaluate.
            baseline_evaluation: Evaluation dictionary from the baseline trajectory.
            replay_evaluation: Evaluation dictionary from the replay trajectory.
            baseline_tool_call_count: Number of tool calls executed during baseline.
            replay_tool_call_count: Number of tool calls executed during replay.

        Returns:
            PromotionDecision detailing promotion status, reason, scores, and metrics.

        Raises:
            ValueError: If the skill fails validation.
        """
        if not skill.validate():
            raise ValueError(f"Invalid skill: {skill.skill_id}")

        baseline_score = float(baseline_evaluation.get("overall_score", 0.0))
        replay_score = float(replay_evaluation.get("overall_score", 0.0))
        score_delta = round(replay_score - baseline_score, 6)
        tool_call_delta = replay_tool_call_count - baseline_tool_call_count

        score_improved = score_delta > 0.0
        tool_calls_increased = tool_call_delta > 0
        tool_efficiency_improved = tool_call_delta < 0

        metrics = {
            "score_improved": score_improved,
            "tool_efficiency_improved": tool_efficiency_improved,
            "score_delta": score_delta,
            "tool_call_delta": tool_call_delta,
        }

        if score_improved and not tool_calls_increased:
            promoted = True
            reason = (
                f"Skill promoted: replay score improved by {score_delta:+.4f} "
                f"({baseline_score:.4f} -> {replay_score:.4f}) without increasing tool usage "
                f"({baseline_tool_call_count} -> {replay_tool_call_count})."
            )
        else:
            promoted = False
            if not score_improved and tool_calls_increased:
                reason = (
                    f"Promotion rejected: replay score did not improve (delta: {score_delta:+.4f}) "
                    f"and tool usage increased ({baseline_tool_call_count} -> {replay_tool_call_count})."
                )
            elif not score_improved:
                reason = (
                    f"Promotion rejected: replay score did not strictly improve over baseline "
                    f"({baseline_score:.4f} -> {replay_score:.4f}, delta: {score_delta:+.4f})."
                )
            else:  # tool_calls_increased
                reason = (
                    f"Promotion rejected: replay used more tool calls than baseline "
                    f"({baseline_tool_call_count} -> {replay_tool_call_count}, delta: {tool_call_delta:+d}) "
                    f"despite score improvement."
                )

        return PromotionDecision(
            promoted=promoted,
            reason=reason,
            baseline_score=baseline_score,
            replay_score=replay_score,
            score_delta=score_delta,
            baseline_tool_calls=baseline_tool_call_count,
            replay_tool_calls=replay_tool_call_count,
            metrics=metrics,
        )
