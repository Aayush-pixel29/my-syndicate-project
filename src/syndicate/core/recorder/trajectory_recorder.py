"""Trajectory recorder for Syndicate."""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.task import Task, ToolCall, ToolResult


class TrajectoryRecorder:
    """
    Recorder for tracking tool execution trajectories.

    Records trajectories for evaluation and analysis purposes.
    Supports both in-memory storage and SQLite persistence.
    """

    def __init__(self, storage_type: str = "memory", db_path: Optional[str] = None):
        """
        Initialize the trajectory recorder.

        Args:
            storage_type: Storage type ("memory" or "sqlite").
            db_path: Path to SQLite database (only used if storage_type is "sqlite").
        """
        self.storage_type = storage_type
        self.trajectories: List[Dict[str, Any]] = []
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

        if storage_type == "sqlite" and db_path:
            self._init_sqlite(db_path)

    def _init_sqlite(self, db_path: str):
        """Initialize SQLite database connection and tables."""
        self._conn = sqlite3.connect(db_path)
        cursor = self._conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trajectories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trajectory_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                model TEXT,
                latency_ms INTEGER,
                token_usage_prompt INTEGER,
                token_usage_completion INTEGER,
                token_usage_total INTEGER,
                success INTEGER NOT NULL,
                final_answer TEXT,
                error TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trajectory_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                input TEXT NOT NULL,
                output TEXT NOT NULL,
                success INTEGER NOT NULL,
                error TEXT,
                execution_time_ms INTEGER,
                timestamp TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trajectory_summary (
                trajectory_id TEXT PRIMARY KEY,
                total_tool_calls INTEGER,
                successful_tool_calls INTEGER,
                failed_tool_calls INTEGER,
                total_execution_time_ms INTEGER,
                reasoning_summary TEXT
            )
        """
        )

        self._conn.commit()

    def record_trajectory(
        self,
        trajectory_id: str,
        task: Task,
        model: str,
        steps: List[Dict[str, Any]],
        final_answer: str,
        success: bool,
        error: Optional[str] = None,
        latency_ms: Optional[int] = None,
        token_usage: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Record a complete trajectory.

        Args:
            trajectory_id: Unique identifier for this trajectory.
            task: The task that was executed.
            model: Model used for execution.
            steps: List of execution steps.
            final_answer: Final answer from execution.
            success: Whether execution succeeded.
            error: Error message if execution failed.
            latency_ms: Total execution time in milliseconds.
            token_usage: Token usage metadata.

        Returns:
            Recorded trajectory data.
        """
        now = datetime.utcnow()
        tool_calls = steps

        trajectory = {
            "trajectory_id": trajectory_id,
            "task_id": task.task_id,
            "created_at": now.isoformat(),
            "completed_at": None if success and error is None else now.isoformat(),
            "model": model,
            "latency_ms": latency_ms,
            "token_usage_prompt": token_usage.get("prompt_tokens") if token_usage else None,
            "token_usage_completion": token_usage.get("completion_tokens") if token_usage else None,
            "token_usage_total": token_usage.get("total_tokens") if token_usage else None,
            "success": 1 if success else 0,
            "final_answer": final_answer,
            "error": error,
            "steps": tool_calls,
        }

        self.trajectories.append(trajectory)

        if self.storage_type == "sqlite" and self._conn:
            self._persist_trajectory(trajectory_id, trajectory)

        return trajectory

    def _persist_trajectory(self, trajectory_id: str, trajectory: Dict[str, Any]):
        """Persist trajectory to SQLite database."""
        cursor = self._conn.cursor()

        # Record trajectory header
        cursor.execute(
            """
            INSERT INTO trajectories
            (trajectory_id, task_id, created_at, completed_at, model, latency_ms,
             token_usage_prompt, token_usage_completion, token_usage_total, success,
             final_answer, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                trajectory["trajectory_id"],
                trajectory["task_id"],
                trajectory["created_at"],
                trajectory["completed_at"],
                trajectory["model"],
                trajectory["latency_ms"],
                trajectory["token_usage_prompt"],
                trajectory["token_usage_completion"],
                trajectory["token_usage_total"],
                trajectory["success"],
                trajectory["final_answer"],
                trajectory["error"],
            ),
        )

        # Record tool calls
        step_offset = trajectory_id.count("-") + 1
        for i, step in enumerate(trajectory["steps"], start=1):
            step_num = step_offset + i

            if step.get("type") == "tool":
                cursor.execute(
                    """
                    INSERT INTO tool_calls
                    (trajectory_id, tool_name, input, output, success, error,
                     execution_time_ms, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        trajectory_id,
                        step.get("tool_name"),
                        json.dumps(step.get("input", {})),
                        json.dumps(step.get("output", {})),
                        1 if step.get("status") == "success" else 0,
                        step.get("error"),
                        step.get("execution_time_ms"),
                        datetime.utcnow().isoformat(),
                    ),
                )

        # Record summary
        successful_steps = sum(1 for step in trajectory["steps"] if step.get("status") == "success")
        total_time = sum(step.get("execution_time_ms", 0) for step in trajectory["steps"])

        cursor.execute(
            """
            INSERT INTO trajectory_summary
            (trajectory_id, total_tool_calls, successful_tool_calls, failed_tool_calls,
             total_execution_time_ms, reasoning_summary)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                trajectory_id,
                len(trajectory["steps"]),
                successful_steps,
                len(trajectory["steps"]) - successful_steps,
                total_time,
                "No reasoning summary available",
            ),
        )

        self._conn.commit()

    def record_trajectory_initialization(
        self,
        task_id: str,
        description: str,
        available_tools: List[str],
        success_criteria: str,
        trajectory_id: Optional[str] = None,
    ) -> str:
        """
        Initialize a trajectory recording.

        Args:
            task_id: Task identifier.
            description: Task description.
            available_tools: List of available tool names.
            success_criteria: Criteria for task success.
            trajectory_id: Unique trajectory identifier. Generated if omitted.

        Returns:
            The trajectory ID used (generated or provided).
        """
        if trajectory_id is None:
            trajectory_id = generate_trajectory_id()

        if self.storage_type == "memory":
            self.trajectories.append({
                "trajectory_id": trajectory_id,
                "task_id": task_id,
                "description": description,
                "available_tools": available_tools,
                "success_criteria": success_criteria,
                "tool_calls": [],
                "tool_results": [],
                "final_answer": None,
                "summary": None,
            })

        return trajectory_id

    def _ensure_trajectory(self, trajectory_id: str) -> None:
        """Ensure a trajectory entry exists for the given ID.

        Creates a bare entry if no trajectory with this ID exists yet.
        This supports workflows where tool calls are recorded before
        explicit initialization.
        """
        if self.storage_type == "memory":
            existing = next(
                (t for t in self.trajectories if t["trajectory_id"] == trajectory_id),
                None,
            )
            if not existing:
                self.trajectories.append({
                    "trajectory_id": trajectory_id,
                    "task_id": None,
                    "description": None,
                    "available_tools": [],
                    "success_criteria": None,
                    "tool_calls": [],
                    "tool_results": [],
                    "final_answer": None,
                    "summary": None,
                })

    def record_tool_call(
        self,
        trajectory_id: str,
        tool_call: "ToolCall",
    ) -> None:
        """
        Record a tool call.

        Args:
            trajectory_id: Trajectory identifier.
            tool_call: Tool call to record.
        """
        if self.storage_type == "memory":
            self._ensure_trajectory(trajectory_id)
            trajectory = next(
                (t for t in self.trajectories if t["trajectory_id"] == trajectory_id),
                None,
            )
            if trajectory:
                trajectory["tool_calls"].append(tool_call.__dict__)

    def record_tool_result(
        self,
        trajectory_id: str,
        tool_result: "ToolResult",
    ) -> None:
        """
        Record a tool result.

        Args:
            trajectory_id: Trajectory identifier.
            tool_result: Tool result to record.
        """
        if self.storage_type == "memory":
            self._ensure_trajectory(trajectory_id)
            trajectory = next(
                (t for t in self.trajectories if t["trajectory_id"] == trajectory_id),
                None,
            )
            if trajectory:
                trajectory["tool_results"].append(tool_result.__dict__)

    def record_final_answer(self, trajectory_id: str, answer: str) -> None:
        """
        Record the final answer.

        Args:
            trajectory_id: Trajectory identifier.
            answer: Final answer string.
        """
        if self.storage_type == "memory":
            self._ensure_trajectory(trajectory_id)
            trajectory = next(
                (t for t in self.trajectories if t["trajectory_id"] == trajectory_id),
                None,
            )
            if trajectory:
                trajectory["final_answer"] = answer

    def record_trajectory_summary(
        self,
        trajectory_id: str,
        summary: Dict[str, Any],
    ) -> None:
        """
        Record trajectory summary.

        Args:
            trajectory_id: Trajectory identifier.
            summary: Summary dictionary.
        """
        if self.storage_type == "memory":
            self._ensure_trajectory(trajectory_id)
            trajectory = next(
                (t for t in self.trajectories if t["trajectory_id"] == trajectory_id),
                None,
            )
            if trajectory:
                trajectory["summary"] = summary

    def get_steps(self, trajectory_id: str) -> List[Dict[str, Any]]:
        """
        Get all steps from a trajectory.

        Args:
            trajectory_id: Trajectory identifier.

        Returns:
            List of steps.
        """
        if self.storage_type == "memory":
            trajectory = next(
                (t for t in self.trajectories if t["trajectory_id"] == trajectory_id),
                None,
            )
            if trajectory:
                return trajectory["tool_calls"]

        return []

    def record_step(self, trajectory_id: str, step: Dict[str, Any]) -> None:
        """
        Record a step in the trajectory.

        Args:
            trajectory_id: Trajectory identifier.
            step: Step dictionary.
        """
        if self.storage_type == "memory":
            trajectory = next(
                (t for t in self.trajectories if t["trajectory_id"] == trajectory_id),
                None,
            )
            if trajectory:
                trajectory["tool_calls"].append(step)

    def get_trajectories(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all trajectories.

        Returns:
            Dictionary mapping trajectory IDs to trajectory data.
        """
        if self.storage_type == "memory":
            return {
                trajectory["trajectory_id"]: trajectory
                for trajectory in self.trajectories
            }

        elif self.storage_type == "sqlite" and self._conn:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM trajectories")
            rows = cursor.fetchall()

            trajectories = {}
            for row in rows:
                trajectories[row[1]] = {
                    "trajectory_id": row[1],
                    "task_id": row[2],
                    "created_at": row[3],
                    "completed_at": row[4],
                    "model": row[5],
                    "latency_ms": row[6],
                    "token_usage_prompt": row[7],
                    "token_usage_completion": row[8],
                    "token_usage_total": row[9],
                    "success": bool(row[10]),
                    "final_answer": row[11],
                    "error": row[12],
                }

            return trajectories

        return {}

    def get_trajectory(self, trajectory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a trajectory by ID.

        Args:
            trajectory_id: Trajectory identifier.

        Returns:
            Trajectory data or None if not found.
        """
        if self.storage_type == "memory":
            return next((t for t in self.trajectories if t["trajectory_id"] == trajectory_id), None)

        elif self.storage_type == "sqlite" and self._conn:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT * FROM trajectories WHERE trajectory_id = ?
            """,
                (trajectory_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "trajectory_id": row[1],
                    "task_id": row[2],
                    "created_at": row[3],
                    "completed_at": row[4],
                    "model": row[5],
                    "latency_ms": row[6],
                    "token_usage_prompt": row[7],
                    "token_usage_completion": row[8],
                    "token_usage_total": row[9],
                    "success": bool(row[10]),
                    "final_answer": row[11],
                    "error": row[12],
                }

        return None

    def list_trajectories(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all trajectories, optionally filtered by task.

        Args:
            task_id: Optional task ID to filter by.

        Returns:
            List of trajectories.
        """
        if task_id:
            return [t for t in self.trajectories if t.get("task_id") == task_id]

        return self.trajectories

    def clear(self):
        """Clear all recorded trajectories."""
        self.trajectories.clear()
        if self.storage_type == "sqlite" and self._conn:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM trajectories")
            cursor.execute("DELETE FROM tool_calls")
            cursor.execute("DELETE FROM trajectory_summary")
            self._conn.commit()

    def clear_trajectories(self):
        """Clear all recorded trajectories (alias for clear)."""
        self.clear()

    def generate_trajectory_id(self) -> str:
        """Instance method to generate a unique trajectory ID.

        Returns:
            Unique trajectory identifier.
        """
        return generate_trajectory_id()


def generate_trajectory_id() -> str:
    """
    Generate a unique trajectory ID.

    Returns:
        Unique trajectory identifier.
    """
    unique = uuid.uuid4().hex[:12]
    return f"trajectory-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{unique}"
