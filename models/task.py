"""Task state and session memory data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from models.authority_context import AuthorityContext
from models.execution_context import (
    ExecutionContext,
    InputConflict,
    context_status_to_task_status,
    execution_context_for_task,
    task_status_to_context_status,
)
from .input import ParameterDescriptor


class TaskStatus(str, Enum):
    ACTIVE = "active"
    AWAITING_INPUT = "awaiting_input"
    PAUSED = "paused"
    COMPLETED = "completed"
    INVALIDATED = "invalidated"
    IN_PROGRESS = "in_progress"


@dataclass
class Task:
    task_id: str
    execution_context: ExecutionContext
    authority_context: AuthorityContext | None = None
    active_nodes: list[str] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    parameter_registry: dict[str, ParameterDescriptor] = field(default_factory=dict)
    payload_version: int = 5

    @property
    def status(self) -> TaskStatus:
        return context_status_to_task_status(self.execution_context.status)

    @status.setter
    def status(self, value: TaskStatus) -> None:
        self.execution_context.status = task_status_to_context_status(value)

    @property
    def fact_store(self):
        return self.execution_context.fact_store

    @property
    def goal_store(self):
        return self.execution_context.goal_store

    @property
    def warnings(self) -> list[str]:
        return self.execution_context.warnings

    @warnings.setter
    def warnings(self, value: list[str]) -> None:
        self.execution_context.warnings = value

    @property
    def conflicts(self) -> list[InputConflict]:
        return self.execution_context.conflicts

    @conflicts.setter
    def conflicts(self, value: list[InputConflict]) -> None:
        self.execution_context.conflicts = value


def new_task(
    task_id: str,
    *,
    status: TaskStatus = TaskStatus.ACTIVE,
    workflow_id: str | None = None,
    project_id: str | None = None,
    authority_context: AuthorityContext | None = None,
) -> Task:
    ctx = execution_context_for_task(
        task_id,
        workflow_id=workflow_id,
        project_id=project_id,
        status=status,
    )
    return Task(
        task_id=task_id,
        execution_context=ctx,
        authority_context=authority_context,
    )
