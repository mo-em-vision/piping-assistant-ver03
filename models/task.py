"""Task state and session memory data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .input import EngineeringInput


class TaskStatus(str, Enum):
    ACTIVE = "active"
    AWAITING_INPUT = "awaiting_input"
    PAUSED = "paused"
    COMPLETED = "completed"
    INVALIDATED = "invalidated"
    IN_PROGRESS = "in_progress"


@dataclass
class InputConflict:
    previous_calculation_invalid: bool
    reason: str
    input_id: str | None = None
    previous_value: Any | None = None
    new_value: Any | None = None


@dataclass
class Task:
    task_id: str
    status: TaskStatus
    active_nodes: list[str] = field(default_factory=list)
    inputs: dict[str, EngineeringInput] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    conflicts: list[InputConflict] = field(default_factory=list)
