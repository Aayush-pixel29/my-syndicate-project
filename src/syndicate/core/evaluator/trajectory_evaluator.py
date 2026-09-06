"""Basic evaluator for Syndicate."""

from typing import Any, Dict, List, Optional

from ..recorder.trajectory_recorder import TrajectoryRecorder


class TrajectoryEvaluator:
    """
    Deterministic evaluator for trajectory quality.

    Evaluates trajectories based on:
    - Task completion
    - Correctness/accuracy
    - Tool efficiency
    - Reliability
    """

    def __init__(self, recorder: Optional[TrajectoryRecorder] = None):
        """
        Initialize the evaluator.

        Args:
            recorder: TrajectoryRecorder instance for accessing trajectory data.
                     If None, creates a new default recorder.
        """
        self.recorder = recorder or TrajectoryRecorder()

    def evaluate(
        self, trajectory_id: str, recorder: Optional[TrajectoryRecorder] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a trajectory using the provided recorder.

        This is a compatibility method that delegates to the internal
        evaluation logic.  It accepts an external recorder so callers
        can pass their own recorder instance.

        Args:
            trajectory_id: Trajectory identifier to evaluate.
            recorder: TrajectoryRecorder containing the trajectory data.
                     Falls back to self.recorder if not provided.

        Returns:
            Evaluation results with overall_score, category, and details.

        Raises:
            KeyError: If the trajectory does not exist in the recorder.
        """
        rec = recorder or self.recorder
        trajectory = rec.get_trajectory(trajectory_id)

        if trajectory is None:
            raise KeyError(f"Trajectory {trajectory_id} not found")

        # Gather tool calls and results (support both representations)
        tool_calls = trajectory.get("tool_calls", [])
        tool_results = trajectory.get("tool_results", [])
        # Also support the "steps" key used by record_trajectory
        steps = trajectory.get("steps", [])
        final_answer = trajectory.get("final_answer")

        # Detect failures
        failed_results = [
            r for r in tool_results
            if not r.get("success", True)
        ]
        failed_steps = [
            s for s in steps
            if s.get("status") == "error" or not s.get("success", True)
        ]
        has_failure = len(failed_results) > 0 or len(failed_steps) > 0

        # Count totals
        total_actions = len(tool_calls) + len(steps)
        total_results = len(tool_results)
        successful_results = len([
            r for r in tool_results if r.get("success", True)
        ])
        successful_steps = len([
            s for s in steps if s.get("status") == "success"
        ])

        # --- Task completeness ---
        if final_answer:
            task_completeness = 1.0
        elif tool_calls or steps:
            task_completeness = 0.5
        else:
            task_completeness = 0.0

        # --- Correctness ---
        if total_results > 0:
            correctness = successful_results / total_results
        elif successful_steps > 0:
            correctness = 1.0
        else:
            correctness = 0.5  # Unknown

        # --- Efficiency ---
        if total_actions > 0:
            efficiency = min(1.0, (successful_results + successful_steps) / max(total_actions, 1))
        else:
            efficiency = 0.0

        # --- Reliability ---
        if total_results > 0:
            reliability = successful_results / total_results
        elif len(steps) > 0:
            reliability = successful_steps / len(steps) if len(steps) > 0 else 0.0
        else:
            reliability = 0.5

        overall_score = (task_completeness + correctness + efficiency + reliability) / 4.0

        # Category
        if overall_score >= 0.8:
            category = "excellent"
        elif overall_score >= 0.6:
            category = "good"
        elif overall_score >= 0.4:
            category = "fair"
        else:
            category = "poor"

        result: Dict[str, Any] = {
            "overall_score": overall_score,
            "category": category,
            "details": {
                "task_completeness": task_completeness,
                "correctness": correctness,
                "efficiency": efficiency,
                "reliability": reliability,
            },
        }

        if has_failure:
            error_msgs = []
            for r in failed_results:
                e = r.get("error")
                if e:
                    error_msgs.append(str(e))
            for s in failed_steps:
                e = s.get("error")
                if e:
                    error_msgs.append(str(e))
            result["error"] = "; ".join(error_msgs) if error_msgs else "Tool execution failed"

        return result

    def evaluate_trajectory(
        self, trajectory_id: str, ground_truth: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a trajectory against success criteria.

        Args:
            trajectory_id: Trajectory identifier to evaluate.
            ground_truth: Optional ground truth for comparison.

        Returns:
            Evaluation results and scores.
        """
        trajectory = self.recorder.get_trajectory(trajectory_id)

        if not trajectory:
            return {"error": f"Trajectory {trajectory_id} not found"}

        # Extract evaluation metrics
        metrics = self._extract_metrics(trajectory)

        # Score based on metrics
        scores = self._calculate_scores(metrics, ground_truth)

        return {
            "trajectory_id": trajectory_id,
            "task_id": trajectory.get("task_id"),
            "scores": scores,
            "metrics": metrics,
            "summary": self._generate_summary(scores),
        }

    def _extract_metrics(self, trajectory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics from a trajectory.

        Args:
            trajectory: Trajectory data.

        Returns:
            Dictionary of metrics.
        """
        steps = trajectory.get("steps", [])
        tool_calls = trajectory.get("tool_calls", [])
        tool_results = trajectory.get("tool_results", [])

        # Use steps if available, otherwise combine tool_calls/tool_results
        if steps:
            successful_steps = [s for s in steps if s.get("status") == "success"]
            failed_steps = [s for s in steps if s.get("status") == "error"]
            total_tool_calls = len(steps)
            successful_calls = len(successful_steps)
            failed_calls = len(failed_steps)
        else:
            total_tool_calls = max(len(tool_calls), len(tool_results))
            successful_calls = len([r for r in tool_results if r.get("success", True)])
            failed_calls = len([r for r in tool_results if not r.get("success", True)])

        efficiency = (successful_calls / total_tool_calls) if total_tool_calls > 0 else 0.0
        reliability = (successful_calls / total_tool_calls) if total_tool_calls > 0 else 0.0

        # Calculate execution time
        all_items = steps or tool_results
        execution_times = [
            item.get("execution_time_ms", 0) for item in all_items if item.get("execution_time_ms")
        ]
        total_execution_time = sum(execution_times) if execution_times else 0

        # Tool usage distribution
        tool_usage: Dict[str, int] = {}
        for item in (steps or tool_calls):
            tool_name = item.get("tool_name", "unknown")
            if item.get("type") == "tool" or "tool_name" in item:
                tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

        # Determine success
        has_final_answer = trajectory.get("final_answer") is not None
        explicit_success = trajectory.get("success")
        if explicit_success is not None:
            is_success = explicit_success == 1 or explicit_success is True
        else:
            is_success = has_final_answer and failed_calls == 0

        return {
            "total_tool_calls": total_tool_calls,
            "successful_tool_calls": successful_calls,
            "failed_tool_calls": failed_calls,
            "tool_efficiency": efficiency,
            "reliability": reliability,
            "total_execution_time_ms": total_execution_time,
            "avg_execution_time_ms": total_execution_time / successful_calls if successful_calls > 0 else 0,
            "tool_usage": tool_usage,
            "success": is_success,
        }

    def _calculate_scores(
        self, metrics: Dict[str, Any], ground_truth: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculate scores based on metrics.

        Args:
            metrics: Extracted metrics.
            ground_truth: Optional ground truth for correctness scoring.

        Returns:
            Dictionary of scores.
        """
        # Task completion score (binary: did it succeed?)
        completion_score = 1.0 if metrics["success"] else 0.0

        # Correctness/accuracy score (based on ground truth comparison if available)
        correctness_score = 1.0
        if ground_truth:
            correctness_score = self._compare_with_ground_truth(metrics, ground_truth)

        # Tool efficiency score (0-1 scale)
        efficiency_score = metrics["tool_efficiency"]

        # Reliability score (0-1 scale)
        reliability_score = metrics["reliability"]

        # Penalty for failed tool calls
        failed_penalty = 0.0
        if metrics["failed_tool_calls"] > 0:
            failed_penalty = 0.2  # 20% penalty for each failed tool call

        # Final composite score
        final_score = (
            completion_score * 0.4
            + correctness_score * 0.2
            + efficiency_score * 0.2
            + reliability_score * 0.2
            - (failed_penalty if failed_penalty > 0 else 0)
        )

        # Clamp to valid range
        final_score = max(0.0, min(1.0, final_score))

        return {
            "completion": completion_score,
            "correctness": correctness_score,
            "efficiency": efficiency_score,
            "reliability": reliability_score,
            "composite": final_score,
        }

    def _compare_with_ground_truth(
        self, metrics: Dict[str, Any], ground_truth: Dict[str, Any]
    ) -> float:
        """
        Compare trajectory against ground truth.

        Args:
            metrics: Extracted metrics.
            ground_truth: Ground truth data.

        Returns:
            Correctness score (0-1).
        """
        # Check if the required tools were used
        required_tools = ground_truth.get("required_tools", [])
        used_tools = list(metrics["tool_usage"].keys())

        required_match = set(required_tools).issubset(set(used_tools))
        correctness = 1.0 if required_match else 0.5

        # Check if all required tools were successful
        required_tool_success = all(
            all(
                self._tool_used_successfully(metrics, tool)
                for tool in required_tools
            )
            if required_tools
            else True
        )

        if required_tool_success and required_match:
            correctness = 1.0
        elif not required_match:
            correctness = 0.5

        return correctness

    def _tool_used_successfully(self, metrics: Dict[str, Any], tool_name: str) -> bool:
        """
        Check if a tool was used successfully.

        Args:
            metrics: Extracted metrics.
            tool_name: Tool name to check.

        Returns:
            True if the tool was used and successful.
        """
        tool_count = metrics["tool_usage"].get(tool_name, 0)

        # Check if all uses of this tool were successful
        # This is a simplified check - in production, would track per-call success
        return tool_count > 0

    def _generate_summary(self, scores: Dict[str, float]) -> str:
        """
        Generate a human-readable summary of the evaluation.

        Args:
            scores: Scores from evaluation.

        Returns:
            Summary string.
        """
        components = []

        if scores["completion"] >= 1.0:
            components.append("Task was completed successfully")
        else:
            components.append("Task was not completed")

        if scores["correctness"] >= 0.8:
            components.append("Results are accurate")
        elif scores["correctness"] >= 0.5:
            components.append("Results are partially accurate")
        else:
            components.append("Results have accuracy issues")

        if scores["efficiency"] >= 0.8:
            components.append("Tool usage is efficient")
        else:
            components.append("Consider optimizing tool usage")

        return " ".join(components)

    def evaluate_multiple_trajectories(
        self, trajectory_ids: List[str], ground_truth: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple trajectories.

        Args:
            trajectory_ids: List of trajectory IDs to evaluate.
            ground_truth: Optional ground truth for comparison.

        Returns:
            List of evaluation results.
        """
        results = []

        for trajectory_id in trajectory_ids:
            result = self.evaluate_trajectory(trajectory_id, ground_truth)
            results.append(result)

        return results
