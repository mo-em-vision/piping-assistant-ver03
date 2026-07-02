"""Execution plan and runtime result data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .graph import GraphEdge, GraphVersion
from .fact import Fact


class NodeExecutionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ERROR = "error"
    AWAITING_INPUT = "awaiting_input"
    SKIPPED = "skipped"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ERROR = "error"
    AWAITING_INPUT = "awaiting_input"
    PARTIAL = "partial"


@dataclass
class ExecutionConfiguration:
    """Optional execution settings passed with a plan."""

    precision: str = "full"
    record_intermediates: bool = True


@dataclass
class ExecutionPlan:
    """Deterministic execution plan produced by the Graph Engine."""

    task_id: str
    root: str
    nodes: tuple[str, ...]
    execution_order: tuple[str, ...]
    inputs: dict[str, Fact] = field(default_factory=dict)
    dependencies: tuple[GraphEdge, ...] = ()
    graph_version: GraphVersion | None = None
    configuration: ExecutionConfiguration = field(default_factory=ExecutionConfiguration)
    skipped_nodes: tuple[dict[str, str | bool], ...] = ()


@dataclass
class NodeExecutionResult:
    """Result of executing a single node."""

    node_id: str
    status: NodeExecutionStatus
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_id: str | None = None
    node_version: str | None = None
    formula_version: str | None = None
    input_hash: str | None = None
    result_hash: str | None = None


@dataclass
class ExecutionResult:
    """Full result of executing an ExecutionPlan."""

    plan: ExecutionPlan
    node_results: list[NodeExecutionResult] = field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING
    events: list[dict[str, Any]] = field(default_factory=list)
    lifecycle_events: list[dict[str, Any]] = field(default_factory=list)
