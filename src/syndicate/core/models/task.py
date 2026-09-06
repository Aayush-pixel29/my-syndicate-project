"""Core models for Syndicate skill execution engine."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolInputSchema:
    """Schema for tool input validation and description."""
    type: str
    description: str
    required: List[str] = field(default_factory=list)
    enum: Optional[List[str]] = None
    properties: Optional[dict] = None


@dataclass
class ToolCall:
    """Record of a tool invocation."""
    tool_name: str
    input: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ToolResult:
    """Result from executing a tool."""
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Task:
    """Core task representation."""
    task_id: str
    description: str
    available_tool_names: List[str] = field(default_factory=list)
    success_criteria: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    final_answer: Optional[str] = None
    error: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    execution_history: List[Any] = field(default_factory=list)
