"""Runtime Execution Context — mutable container for one engineering execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from models.fact_store import FactStore
from models.goal_store import GoalStore


class ExecutionContextStatus(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    AWAITING_INPUT = "awaiting_input"
    READY = "ready"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    INVALIDATED = "invalidated"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    IN_PROGRESS = "in_progress"


def task_status_to_context_status(status: Any) -> ExecutionContextStatus:
    from models.task import TaskStatus

    mapping = {
        TaskStatus.ACTIVE: ExecutionContextStatus.ACTIVE,
        TaskStatus.AWAITING_INPUT: ExecutionContextStatus.AWAITING_INPUT,
        TaskStatus.PAUSED: ExecutionContextStatus.PAUSED,
        TaskStatus.COMPLETED: ExecutionContextStatus.COMPLETED,
        TaskStatus.INVALIDATED: ExecutionContextStatus.INVALIDATED,
        TaskStatus.IN_PROGRESS: ExecutionContextStatus.IN_PROGRESS,
    }
    return mapping.get(status, ExecutionContextStatus.ACTIVE)


def context_status_to_task_status(status: ExecutionContextStatus) -> Any:
    from models.task import TaskStatus

    mapping = {
        ExecutionContextStatus.NEW: TaskStatus.ACTIVE,
        ExecutionContextStatus.ACTIVE: TaskStatus.ACTIVE,
        ExecutionContextStatus.AWAITING_INPUT: TaskStatus.AWAITING_INPUT,
        ExecutionContextStatus.READY: TaskStatus.ACTIVE,
        ExecutionContextStatus.EXECUTING: TaskStatus.IN_PROGRESS,
        ExecutionContextStatus.BLOCKED: TaskStatus.AWAITING_INPUT,
        ExecutionContextStatus.COMPLETED: TaskStatus.COMPLETED,
        ExecutionContextStatus.INVALIDATED: TaskStatus.INVALIDATED,
        ExecutionContextStatus.FAILED: TaskStatus.INVALIDATED,
        ExecutionContextStatus.PAUSED: TaskStatus.PAUSED,
        ExecutionContextStatus.CANCELLED: TaskStatus.INVALIDATED,
        ExecutionContextStatus.IN_PROGRESS: TaskStatus.IN_PROGRESS,
    }
    return mapping.get(status, TaskStatus.ACTIVE)


@dataclass
class InputConflict:
    previous_calculation_invalid: bool
    reason: str
    input_id: str | None = None
    previous_value: Any | None = None
    new_value: Any | None = None


@dataclass
class ExecutionState:
    current_phase: str = "ready"
    blocked_by: list[str] = field(default_factory=list)
    ready_goals: list[str] = field(default_factory=list)
    blocked_goals: list[str] = field(default_factory=list)
    completed_goals: list[str] = field(default_factory=list)


@dataclass
class FactsIndex:
    active: list[str] = field(default_factory=list)
    superseded: list[str] = field(default_factory=list)
    conflicting: list[str] = field(default_factory=list)


@dataclass
class Decision:
    id: str
    parameter: str
    selected_value: Any
    source: str
    timestamp: str
    reason: str | None = None


@dataclass
class Assumption:
    id: str
    parameter: str
    value: Any
    confirmed_by: str
    timestamp: str
    affects_expansion: bool = False


@dataclass
class ExecutionValidation:
    status: str = "incomplete"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    overrides: list[str] = field(default_factory=list)


@dataclass
class ExecutionTraceRef:
    events: list[str] = field(default_factory=list)


@dataclass
class ExecutionMetadata:
    created: str | None = None
    modified: str | None = None
    version: int = 1


@dataclass
class ExecutionContext:
    id: str
    task_id: str
    type: str = "execution_context"
    workflow_id: str | None = None
    project_id: str | None = None
    status: ExecutionContextStatus = ExecutionContextStatus.ACTIVE
    authority_context_id: str | None = None
    active_goals: list[str] = field(default_factory=list)
    fact_store: FactStore = field(default_factory=FactStore)
    goal_store: GoalStore = field(default_factory=GoalStore)
    facts_index: FactsIndex = field(default_factory=FactsIndex)
    state: ExecutionState = field(default_factory=ExecutionState)
    decisions: list[Decision] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    validation: ExecutionValidation = field(default_factory=ExecutionValidation)
    execution_trace: ExecutionTraceRef = field(default_factory=ExecutionTraceRef)
    warnings: list[str] = field(default_factory=list)
    conflicts: list[InputConflict] = field(default_factory=list)
    metadata: ExecutionMetadata = field(default_factory=ExecutionMetadata)


def new_execution_context_id() -> str:
    return f"EXEC-{uuid4().hex[:12]}"


def new_decision_id() -> str:
    return f"DECISION-{uuid4().hex[:12]}"


def new_assumption_id() -> str:
    return f"ASSUMPTION-{uuid4().hex[:12]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def execution_context_for_task(
    task_id: str,
    *,
    workflow_id: str | None = None,
    project_id: str | None = None,
    status: ExecutionContextStatus | Any = ExecutionContextStatus.ACTIVE,
    context_id: str | None = None,
) -> ExecutionContext:
    if not isinstance(status, ExecutionContextStatus):
        status = task_status_to_context_status(status)
    now = _utc_now_iso()
    return ExecutionContext(
        id=context_id or new_execution_context_id(),
        task_id=task_id,
        workflow_id=workflow_id,
        project_id=project_id,
        status=status,
        metadata=ExecutionMetadata(created=now, modified=now, version=1),
    )


def execution_context_to_dict(ctx: ExecutionContext) -> dict[str, Any]:
    from dataclasses import asdict

    payload = asdict(ctx)
    payload["status"] = ctx.status.value
    return payload


def _decision_from_dict(data: dict[str, Any]) -> Decision:
    return Decision(
        id=str(data["id"]),
        parameter=str(data["parameter"]),
        selected_value=data.get("selected_value"),
        source=str(data.get("source", "user_input")),
        timestamp=str(data.get("timestamp", "")),
        reason=data.get("reason"),
    )


def _assumption_from_dict(data: dict[str, Any]) -> Assumption:
    return Assumption(
        id=str(data["id"]),
        parameter=str(data["parameter"]),
        value=data.get("value"),
        confirmed_by=str(data.get("confirmed_by", "user")),
        timestamp=str(data.get("timestamp", "")),
        affects_expansion=bool(data.get("affects_expansion", False)),
    )


def execution_context_from_dict(data: dict[str, Any]) -> ExecutionContext:
    status_raw = data.get("status", ExecutionContextStatus.ACTIVE.value)
    if isinstance(status_raw, ExecutionContextStatus):
        status = status_raw
    else:
        status = ExecutionContextStatus(str(status_raw))

    state_data = data.get("state") or {}
    facts_index_data = data.get("facts_index") or data.get("facts") or {}
    validation_data = data.get("validation") or {}
    trace_data = data.get("execution_trace") or {}
    meta_data = data.get("metadata") or {}

    conflicts = [
        InputConflict(**item) if isinstance(item, dict) else item
        for item in (data.get("conflicts") or [])
    ]

    return ExecutionContext(
        id=str(data.get("id") or new_execution_context_id()),
        type=str(data.get("type", "execution_context")),
        task_id=str(data["task_id"]),
        workflow_id=data.get("workflow_id"),
        project_id=data.get("project_id"),
        status=status,
        authority_context_id=data.get("authority_context_id") or data.get("authority_context"),
        active_goals=list(data.get("active_goals") or []),
        fact_store=FactStore.from_dict(data.get("fact_store")),
        goal_store=GoalStore.from_dict(data.get("goal_store")),
        facts_index=FactsIndex(
            active=list(facts_index_data.get("active") or []),
            superseded=list(facts_index_data.get("superseded") or []),
            conflicting=list(facts_index_data.get("conflicting") or []),
        ),
        state=ExecutionState(
            current_phase=str(state_data.get("current_phase") or "ready"),
            blocked_by=list(state_data.get("blocked_by") or []),
            ready_goals=list(state_data.get("ready_goals") or []),
            blocked_goals=list(state_data.get("blocked_goals") or []),
            completed_goals=list(state_data.get("completed_goals") or []),
        ),
        decisions=[_decision_from_dict(item) for item in (data.get("decisions") or [])],
        assumptions=[_assumption_from_dict(item) for item in (data.get("assumptions") or [])],
        validation=ExecutionValidation(
            status=str(validation_data.get("status", "incomplete")),
            warnings=list(validation_data.get("warnings") or []),
            errors=list(validation_data.get("errors") or []),
            overrides=list(validation_data.get("overrides") or []),
        ),
        execution_trace=ExecutionTraceRef(events=list(trace_data.get("events") or [])),
        warnings=list(data.get("warnings") or []),
        conflicts=conflicts,
        metadata=ExecutionMetadata(
            created=meta_data.get("created"),
            modified=meta_data.get("modified"),
            version=int(meta_data.get("version", 1)),
        ),
    )
