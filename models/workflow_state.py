"""Serializable runtime workflow state.

The knowledge graph defines engineering knowledge. This model holds the
mutable execution state for one task.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


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
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    history: tuple[dict[str, Any], ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1"
