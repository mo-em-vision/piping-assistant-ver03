"""Data models for the developer inspection framework."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GraphEdgeRef:
    """A directed graph edge reference."""

    from_node: str
    to_node: str
    edge_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionTraceStep:
    """One step in the execution trace (stack-trace equivalent for the graph)."""

    step_index: int
    workflow_id: str
    node_id: str
    node_type: str
    incoming_edge: GraphEdgeRef | None
    outgoing_edge: GraphEdgeRef | None
    selection_reason: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    duration_ms: float | None
    status: str  # success | failed | skipped | awaiting_input
    timestamp: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.incoming_edge is not None:
            payload["incoming_edge"] = self.incoming_edge.to_dict()
        else:
            payload["incoming_edge"] = None
        if self.outgoing_edge is not None:
            payload["outgoing_edge"] = self.outgoing_edge.to_dict()
        else:
            payload["outgoing_edge"] = None
        return payload


@dataclass
class PlannerDecision:
    """Explanation for why a node was selected by the planner."""

    node_id: str
    why_selected: str
    trigger_dependency: str | None = None
    edge_followed: GraphEdgeRef | None = None
    rule_fired: str = ""
    rejected_candidates: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.edge_followed is not None:
            payload["edge_followed"] = self.edge_followed.to_dict()
        else:
            payload["edge_followed"] = None
        return payload


@dataclass
class ValueProvenanceRecord:
    """Provenance for a displayed value."""

    display_id: str
    display_value: str
    source_node: str
    source_property: str
    generated_by: str | None = None
    consumed_by: list[str] = field(default_factory=list)
    transformation_history: list[dict[str, Any]] = field(default_factory=list)
    missing: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReplayFrame:
    """One frame in an execution replay."""

    frame_index: int
    step_index: int | None
    active_node: str | None
    visited_nodes: list[str]
    pending_nodes: list[str]
    variables: dict[str, Any]
    outputs: dict[str, Any]
    planner_state: dict[str, Any]
    context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntegrityCheckResult:
    """Result of a single graph integrity check."""

    check_id: str
    name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
