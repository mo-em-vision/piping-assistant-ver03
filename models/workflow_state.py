"""Serializable runtime workflow state.

The knowledge graph defines engineering knowledge. This model holds the
mutable execution state for one task.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from models.node_documentation import NodeDocumentation
from models.node_output import NodeOutput
from models.workflow_lifecycle import WorkflowLifecycleEvent


@dataclass(frozen=True)
class WorkflowParameter:
    """Structured runtime parameter (Phase 5)."""

    name: str
    value: Any
    dimension: str | None
    unit: str
    priority: int
    source: str
    status: str
    symbol: str | None = None
    param_node_id: str | None = None
    concept_id: str | None = None
    canonical_unit: str | None = None
    allowed_units: tuple[str, ...] = ()
    unit_id: str | None = None


@dataclass(frozen=True)
class WorkflowState:
    """Runtime data for a workflow execution, separate from graph nodes."""

    task_id: str
    workflow_id: str
    current_node: str | None = None
    visited_nodes: tuple[str, ...] = ()
    variable_values: dict[str, Any] = field(default_factory=dict)
    lookup_results: dict[str, Any] = field(default_factory=dict)
    selections: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, WorkflowParameter] = field(default_factory=dict)
    current_documentation: NodeDocumentation | None = None
    node_documentation: dict[str, NodeDocumentation] = field(default_factory=dict)
    execution_events: tuple[WorkflowLifecycleEvent, ...] = ()
    presentation_blocks: tuple[dict[str, Any], ...] = ()
    node_outputs: dict[str, tuple[NodeOutput, ...]] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    history: tuple[dict[str, Any], ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "2"
