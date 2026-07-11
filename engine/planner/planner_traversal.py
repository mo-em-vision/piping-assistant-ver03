"""Planner graph traversal state for engineering-plan debugging."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import _field_from_param_ref, field_value
from engine.graph.graph_engine import normalize_root_id
from engine.graph.path_decision import _applies_when_matches_field
from engine.planner.plan_phases import strategy_field
from engine.reference.parameter_keys import (
    load_parameter_node_metadata,
    param_node_id_for_input,
)
from engine.reference.standards_reader import StandardsReader
from models.planning import NavigationPhase
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

_COEFFICIENT_PHASE = NavigationPhase.COEFFICIENT_RESOLUTION.value
_GATE_PHASES = frozenset({"expansion_assumptions", "path_decisions"})


def _graph_store(reader: StandardsReader | None):
    if reader is None:
        return None
    return reader.graph_store


def _canonical_workflow_node_id(reader: StandardsReader | None, workflow_id: str) -> str:
    store = _graph_store(reader)
    slug = normalize_root_id(workflow_id)
    if store is not None:
        resolved = store.resolve_node_id(slug)
        if resolved:
            return resolved
    return slug


def _infer_node_type(reader: StandardsReader | None, node_id: str) -> str:
    if node_id.startswith("PARAM-"):
        return "parameter"
    store = _graph_store(reader)
    if store is not None:
        node = store.get_node(node_id)
        if node is not None:
            node_type = str(node.node_type or "").strip()
            if node_type:
                return node_type
    if node_id.startswith("WF-") or node_id.startswith("B313-WF-"):
        return "workflow"
    if node_id.startswith("asme-b313-"):
        if "eq-" in node_id:
            return "equation"
        if "table-" in node_id:
            return "table"
        if "valrule-" in node_id:
            return "validation_rule"
    return "paragraph"


def _node_title(
    reader: StandardsReader | None,
    node_id: str,
    *,
    node_type: str,
    title: str | None = None,
) -> str:
    if title and str(title).strip():
        return str(title).strip()
    if node_type == "parameter" or node_id.startswith("PARAM-"):
        meta = load_parameter_node_metadata(node_id)
        if meta:
            name = str(meta.get("name") or meta.get("title") or "").strip()
            if name:
                return name
    store = _graph_store(reader)
    if store is not None:
        node = store.get_node(node_id)
        if node is not None:
            metadata = node.metadata if isinstance(node.metadata, dict) else {}
            presentation = metadata.get("presentation")
            if isinstance(presentation, dict):
                display_label = str(presentation.get("display_label") or "").strip()
                if display_label:
                    return display_label.title()
            for key in ("title", "name", "purpose"):
                value = str(metadata.get(key) or "").strip()
                if value:
                    return value
    return node_id


def _execution_order(preview: Any | None, graph: PlanGraph) -> list[str]:
    order = list(getattr(preview, "execution_order", ()) or [])
    if order:
        return order
    return list(graph.selected_subgraph_node_ids or graph.expanded_node_ids)


def _req_for_field(requirements: dict[str, PlanRequirement], field: str) -> PlanRequirement | None:
    for req in requirements.values():
        if strategy_field(req) == field or req.field == field:
            return req
    return None


def _is_askable_requirement(req: PlanRequirement) -> bool:
    if req.activation_status != "active":
        return False
    if req.status != "missing":
        return False
    if req.requirement_class not in {"user_input", "branch_decision"}:
        return False
    if req.question_spec is None:
        return False
    if req.question_spec.ask_policy in {"ask_later", "do_not_ask", "ask_if_needed"}:
        return False
    return True


def _is_askable_field(requirements: dict[str, PlanRequirement], field: str) -> bool:
    req = _req_for_field(requirements, field)
    return req is not None and _is_askable_requirement(req)


def _equation_dep_unresolved(
    req: PlanRequirement,
    requirements: dict[str, PlanRequirement],
) -> bool:
    for dep_id in req.depends_on:
        dep = requirements.get(dep_id)
        if dep is None:
            continue
        if dep.status not in {"resolved", "not_applicable"}:
            return True
    return False


def _gate_phases_clear(requirements: dict[str, PlanRequirement]) -> bool:
    for req in requirements.values():
        if req.phase not in _GATE_PHASES:
            continue
        if req.requirement_class not in {"user_input", "branch_decision"}:
            continue
        if req.activation_status != "active":
            continue
        if req.status not in {"resolved", "not_applicable"}:
            return False
    return True


def _default_branch_value(field: str) -> Any:
    param_node_id = param_node_id_for_input(field)
    meta = load_parameter_node_metadata(param_node_id)
    if not meta:
        return None
    nested = meta.get("metadata")
    options_source = nested if isinstance(nested, dict) else meta
    if "default_value" in options_source:
        return options_source.get("default_value")
    options = options_source.get("composer_options") or []
    if not options:
        return None
    first = options[0]
    if isinstance(first, dict):
        value = str(first.get("value") or "").strip()
        return value or None
    return None


def _paragraph_applies_to_field(metadata: dict[str, Any], field: str) -> bool:
    applicability = metadata.get("applicability") or {}
    if not isinstance(applicability, dict):
        return False
    for item in applicability.get("applies_when") or []:
        if not isinstance(item, dict):
            continue
        clause_field = _field_from_param_ref(str(item.get("parameter") or ""))
        if clause_field == field:
            return True
    return False


def _branch_candidates_for_field(
    reader: StandardsReader | None,
    execution_order: list[str],
    field: str,
) -> list[str]:
    store = _graph_store(reader)
    if store is None:
        return []
    candidates: list[str] = []
    seen: set[str] = set()

    def _maybe_add(node_id: str) -> None:
        if node_id in seen:
            return
        node = store.get_node(node_id)
        if node is None or node.node_type != "paragraph":
            return
        metadata = node.metadata if isinstance(node.metadata, dict) else {}
        if _paragraph_applies_to_field(metadata, field):
            seen.add(node_id)
            candidates.append(node_id)

    for node_id in execution_order:
        _maybe_add(node_id)
    for node in store.list_nodes(node_type="paragraph"):
        _maybe_add(node.node_id)
    return candidates


def _build_active_node(
    *,
    reader: StandardsReader | None,
    requirements: dict[str, PlanRequirement],
    input_strategy: InputStrategy | None,
) -> tuple[str | None, TraversalActiveNode | None]:
    if input_strategy is None or not input_strategy.next_fields:
        return None, None

    field = input_strategy.next_fields[0]
    if not _is_askable_field(requirements, field):
        return None, None

    node_id = param_node_id_for_input(field)
    phase = input_strategy.current_phase
    req = _req_for_field(requirements, field)
    reason = None
    if req and req.question_spec and req.question_spec.reason_code:
        reason = req.question_spec.reason_code
    elif req:
        reason = f"Next required input for {phase.replace('_', ' ')}."
    else:
        reason = f"Active traversal node for phase {phase}."

    if req and req.requirement_class == "table_lookup" and phase != _COEFFICIENT_PHASE:
        return None, None

    node_type = _infer_node_type(reader, node_id)
    active = TraversalActiveNode(
        node_id=node_id,
        node_type=node_type,
        title=_node_title(reader, node_id, node_type=node_type),
        phase=phase,
        reason=reason,
    )
    return node_id, active


def _append_pending(
    pending: list[TraversalPendingNode],
    *,
    reader: StandardsReader | None,
    node_id: str,
    waiting_on: list[str],
    phase: str,
    reason: str,
    seen: set[str],
    title: str | None = None,
) -> None:
    if node_id in seen:
        return
    seen.add(node_id)
    node_type = _infer_node_type(reader, node_id)
    pending.append(
        TraversalPendingNode(
            node_id=node_id,
            node_type=node_type,
            title=_node_title(reader, node_id, node_type=node_type, title=title),
            phase=phase,
            waiting_on=list(waiting_on),
            reason=reason,
        )
    )


def _infer_waiting_on_for_missing(
    req: PlanRequirement,
    requirements: dict[str, PlanRequirement],
    input_strategy: InputStrategy | None,
) -> list[str]:
    waiting_on = _waiting_on_param_nodes(req, requirements)
    if waiting_on:
        return waiting_on
    if input_strategy is None:
        return []
    field = strategy_field(req)
    if field not in input_strategy.blocked_fields:
        return []
    if not input_strategy.next_fields:
        return []
    return [param_node_id_for_input(input_strategy.next_fields[0])]


def _waiting_on_param_nodes(
    req: PlanRequirement,
    requirements: dict[str, PlanRequirement],
) -> list[str]:
    waiting_on: list[str] = []
    for dep_id in req.depends_on:
        dep = requirements.get(dep_id)
        if dep is None:
            continue
        if dep.status in {"resolved", "not_applicable"}:
            continue
        dep_node = dep.parameter_node_id or param_node_id_for_input(dep.field)
        if dep_node:
            waiting_on.append(dep_node)
    return waiting_on


def _build_branch_decisions(
    *,
    reader: StandardsReader | None,
    requirements: dict[str, PlanRequirement],
    path_decision: dict[str, str] | None,
    existing_inputs: dict[str, Any],
    execution_order: list[str],
) -> list[TraversalBranchDecision]:
    decisions: list[TraversalBranchDecision] = []
    seen_fields: set[str] = set()

    if path_decision and path_decision.get("field"):
        field = str(path_decision["field"])
        value = path_decision.get("value")
        value_text = str(value).strip() if value is not None else None
        selected_node = path_decision.get("selected_node")
        candidates = _branch_candidates_for_field(reader, execution_order, field)
        decisions.append(
            TraversalBranchDecision(
                field=field,
                value=value_text,
                selected_node=str(selected_node) if selected_node else None,
                candidate_nodes=candidates,
                status="resolved" if value_text else "unresolved",
            )
        )
        seen_fields.add(field)

    for req in requirements.values():
        if req.requirement_class != "branch_decision":
            continue
        field = strategy_field(req)
        if field in seen_fields:
            continue
        value_text = field_value(field, existing_inputs)
        value_text = str(value_text).strip() if value_text is not None else None
        selected = None
        if value_text and reader is not None:
            store = _graph_store(reader)
            if store is not None:
                for node_id in execution_order:
                    node = store.get_node(node_id)
                    if node is None:
                        continue
                    metadata = node.metadata if isinstance(node.metadata, dict) else {}
                    if _applies_when_matches_field(
                        metadata,
                        field_name=field,
                        field_value_text=value_text,
                    ):
                        selected = node_id
                        break
        candidates = _branch_candidates_for_field(reader, execution_order, field)
        decisions.append(
            TraversalBranchDecision(
                field=field,
                value=value_text,
                selected_node=selected,
                candidate_nodes=candidates,
                status="resolved" if value_text else "unresolved",
            )
        )
        seen_fields.add(field)

    return decisions


def _append_equation_gathering_pending(
    pending: list[TraversalPendingNode],
    *,
    reader: StandardsReader | None,
    requirements: dict[str, PlanRequirement],
    active_node_id: str | None,
    seen: set[str],
) -> None:
    if not _gate_phases_clear(requirements):
        return
    for req in requirements.values():
        if req.requirement_class != "equation_result":
            continue
        if req.status in {"resolved", "not_applicable"}:
            continue
        if req.activation_status != "active":
            continue
        resolution = req.resolution if isinstance(req.resolution, dict) else {}
        equation_id = str(resolution.get("source_node_id") or "").strip()
        if not equation_id or equation_id in seen or equation_id == active_node_id:
            continue
        if not _equation_dep_unresolved(req, requirements) and req.status != "missing":
            continue
        seen.add(equation_id)
        node_type = _infer_node_type(reader, equation_id)
        pending.append(
            TraversalPendingNode(
                node_id=equation_id,
                node_type=node_type,
                title=_node_title(reader, equation_id, node_type=node_type),
                phase=req.phase,
                waiting_on=[],
                reason="Awaiting parameter gathering.",
            )
        )


def _build_pending_nodes(
    *,
    reader: StandardsReader | None,
    requirements: dict[str, PlanRequirement],
    input_strategy: InputStrategy | None,
    active_node_id: str | None,
    branch_decisions: list[TraversalBranchDecision],
    existing_inputs: dict[str, Any],
) -> list[TraversalPendingNode]:
    pending: list[TraversalPendingNode] = []
    seen: set[str] = set()

    for req in requirements.values():
        if req.status not in {"missing", "blocked"}:
            continue
        if req.activation_status != "active":
            continue
        if req.requirement_class in {"report_output", "table_lookup", "equation_result"}:
            continue
        node_id = req.parameter_node_id or param_node_id_for_input(req.field)
        if not node_id or node_id == active_node_id:
            continue
        waiting_on = _waiting_on_param_nodes(req, requirements)
        if not waiting_on and req.status == "missing":
            waiting_on = _infer_waiting_on_for_missing(req, requirements, input_strategy)
        if req.status == "missing" and not waiting_on:
            if req.requirement_class == "user_input":
                _append_pending(
                    pending,
                    reader=reader,
                    node_id=node_id,
                    waiting_on=[],
                    phase=req.phase,
                    reason="Awaiting user input.",
                    seen=seen,
                )
            continue
        _append_pending(
            pending,
            reader=reader,
            node_id=node_id,
            waiting_on=waiting_on,
            phase=req.phase,
            reason=f"Waiting on dependencies for {req.resolved_title()}.",
            seen=seen,
        )

    _append_equation_gathering_pending(
        pending,
        reader=reader,
        requirements=requirements,
        active_node_id=active_node_id,
        seen=seen,
    )

    for decision in branch_decisions:
        if decision.status == "resolved":
            continue
        default_value = _default_branch_value(decision.field)
        branch_param = param_node_id_for_input(decision.field)
        for candidate_id in decision.candidate_nodes:
            if candidate_id == active_node_id:
                continue
            store = _graph_store(reader)
            if store is None:
                continue
            node = store.get_node(candidate_id)
            if node is None:
                continue
            metadata = node.metadata if isinstance(node.metadata, dict) else {}
            applicability = metadata.get("applicability") or {}
            applies_when = applicability.get("applies_when") if isinstance(applicability, dict) else None
            if not applies_when:
                continue
            include = False
            for item in applies_when:
                if not isinstance(item, dict):
                    continue
                clause_field = _field_from_param_ref(str(item.get("parameter") or ""))
                if clause_field != decision.field:
                    continue
                clause_value = str(item.get("value") or "").strip()
                if default_value and clause_value == default_value:
                    include = True
                    break
            if not include:
                continue
            _append_pending(
                pending,
                reader=reader,
                node_id=candidate_id,
                waiting_on=[branch_param] if branch_param else [],
                phase="parameter_gathering",
                reason=f"Branch paragraph pending {decision.field} selection.",
                seen=seen,
            )

        branch_value = field_value(decision.field, existing_inputs)
        branch_value = str(branch_value).strip() if branch_value is not None else None
        if branch_value:
            for candidate_id in decision.candidate_nodes:
                if candidate_id == active_node_id:
                    continue
                store = _graph_store(reader)
                if store is None:
                    continue
                node = store.get_node(candidate_id)
                if node is None:
                    continue
                metadata = node.metadata if isinstance(node.metadata, dict) else {}
                if not _applies_when_matches_field(
                    metadata,
                    field_name=decision.field,
                    field_value_text=branch_value,
                ):
                    continue
                _append_pending(
                    pending,
                    reader=reader,
                    node_id=candidate_id,
                    waiting_on=[branch_param] if branch_param else [],
                    phase="parameter_gathering",
                    reason=f"Branch paragraph pending {decision.field} resolution.",
                    seen=seen,
                )

    return pending


def _build_expanded_nodes(
    *,
    reader: StandardsReader | None,
    workflow_id: str,
    graph: PlanGraph,
    requirements: dict[str, PlanRequirement],
) -> list[TraversalExpandedNode]:
    workflow_node_id = _canonical_workflow_node_id(reader, workflow_id)
    gate_req_ids = [
        req.id
        for req in requirements.values()
        if req.phase in {"expansion_assumptions", "path_decisions"}
        and req.requirement_class in {"user_input", "branch_decision"}
    ]

    order = 1
    expanded: list[TraversalExpandedNode] = []
    seen: set[str] = set()

    if workflow_node_id:
        expanded.append(
            TraversalExpandedNode(
                node_id=workflow_node_id,
                node_type="workflow",
                title=_node_title(reader, workflow_node_id, node_type="workflow"),
                expanded_at_order=order,
                produced_requirements=[rid for rid in gate_req_ids if rid in requirements],
                produced_edges=[],
            )
        )
        seen.add(workflow_node_id)
        order += 1

    for node_id in graph.expanded_node_ids:
        if node_id in seen:
            continue
        node_type = _infer_node_type(reader, node_id)
        if node_type == "parameter":
            continue
        seen.add(node_id)
        expanded.append(
            TraversalExpandedNode(
                node_id=node_id,
                node_type=node_type,
                title=_node_title(reader, node_id, node_type=node_type),
                expanded_at_order=order,
                produced_requirements=[],
                produced_edges=[],
            )
        )
        order += 1

    return expanded


def _build_candidate_next_nodes(
    *,
    reader: StandardsReader | None,
    active_node_id: str | None,
    pending_nodes: list[TraversalPendingNode],
    branch_decisions: list[TraversalBranchDecision],
) -> list[TraversalCandidateNode]:
    candidates: list[TraversalCandidateNode] = []
    seen: set[str] = set()

    if active_node_id:
        for pending in pending_nodes:
            if pending.node_id in seen:
                continue
            if pending.waiting_on == [active_node_id]:
                seen.add(pending.node_id)
                candidates.append(
                    TraversalCandidateNode(
                        node_id=pending.node_id,
                        node_type=pending.node_type,
                        title=pending.title,
                        reason="Next node after active gate.",
                    )
                )

    for decision in branch_decisions:
        if decision.status != "unresolved":
            continue
        branch_param = param_node_id_for_input(decision.field)
        if active_node_id != branch_param:
            continue
        for candidate_id in decision.candidate_nodes:
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            node_type = _infer_node_type(reader, candidate_id)
            candidates.append(
                TraversalCandidateNode(
                    node_id=candidate_id,
                    node_type=node_type,
                    title=_node_title(reader, candidate_id, node_type=node_type),
                    reason=f"Candidate branch for {decision.field}.",
                )
            )

    return candidates


def _build_traversal_events(
    *,
    expanded_nodes: list[TraversalExpandedNode],
    active_node: TraversalActiveNode | None,
    branch_decisions: list[TraversalBranchDecision],
    pending_nodes: list[TraversalPendingNode],
    input_strategy: InputStrategy | None = None,
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

    if input_strategy is not None:
        for field in input_strategy.resolved_fields:
            node_id = param_node_id_for_input(field)
            order += 1
            events.append(
                TraversalEvent(
                    order=order,
                    event_type="parameter_resolved",
                    node_id=node_id,
                    message=f"User input resolved for {field}.",
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
    reader: StandardsReader | None = None,
    preview: Any | None = None,
) -> PlannerTraversalState | None:
    """Derive compact planner traversal snapshot from plan graph and requirements."""
    if not workflow_id:
        return None

    inputs = dict(existing_inputs or {})
    execution_order = _execution_order(preview, graph)

    active_node_id, active_node = _build_active_node(
        reader=reader,
        requirements=requirements,
        input_strategy=input_strategy,
    )
    branch_decisions = _build_branch_decisions(
        reader=reader,
        requirements=requirements,
        path_decision=path_decision,
        existing_inputs=inputs,
        execution_order=execution_order,
    )
    pending_nodes = _build_pending_nodes(
        reader=reader,
        requirements=requirements,
        input_strategy=input_strategy,
        active_node_id=active_node_id,
        branch_decisions=branch_decisions,
        existing_inputs=inputs,
    )
    expanded_nodes = _build_expanded_nodes(
        reader=reader,
        workflow_id=workflow_id,
        graph=graph,
        requirements=requirements,
    )
    candidate_next_nodes = _build_candidate_next_nodes(
        reader=reader,
        active_node_id=active_node_id,
        pending_nodes=pending_nodes,
        branch_decisions=branch_decisions,
    )
    traversal_events = _build_traversal_events(
        expanded_nodes=expanded_nodes,
        active_node=active_node,
        branch_decisions=branch_decisions,
        pending_nodes=pending_nodes,
        input_strategy=input_strategy,
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
    reader: StandardsReader | None = None,
    preview: Any | None = None,
) -> PlannerTraversalState | None:
    return build_planner_traversal_state(
        plan_id=plan.plan_id,
        workflow_id=plan.workflow_id,
        requirements=plan.requirements,
        input_strategy=plan.input_strategy,
        graph=plan.graph,
        path_decision=path_decision,
        existing_inputs=existing_inputs,
        reader=reader,
        preview=preview,
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


def build_traversal_path_view(traversal: PlannerTraversalState) -> list[dict[str, Any]]:
    """Ordered timeline rows for inspector UI (debug visualization only)."""
    rows: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()

    for item in sorted(traversal.expanded_nodes, key=lambda node: node.expanded_at_order):
        seen_node_ids.add(item.node_id)
        rows.append(
            {
                "node_id": item.node_id,
                "title": item.title,
                "node_type": item.node_type,
                "state": "completed",
                "reason": None,
                "waiting_on": [],
            }
        )

    if traversal.current_active_node is not None:
        active = traversal.current_active_node
        seen_node_ids.add(active.node_id)
        rows.append(
            {
                "node_id": active.node_id,
                "title": active.title,
                "node_type": active.node_type,
                "state": "current",
                "reason": active.reason,
                "waiting_on": [],
            }
        )

    skipped_node_ids: set[str] = set()
    for event in traversal.traversal_events:
        if event.event_type not in {"node_marked_not_applicable", "node_deferred"}:
            continue
        if not event.node_id or event.node_id in seen_node_ids:
            continue
        skipped_node_ids.add(event.node_id)
        rows.append(
            {
                "node_id": event.node_id,
                "title": None,
                "node_type": None,
                "state": "skipped",
                "reason": event.message,
                "waiting_on": [],
            }
        )

    for item in traversal.pending_expansion_nodes:
        if item.node_id in seen_node_ids or item.node_id in skipped_node_ids:
            continue
        state = "blocked" if item.waiting_on else "pending"
        rows.append(
            {
                "node_id": item.node_id,
                "title": item.title,
                "node_type": item.node_type,
                "state": state,
                "reason": item.reason,
                "waiting_on": list(item.waiting_on),
            }
        )

    for item in traversal.candidate_next_nodes:
        if item.node_id in seen_node_ids or item.node_id in skipped_node_ids:
            continue
        rows.append(
            {
                "node_id": item.node_id,
                "title": item.title,
                "node_type": item.node_type,
                "state": "pending",
                "reason": item.reason,
                "waiting_on": [],
            }
        )

    return rows
