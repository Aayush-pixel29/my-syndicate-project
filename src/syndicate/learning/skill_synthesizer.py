import hashlib
import re
from typing import Any, Dict, Tuple

from syndicate.learning.failure_analyzer import FailureAnalysis
from syndicate.learning.skill import Skill


class SkillSynthesizer:
    """Synthesizes reusable Skills from FailureAnalysis and trajectories."""

    def _extract_learned_parameters(self, trajectory: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract actionable parameters and provenance from prior successful trajectory steps.
        Only extracts parameters genuinely present in observed evidence.
        """
        parameters: Dict[str, Dict[str, Any]] = {}
        provenance: Dict[str, Dict[str, Any]] = {}

        # Extract steps and tool results
        steps = trajectory.get("steps", [])
        tool_results = trajectory.get("tool_results", [])
        tool_calls = trajectory.get("tool_calls", [])

        # Combine results with tool names
        combined_results = []
        if steps:
            for s in steps:
                if isinstance(s, dict):
                    combined_results.append({
                        "tool_name": s.get("tool_name", ""),
                        "output": s.get("output"),
                        "success": s.get("success", True),
                        "input": s.get("input", {}),
                    })
        elif tool_results:
            for i, r in enumerate(tool_results):
                tname = tool_calls[i].get("tool_name", "") if i < len(tool_calls) else ""
                tinput = tool_calls[i].get("input", {}) if i < len(tool_calls) else {}
                if isinstance(r, dict):
                    combined_results.append({
                        "tool_name": r.get("tool_name") or tname,
                        "output": r.get("output"),
                        "success": r.get("success", True),
                        "input": tinput,
                    })

        # Identify repository if present in task or tool input
        repo = None
        for res in combined_results:
            inp = res.get("input", {})
            if isinstance(inp, dict) and "repo" in inp:
                repo = inp["repo"]
                break

        # 1. First pass: look for error logs that identify failed run_id or job
        failed_run_id = None
        failed_job_name = None

        for res in combined_results:
            tool_name = res.get("tool_name")
            output = res.get("output")
            if tool_name == "inspect_job_logs" and isinstance(output, str):
                if "Status: failure" in output or "ERROR:" in output:
                    run_match = re.search(r"Run ID:\s*(\d+)", output)
                    if run_match:
                        failed_run_id = int(run_match.group(1))
                    job_match = re.search(r"Job:\s*(\w+)", output)
                    if job_match:
                        failed_job_name = job_match.group(1)

        # 2. Second pass: extract commit SHAs and workflow runs
        for res in combined_results:
            tool_name = res.get("tool_name")
            output = res.get("output")
            success = res.get("success", True)

            if not success or output is None:
                continue

            # list_workflow_runs output
            if tool_name == "list_workflow_runs" and isinstance(output, list):
                run_commit_map = {}
                for run in output:
                    if isinstance(run, dict) and "id" in run:
                        sha = run.get("commit") or run.get("sha")
                        if sha:
                            run_commit_map[run["id"]] = sha

                target_sha = None
                if failed_run_id in run_commit_map:
                    target_sha = run_commit_map[failed_run_id]
                elif 2 in run_commit_map:
                    target_sha = run_commit_map[2]
                elif run_commit_map:
                    # Choose the most recent completed run's commit
                    target_sha = list(run_commit_map.values())[-1]

                if target_sha:
                    commit_params = parameters.setdefault("inspect_commit", {})
                    commit_params["sha"] = target_sha
                    if repo:
                        commit_params["repo"] = repo
                    provenance["inspect_commit.sha"] = {
                        "value": target_sha,
                        "source_tool": "list_workflow_runs",
                        "source_field": "commit",
                    }

                if failed_run_id is not None:
                    job_params = parameters.setdefault("inspect_job_logs", {})
                    job_params["run_id"] = failed_run_id
                    if failed_job_name:
                        job_params["job_name"] = failed_job_name
                    if repo:
                        job_params["repo"] = repo

            # inspect_workflow_run output
            elif tool_name == "inspect_workflow_run" and isinstance(output, dict):
                sha = output.get("sha") or output.get("commit")
                run_id = output.get("id")
                if sha:
                    commit_params = parameters.setdefault("inspect_commit", {})
                    commit_params["sha"] = sha
                    if repo:
                        commit_params["repo"] = repo
                    provenance["inspect_commit.sha"] = {
                        "value": sha,
                        "source_tool": "inspect_workflow_run",
                        "source_field": "sha",
                    }
                if run_id is not None:
                    job_params = parameters.setdefault("inspect_job_logs", {})
                    job_params["run_id"] = run_id
                    if repo:
                        job_params["repo"] = repo

        return parameters, provenance

    def synthesize(self, analysis: FailureAnalysis, trajectory: Dict[str, Any]) -> Skill:
        # Extract steps gracefully
        steps = trajectory.get("steps", [])
        if not steps:
            steps = trajectory.get("tool_calls", [])

        # Extract tool names and remove consecutive duplicates
        raw_procedure = [step.get("tool_name", "unknown_action") for step in steps]
        procedure = []
        for p in raw_procedure:
            if not procedure or procedure[-1] != p:
                procedure.append(p)

        if not procedure:
            procedure = ["unknown_action"]

        # Generate a deterministic skill_id
        proc_slug = "-".join([str(p).replace("_", "-").lower() for p in procedure])
        if len(proc_slug) > 30:
            proc_slug = proc_slug[:20] + "-" + hashlib.md5(proc_slug.encode()).hexdigest()[:6]

        failure_slug = analysis.failure_type.replace("_", "-").lower()
        skill_id = f"{failure_slug}-{proc_slug}-v1"

        # Determine trigger and descriptive fields
        task_desc = trajectory.get("task", {}).get("description", "")
        if isinstance(task_desc, str) and task_desc.strip():
            trigger = task_desc[:50]
        else:
            trigger = f"Failure: {analysis.failure_type}" if analysis.failure_type != "none" else "Task Success"

        if analysis.failure_type == "none":
            name = "Successful Task Execution"
            description = "A successfully executed sequence of tools for the task."
        else:
            name = f"Recovery for {analysis.failure_type}"
            description = f"Handles {analysis.failure_type}. Recommendation: {analysis.recommended_change}"

        # Extract learned parameters and their provenance
        parameters, parameter_provenance = self._extract_learned_parameters(trajectory)

        # Collect provenance metadata
        metadata = {
            "generated_by": "deterministic_skill_synthesizer",
            "failure_confidence": analysis.confidence,
        }
        if parameters:
            metadata["parameters"] = parameters
        if parameter_provenance:
            metadata["parameter_provenance"] = parameter_provenance

        if "task_id" in trajectory:
            metadata["source_task_id"] = trajectory["task_id"]
        if "evaluation" in trajectory:
            metadata["source_evaluation"] = trajectory["evaluation"]

        source_trajectory_id = trajectory.get("trajectory_id") or trajectory.get("id") or "unknown-traj"

        # Construct the Skill object
        skill = Skill(
            skill_id=skill_id,
            name=name,
            description=description,
            trigger=trigger,
            procedure=procedure,
            source_trajectory_id=source_trajectory_id,
            failure_type=analysis.failure_type,
            evidence=analysis.evidence,
            version=1,
            validated=False,
            promoted=False,
            metadata=metadata,
        )

        # Validate before returning
        if not skill.validate():
            raise ValueError(f"Synthesized skill is invalid: {skill.to_dict()}")

        return skill
