"""Normalized engineering plan produced by the planner layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


def new_plan_id() -> str:
    return f"PLAN-{uuid4().hex[:12]}"


@dataclass
class CalculationGoal:
    id: str
    key: str
    title: str
    goal_class: str = "calculation_goal"
    target_parameter: str = ""
    target_field: str = ""
    status: str = "blocked"
    blocked_by: list[str] = field(default_factory=list)
    provisional_blocked_by: list[str] = field(default_factory=list)
    required_outputs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActivationCondition:
    field: str
    operator: str
    value: str | list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RequirementAlternative:
    id: str
    label: str
    fields: list[str]
    resolves: str
    method: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuestionSpec:
    field: str
    label: str
    expected_value_class: str
    priority: int
    ask_policy: str
    reason_code: str | None = None
    allowed_units: list[str] | None = None
    options_source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PlanRequirement:
    id: str
    field: str
    parameter_node_id: str
    requirement_class: str
    status: str
    phase: str
    required_by: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    alternatives: list[RequirementAlternative] | None = None
    question_spec: QuestionSpec | None = None
    resolution: dict[str, Any] | None = None
    activation_condition: ActivationCondition | None = None
    activation_status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "field": self.field,
            "parameter_node_id": self.parameter_node_id,
            "requirement_class": self.requirement_class,
            "status": self.status,
            "phase": self.phase,
            "required_by": list(self.required_by),
            "depends_on": list(self.depends_on),
            "activation_status": self.activation_status,
        }
        if self.alternatives:
            payload["alternatives"] = [alt.to_dict() for alt in self.alternatives]
        if self.question_spec:
            payload["question_spec"] = self.question_spec.to_dict()
        if self.resolution:
            payload["resolution"] = dict(self.resolution)
        if self.activation_condition:
            payload["activation_condition"] = self.activation_condition.to_dict()
        return payload


@dataclass
class PlanDependency:
    from_id: str
    to_id: str
    type: str

    def to_dict(self) -> dict[str, Any]:
        return {"from": self.from_id, "to": self.to_id, "type": self.type}


@dataclass
class InputStrategy:
    mode: str
    current_phase: str
    next_fields: list[str] = field(default_factory=list)
    blocked_fields: list[str] = field(default_factory=list)
    resolved_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BranchDecision:
    field: str
    value: str
    selected_node: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlanGraph:
    selected_subgraph_node_ids: list[str] = field(default_factory=list)
    selected_branch_decisions: list[BranchDecision] = field(default_factory=list)
    expanded_node_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_subgraph_node_ids": list(self.selected_subgraph_node_ids),
            "selected_branch_decisions": [item.to_dict() for item in self.selected_branch_decisions],
            "expanded_node_ids": list(self.expanded_node_ids),
        }


@dataclass
class PlanPhase:
    id: str
    title: str
    order: int
    requirement_ids: list[str] = field(default_factory=list)
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TraversalActiveNode:
    node_id: str
    node_type: str
    reason: str
    title: str | None = None
    phase: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TraversalPendingNode:
    node_id: str
    node_type: str
    waiting_on: list[str]
    reason: str
    title: str | None = None
    phase: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TraversalExpandedNode:
    node_id: str
    node_type: str
    expanded_at_order: int
    produced_requirements: list[str] = field(default_factory=list)
    produced_edges: list[str] = field(default_factory=list)
    title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TraversalCandidateNode:
    node_id: str
    node_type: str
    reason: str
    title: str | None = None
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TraversalBranchDecision:
    field: str
    value: str | None
    selected_node: str | None
    candidate_nodes: list[str]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TraversalEvent:
    order: int
    event_type: str
    message: str
    node_id: str | None = None
    requirement_id: str | None = None
    edge_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PlannerTraversalState:
    traversal_id: str
    current_active_node_id: str | None = None
    current_active_node: TraversalActiveNode | None = None
    pending_expansion_nodes: list[TraversalPendingNode] = field(default_factory=list)
    expanded_nodes: list[TraversalExpandedNode] = field(default_factory=list)
    candidate_next_nodes: list[TraversalCandidateNode] = field(default_factory=list)
    branch_decisions: list[TraversalBranchDecision] = field(default_factory=list)
    traversal_events: list[TraversalEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "traversal_id": self.traversal_id,
            "current_active_node_id": self.current_active_node_id,
            "current_active_node": self.current_active_node.to_dict() if self.current_active_node else None,
            "pending_expansion_nodes": [item.to_dict() for item in self.pending_expansion_nodes],
            "expanded_nodes": [item.to_dict() for item in self.expanded_nodes],
            "candidate_next_nodes": [item.to_dict() for item in self.candidate_next_nodes],
            "branch_decisions": [item.to_dict() for item in self.branch_decisions],
            "traversal_events": [item.to_dict() for item in self.traversal_events],
        }


@dataclass
class EngineeringPlan:
    plan_id: str
    task_id: str
    workflow_id: str
    root_goal: CalculationGoal
    requirements: dict[str, PlanRequirement] = field(default_factory=dict)
    dependencies: list[PlanDependency] = field(default_factory=list)
    input_strategy: InputStrategy | None = None
    graph: PlanGraph = field(default_factory=PlanGraph)
    phases: list[PlanPhase] = field(default_factory=list)
    traversal: PlannerTraversalState | None = None
    debug: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "root_goal": self.root_goal.to_dict(),
            "requirements": {rid: req.to_dict() for rid, req in self.requirements.items()},
            "dependencies": [edge.to_dict() for edge in self.dependencies],
            "graph": self.graph.to_dict(),
            "phases": [phase.to_dict() for phase in self.phases],
        }
        if self.input_strategy:
            payload["input_strategy"] = self.input_strategy.to_dict()
        if self.traversal:
            payload["traversal"] = self.traversal.to_dict()
        if self.debug:
            payload["debug"] = dict(self.debug)
        return payload
