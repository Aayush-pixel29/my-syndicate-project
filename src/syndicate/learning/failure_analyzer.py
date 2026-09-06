from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class FailureAnalysis:
    """Structured failure diagnosis."""
    failure_type: str
    root_cause: str
    evidence: List[str]
    recommended_change: str
    confidence: float


class FailureAnalyzer:
    """Analyzes a trajectory and its evaluation to determine the mode of failure."""

    def analyze(self, trajectory: Dict[str, Any], evaluation: Dict[str, Any]) -> FailureAnalysis:
        # 1. Missing or invalid evaluation
        if not evaluation or "overall_score" not in evaluation:
            return FailureAnalysis(
                failure_type="evaluation_failure",
                root_cause="Evaluation data is missing or invalid.",
                evidence=["Evaluation dict is empty or lacks 'overall_score'."],
                recommended_change="Ensure the evaluator ran successfully before analyzing failures.",
                confidence=1.0,
            )

        score = evaluation.get("overall_score", 0.0)
        details = evaluation.get("details", {})

        # Extract steps gracefully supporting both representations
        steps = trajectory.get("steps", [])
        if not steps:
            tool_calls = trajectory.get("tool_calls", [])
            tool_results = trajectory.get("tool_results", [])
            for i in range(max(len(tool_calls), len(tool_results))):
                step = {}
                if i < len(tool_calls):
                    step.update(tool_calls[i])
                if i < len(tool_results):
                    res = tool_results[i]
                    step["success"] = res.get("success", True)
                    step["output"] = res.get("output")
                    step["error"] = res.get("error")
                steps.append(step)

        # 2. Tool failure
        for i, step in enumerate(steps):
            is_success = step.get("success", True)
            status = step.get("status", "success")
            if not is_success or status == "error":
                error_msg = step.get("error", "Unknown error")
                tool_name = step.get("tool_name", "unknown")
                return FailureAnalysis(
                    failure_type="tool_failure",
                    root_cause=f"Tool '{tool_name}' failed during execution.",
                    evidence=[f"Step {i+1} ({tool_name}) error: {error_msg}"],
                    recommended_change="Fix the tool implementation or provide valid parameters.",
                    confidence=0.9,
                )

        # 3. Inefficient execution
        efficiency = details.get("efficiency", 1.0)
        seen_calls = set()
        repeated_call = None
        for step in steps:
            tool_name = step.get("tool_name")
            tool_input = str(step.get("input", step.get("tool_input", {})))
            call_sig = f"{tool_name}({tool_input})"
            if call_sig in seen_calls:
                repeated_call = call_sig
                break
            seen_calls.add(call_sig)

        if repeated_call or efficiency < 0.5:
            evidence = [f"Repeated tool call detected: {repeated_call}"] if repeated_call else [f"Efficiency score is low: {efficiency}"]
            return FailureAnalysis(
                failure_type="inefficient_execution",
                root_cause="The agent performed redundant or unnecessary operations.",
                evidence=evidence,
                recommended_change="Optimize the agent's prompts to avoid repeating identical tool calls.",
                confidence=0.85,
            )

        # 4. Incomplete execution
        completeness = details.get("task_completeness", 1.0)
        final_answer = trajectory.get("final_answer")
        if completeness < 1.0 or not final_answer:
            evidence = []
            if completeness < 1.0:
                evidence.append(f"Task completeness score: {completeness}")
            if not final_answer:
                evidence.append("Trajectory lacks a final_answer.")
            return FailureAnalysis(
                failure_type="incomplete_execution",
                root_cause="The agent stopped before fully completing the task.",
                evidence=evidence,
                recommended_change="Ensure the agent is instructed to complete all steps before finishing.",
                confidence=0.9,
            )

        # 5. Wrong tool sequence
        correctness = details.get("correctness", 1.0)
        if correctness < 0.8:
            return FailureAnalysis(
                failure_type="wrong_tool_sequence",
                root_cause="Tools succeeded but the final result was incorrect, implying wrong sequence or usage.",
                evidence=[f"Correctness score is {correctness}, despite tools succeeding."],
                recommended_change="Review the logical sequence of tool calls for this task.",
                confidence=0.75,
            )

        # 6. Success
        if score >= 0.8:
            return FailureAnalysis(
                failure_type="none",
                root_cause="No failure detected.",
                evidence=[f"Overall score: {score}"],
                recommended_change="No changes needed.",
                confidence=1.0,
            )

        # 7. Unknown failure
        return FailureAnalysis(
            failure_type="unknown_failure",
            root_cause="Task evaluation was poor but no specific failure pattern was matched.",
            evidence=[f"Overall score: {score}", f"Category: {evaluation.get('category')}"],
            recommended_change="Perform manual review of the trajectory.",
            confidence=0.5,
        )
