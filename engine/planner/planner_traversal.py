"""Planner graph traversal state for engineering-plan debugging."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.planner.pipe_wall_plan import PIPE_WALL_WORKFLOW, req_id
from engine.reference.parameter_keys import load_parameter_node_metadata, param_node_id_for_input
from models.engineering_plan import (
    EngineeringPlan,
    InputStrategy,
    PlanGraph,
    PlanRequirement,
    PlannerTraversalState,
    TraversalActiveNode,
    TraversalBranchDecision,
    TraversalCandidateNode,
    TraversalEvent,
    TraversalExpandedNode,
    TraversalPendingNode,
)

PIPE_WALL_WORKFLOW_NODE = "WF-PIPE-WALL-THICKNESS"

_PRESSURE_BRANCH_CANDIDATES = ("304.1.2-a", "304.1.3")
_PRESSURE_BRANCH_BY_VALUE = {
    "internal_pressure": "304.1.2-a",
    "external_pressure": "304.1.3",
}

_PARAGRAPH_TITLES: dict[str, str] = {
    "304.1.2-a": "Straight Pipe Under Internal Pressure",
    "304.1.3": "Straight Pipe Under External Pressure",
}

_WORKFLOW_TITLES: dict[str, str] = {
    PIPE_WALL_WORKFLOW_NODE: "Pipe Wall Thickness Workflow",
}

_ACTIVE_REASONS: dict[str, str] = {
    "straight_pipe_section": (
        "Required to confirm whether straight pipe thickness rules apply."
    ),
    "pressure_loading": "Select internal or external pressure to determine the design path.",
}

_PENDING_REASONS: dict[str, str] = {
    "pressure_loading": (
        "Pressure branch cannot be selected until expansion assumptions are resolved."
    ),
    "304.1.2-a": (
        "Internal pressure branch is conditional until pressure loading is selected."
    ),
    "304.1.3": (
        "External pressure branch is conditional until pressure loading is selected."
    ),
}

_EARLY_PHASES = frozenset(
    {
        "expansion_assumptions",
        "path_decisions",
        "parameter_gathering",
    }
)


def _req_for_field(requirements: dict[str, PlanRequirement], field: str) -> PlanRequirement | None:
    return requirements.get(req_id(field))


def _field_resolved(requirements: dict[str, PlanRequirement], field: str) -> bool:
    req = _req_for_field(requirements, field)
    return req is not None and req.status == "resolved"


def _node_title(node_id: str, node_type: str) -> str | None:
    if node_type == "parameter":
        meta = load_parameter_node_metadata(node_id)
        if meta:
            return str(meta.get("name") or meta.get("title") or node_id)
    if node_type == "workflow":
        return _WORKFLOW_TITLES.get(node_id, node_id)
    if node_type == "paragraph":
        return _PARAGRAPH_TITLES.get(node_id, node_id)
    return node_id


def _node_type_for_id(node_id: str) -> str:
    if node_id.startswith("PARAM-"):
        return "parameter"
    if node_id.startswith("WF-"):
        return "workflow"
    return "paragraph"


def _pressure_value(
    *,
    path_decision: dict[str, str] | None,
    existing_inputs: dict[str, Any],
) -> str | None:
    if path_decision and path_decision.get("field") == "pressure_loading":
        value = path_decision.get("value")
        if value:
            return str(value)
    return field_value("pressure_loading", existing_inputs)


def _selected_branch_node(
    *,
    path_decision: dict[str, str] | None,
    pressure_value: str | None,
) -> str | None:
    if path_decision and path_decision.get("selected_node"):
        return str(path_decision["selected_node"])
    if pressure_value:
        return _PRESSURE_BRANCH_BY_VALUE.get(pressure_value)
    return None


def _build_active_node(
    *,
    requirements: dict[str, PlanRequirement],
    input_strategy: InputStrategy | None,
) -> tuple[str | None, TraversalActiveNode | None]:
    if input_strategy is None or not input_strategy.next_fields:
        return None, None

    field = input_strategy.next_fields[0]
    node_id = param_node_id_for_input(field)
    phase = input_strategy.current_phase
    req = _req_for_field(requirements, field)
    reason = _ACTIVE_REASONS.get(field)
    if not reason and req and req.question_spec:
        reason = f"Next required input for {phase.replace('_', ' ')}."
    if not reason:
        reason = f"Active traversal node for phase {phase}."

    # Coefficient/equation phases must not activate lookup PARAM nodes before early phases complete.
    if phase not in _EARLY_PHASES and req and req.requirement_class == "table_lookup":
        return None, None

    active = TraversalActiveNode(
        node_id=node_id,
        node_type="parameter",
        title=_node_title(node_id, "parameter"),
        phase=phase,
        reason=reason,
    )
    return node_id, active


def _append_pending(
    pending: list[TraversalPendingNode],
    *,
    node_id: str,
    waiting_on: list[str],
    phase: str,
    reason: str,
    seen: set[str],
) -> None:
    if node_id in seen:
        return
    seen.add(node_id)
    node_type = _node_type_for_id(node_id)
    pending.append(
        TraversalPendingNode(
            node_id=node_id,
            node_type=node_type,
            title=_node_title(node_id, node_type),
            phase=phase,
            waiting_on=list(waiting_on),
            reason=reason,
        )
    )


def _build_pending_nodes(
    *,
    requirements: dict[str, PlanRequirement],
    active_node_id: str | None,
    straight_resolved: bool,
    pressure_resolved: bool,
    pressure_value: str | None,
) -> list[TraversalPendingNode]:
    pending: list[TraversalPendingNode] = []
    seen: set[str] = set()
    straight_param = param_node_id_for_input("straight_pipe_section")
    pressure_param = param_node_id_for_input("pressure_loading")

    if not straight_resolved and pressure_param != active_node_id:
        _append_pending(
            pending,
            node_id=pressure_param,
            waiting_on=[straight_param],
            phase="path_decisions",
            reason=_PENDING_REASONS["pressure_loading"],
            seen=seen,
        )

    if not pressure_resolved:
        internal_branch = _PRESSURE_BRANCH_BY_VALUE["internal_pressure"]
        if internal_branch != active_node_id:
            _append_pending(
                pending,
                node_id=internal_branch,
                waiting_on=[pressure_param],
                phase="parameter_gathering",
                reason=_PENDING_REASONS[internal_branch],
                seen=seen,
            )
        external_branch = _PRESSURE_BRANCH_BY_VALUE["external_pressure"]
        if pressure_value == "external_pressure" and external_branch != active_node_id:
            _append_pending(
                pending,
                node_id=external_branch,
                waiting_on=[pressure_param],
                phase="parameter_gathering",
                reason=_PENDING_REASONS[external_branch],
                seen=seen,
            )

    return pending


def _build_expanded_nodes(
    *,
    requirements: dict[str, PlanRequirement],
    graph: PlanGraph,
    workflow_id: str,
) -> list[TraversalExpandedNode]:
    if workflow_id.replace("-", "_") not in {
        PIPE_WALL_WORKFLOW,
        "pipe_wall_thickness_design",
    }:
        return []

    gate_req_ids = [req_id("straight_pipe_section"), req_id("pressure_loading")]
    expanded: list[TraversalExpandedNode] = [
        TraversalExpandedNode(
            node_id=PIPE_WALL_WORKFLOW_NODE,
            node_type="workflow",
            title=_node_title(PIPE_WALL_WORKFLOW_NODE, "workflow"),
            expanded_at_order=1,
            produced_requirements=[rid for rid in gate_req_ids if rid in requirements],
            produced_edges=[],
        )
    ]

    order = 2
    skip = {PIPE_WALL_WORKFLOW_NODE}
    for node_id in graph.expanded_node_ids:
        if node_id in skip:
            continue
        skip.add(node_id)
        node_type = _node_type_for_id(node_id)
        expanded.append(
            TraversalExpandedNode(
                node_id=node_id,
                node_type=node_type,
                title=_node_title(node_id, node_type),
                expanded_at_order=order,
                produced_requirements=[],
                produced_edges=[],
            )
        )
        order += 1

    return expanded


def _build_candidate_next_nodes(
    *,
    active_node_id: str | None,
    straight_resolved: bool,
    pressure_resolved: bool,
) -> list[TraversalCandidateNode]:
    candidates: list[TraversalCandidateNode] = []
    if active_node_id is None:
        return candidates

    straight_param = param_node_id_for_input("straight_pipe_section")
    pressure_param = param_node_id_for_input("pressure_loading")

    if active_node_id == straight_param and not straight_resolved:
        candidates.append(
            TraversalCandidateNode(
                node_id=pressure_param,
                node_type="parameter",
                title=_node_title(pressure_param, "parameter"),
                reason="Next path decision after straight pipe section is confirmed.",
            )
        )
    elif active_node_id == pressure_param and not pressure_resolved:
        for paragraph_id in _PRESSURE_BRANCH_CANDIDATES:
            candidates.append(
                TraversalCandidateNode(
                    node_id=paragraph_id,
                    node_type="paragraph",
                    title=_node_title(paragraph_id, "paragraph"),
                    reason="Candidate branch paragraph for selected pressure loading.",
                )
            )
    return candidates


def _build_branch_decisions(
    *,
    path_decision: dict[str, str] | None,
    pressure_value: str | None,
    selected_node: str | None,
) -> list[TraversalBranchDecision]:
    status = "resolved" if pressure_value else "unresolved"
    return [
        TraversalBranchDecision(
            field="pressure_loading",
            value=pressure_value,
            selected_node=selected_node,
            candidate_nodes=list(_PRESSURE_BRANCH_CANDIDATES),
            status=status,
        )
    ]


def _build_traversal_events(
    *,
    expanded_nodes: list[TraversalExpandedNode],
    active_node: TraversalActiveNode | None,
    branch_decisions: list[TraversalBranchDecision],
    pending_nodes: list[TraversalPendingNode],
) -> list[TraversalEvent]:
    events: list[TraversalEvent] = []
    order = 0

    for expanded in expanded_nodes:
        order += 1
        events.append(
            TraversalEvent(
                order=order,
                event_type="node_expanded",
                node_id=expanded.node_id,
                message=f"Expanded {expanded.node_type} node {expanded.node_id}.",
            )
        )
        for requirement_id in expanded.produced_requirements:
            order += 1
            events.append(
                TraversalEvent(
                    order=order,
                    event_type="requirement_created",
                    requirement_id=requirement_id,
                    message=f"Workflow expansion introduced requirement {requirement_id}.",
                )
            )

    for decision in branch_decisions:
        if decision.status == "unresolved":
            order += 1
            events.append(
                TraversalEvent(
                    order=order,
                    event_type="branch_decision_required",
                    message=f"Branch decision required for field {decision.field}.",
                )
            )
        else:
            order += 1
            events.append(
                TraversalEvent(
                    order=order,
                    event_type="branch_decision_resolved",
                    node_id=decision.selected_node,
                    message=(
                        f"Branch {decision.field} resolved to {decision.value!r} "
                        f"via node {decision.selected_node}."
                    ),
                )
            )

    if active_node is not None:
        order += 1
        events.append(
            TraversalEvent(
                order=order,
                event_type="node_selected",
                node_id=active_node.node_id,
                message=active_node.reason,
            )
        )

    for pending in pending_nodes:
        if pending.node_type == "paragraph" and "not applicable" in pending.reason.lower():
            order += 1
            events.append(
                TraversalEvent(
                    order=order,
                    event_type="node_marked_not_applicable",
                    node_id=pending.node_id,
                    message=pending.reason,
                )
            )
        elif pending.waiting_on:
            order += 1
            events.append(
                TraversalEvent(
                    order=order,
                    event_type="node_deferred",
                    node_id=pending.node_id,
                    message=pending.reason,
                )
            )

    return events


def build_planner_traversal_state(
    *,
    plan_id: str,
    workflow_id: str,
    requirements: dict[str, PlanRequirement],
    input_strategy: InputStrategy | None,
    graph: PlanGraph,
    path_decision: dict[str, str] | None = None,
    existing_inputs: dict[str, Any] | None = None,
) -> PlannerTraversalState | None:
    """Derive compact planner traversal snapshot for pipe wall workflows."""
    slug = workflow_id.replace("-", "_")
    if slug not in {PIPE_WALL_WORKFLOW, "pipe_wall_thickness_design"}:
        return None

    inputs = dict(existing_inputs or {})
    straight_resolved = _field_resolved(requirements, "straight_pipe_section")
    pressure_resolved = _field_resolved(requirements, "pressure_loading")
    pressure_value = _pressure_value(path_decision=path_decision, existing_inputs=inputs)
    selected_node = _selected_branch_node(
        path_decision=path_decision,
        pressure_value=pressure_value,
    )

    active_node_id, active_node = _build_active_node(
        requirements=requirements,
        input_strategy=input_strategy,
    )
    pending_nodes = _build_pending_nodes(
        requirements=requirements,
        active_node_id=active_node_id,
        straight_resolved=straight_resolved,
        pressure_resolved=pressure_resolved,
        pressure_value=pressure_value,
    )
    expanded_nodes = _build_expanded_nodes(
        requirements=requirements,
        graph=graph,
        workflow_id=workflow_id,
    )
    candidate_next_nodes = _build_candidate_next_nodes(
        active_node_id=active_node_id,
        straight_resolved=straight_resolved,
        pressure_resolved=pressure_resolved,
    )
    branch_decisions = _build_branch_decisions(
        path_decision=path_decision,
        pressure_value=pressure_value,
        selected_node=selected_node,
    )
    traversal_events = _build_traversal_events(
        expanded_nodes=expanded_nodes,
        active_node=active_node,
        branch_decisions=branch_decisions,
        pending_nodes=pending_nodes,
    )

    return PlannerTraversalState(
        traversal_id=f"TRAV-{plan_id}",
        current_active_node_id=active_node_id,
        current_active_node=active_node,
        pending_expansion_nodes=pending_nodes,
        expanded_nodes=expanded_nodes,
        candidate_next_nodes=candidate_next_nodes,
        branch_decisions=branch_decisions,
        traversal_events=traversal_events,
    )


def build_planner_traversal_state_from_plan(
    plan: EngineeringPlan,
    *,
    path_decision: dict[str, str] | None = None,
    existing_inputs: dict[str, Any] | None = None,
) -> PlannerTraversalState | None:
    return build_planner_traversal_state(
        plan_id=plan.plan_id,
        workflow_id=plan.workflow_id,
        requirements=plan.requirements,
        input_strategy=plan.input_strategy,
        graph=plan.graph,
        path_decision=path_decision,
        existing_inputs=existing_inputs,
    )


def build_traversal_summary(traversal: PlannerTraversalState) -> dict[str, Any]:
    return {
        "current_active_node_id": traversal.current_active_node_id,
        "current_active_node_title": (
            traversal.current_active_node.title if traversal.current_active_node else None
        ),
        "pending_expansion_count": len(traversal.pending_expansion_nodes),
        "expanded_count": len(traversal.expanded_nodes),
        "unresolved_branch_decisions": [
            decision.field
            for decision in traversal.branch_decisions
            if decision.status == "unresolved"
        ],
    }


def build_planner_traversal_inspector_view_from_plan(
    plan: EngineeringPlan,
    *,
    recent_event_limit: int = 20,
) -> dict[str, Any] | None:
    """Traversal inspector panel from canonical engineering plan."""
    if plan.traversal is None:
        return None
    return build_planner_traversal_inspector_view(
        plan.traversal,
        recent_event_limit=recent_event_limit,
    )


def build_planner_traversal_inspector_view(
    traversal: PlannerTraversalState,
    *,
    recent_event_limit: int = 20,
) -> dict[str, Any]:
    recent_events = traversal.traversal_events[-recent_event_limit:]
    return {
        "current_active_node": (
            traversal.current_active_node.to_dict() if traversal.current_active_node else None
        ),
        "pending_expansion_nodes": [
            item.to_dict() for item in traversal.pending_expansion_nodes
        ],
        "expanded_nodes": [item.to_dict() for item in traversal.expanded_nodes],
        "branch_decisions": [item.to_dict() for item in traversal.branch_decisions],
        "recent_events": [item.to_dict() for item in recent_events],
    }
