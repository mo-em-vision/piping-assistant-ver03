"""Read-only developer inspection projection derived from EngineeringPlan.

Never used for workflow execution, user-facing output, graph traversal,
equation evaluation, validation, or parameter resolution.
"""

from __future__ import annotations

from typing import Any

from engine.graph.traversal_reasons import (
    CANONICAL_EXCLUSION_REASONS,
    CANONICAL_QUEUE_REASONS,
    EXCLUSION_REASON_NOT_APPLICABLE,
    EXCLUSION_REASON_SUPERSEDED_BY_SELECTED_BRANCH,
    QUEUE_REASON_BRANCH_CONDITION_PENDING,
    QUEUE_REASON_READY_FOR_EXPANSION,
    QUEUE_REASON_WAITING_FOR_DEPENDENCY,
    QUEUE_REASON_WAITING_FOR_UPSTREAM_EQUATION,
    QUEUE_REASON_WAITING_FOR_USER_INPUT,
    normalize_exclusion_reason,
    normalize_queue_reason,
)
from engine.planner.plan_inspector import engineering_plan_from_dict
from engine.planner.workflow_goal_metadata import workflow_title_for_goal
from engine.reference.parameter_keys import load_parameter_node_metadata, param_node_id_for_input
from engine.reference.standards_reader import StandardsReader
from models.engineering_plan import (
    EngineeringPlan,
    PlanRequirement,
    PlannerTraversalState,
    TraversalCandidateNode,
    TraversalExpandedNode,
    TraversalPendingNode,
)

_STATUS_REASONS = CANONICAL_QUEUE_REASONS | CANONICAL_EXCLUSION_REASONS

_EXCLUDED_EVENT_TYPES = frozenset({"node_marked_not_applicable"})
_BLOCKED_EVENT_TYPES = frozenset({"node_deferred"})


def _human_label(
    node_id: str,
    *,
    title: str | None,
    reader: StandardsReader | None,
) -> str:
    if title and str(title).strip():
        return str(title).strip()
    if node_id.startswith("PARAM-"):
        meta = load_parameter_node_metadata(node_id)
        if meta is not None:
            name = str(meta.get("name") or meta.get("title") or "").strip()
            if name:
                return name
    if reader is not None:
        try:
            record = reader.load(node_id)
            loaded = str(
                record.metadata.get("name")
                or record.metadata.get("title")
                or ""
            ).strip()
            if loaded:
                return loaded
        except (FileNotFoundError, KeyError, OSError):
            pass
    return node_id


def _node_item(
    node_id: str,
    node_type: str,
    *,
    title: str | None,
    reader: StandardsReader | None,
    status_reason: str | None = None,
) -> dict[str, Any]:
    """Debugger rows use node_id as display_name for traceability."""
    item: dict[str, Any] = {
        "node_id": node_id,
        "node_type": node_type,
        "display_name": node_id,
        "label": _human_label(node_id, title=title, reader=reader),
    }
    if status_reason is not None:
        item["status_reason"] = status_reason
    return item


def _requirement_for_node(plan: EngineeringPlan, node_id: str) -> PlanRequirement | None:
    for req in plan.requirements.values():
        if req.parameter_node_id == node_id:
            return req
    return None


def _excluded_node_ids(traversal: PlannerTraversalState) -> set[str]:
    excluded: set[str] = set()
    for event in traversal.traversal_events:
        if event.event_type not in _EXCLUDED_EVENT_TYPES:
            continue
        if event.node_id:
            excluded.add(event.node_id)
    return excluded


def _has_excluded_by_branch_event(traversal: PlannerTraversalState, node_id: str) -> bool:
    for event in traversal.traversal_events:
        if event.node_id != node_id:
            continue
        if event.event_type == "node_marked_not_applicable":
            return True
    return False


def _pending_status_reason(
    plan: EngineeringPlan,
    traversal: PlannerTraversalState,
    item: TraversalPendingNode,
) -> str:
    reason_lower = str(item.reason or "").lower()
    if item.node_type == "equation" and "parameter gathering" in reason_lower:
        return QUEUE_REASON_WAITING_FOR_UPSTREAM_EQUATION
    if item.waiting_on:
        return QUEUE_REASON_WAITING_FOR_DEPENDENCY
    if _has_excluded_by_branch_event(traversal, item.node_id):
        return EXCLUSION_REASON_SUPERSEDED_BY_SELECTED_BRANCH

    req = _requirement_for_node(plan, item.node_id)
    if req is not None:
        if req.activation_status == "not_applicable" or req.status == "not_applicable":
            return QUEUE_REASON_BRANCH_CONDITION_PENDING
        if req.status == "resolved":
            return QUEUE_REASON_READY_FOR_EXPANSION
        if req.requirement_class == "user_input" and req.status == "missing":
            return QUEUE_REASON_WAITING_FOR_USER_INPUT
        if req.requirement_class == "equation_result" and req.status in {"missing", "blocked"}:
            return QUEUE_REASON_WAITING_FOR_UPSTREAM_EQUATION

    return normalize_queue_reason(item.reason)


def _status_reason_for_queue_node(
    plan: EngineeringPlan,
    traversal: PlannerTraversalState,
    *,
    node_id: str,
    waiting_on: list[str],
    is_candidate: bool,
    pending: TraversalPendingNode | None = None,
) -> str:
    if pending is not None:
        return _pending_status_reason(plan, traversal, pending)
    if waiting_on:
        return QUEUE_REASON_WAITING_FOR_DEPENDENCY
    if is_candidate:
        return QUEUE_REASON_READY_FOR_EXPANSION
    if _has_excluded_by_branch_event(traversal, node_id):
        return EXCLUSION_REASON_SUPERSEDED_BY_SELECTED_BRANCH

    req = _requirement_for_node(plan, node_id)
    if req is not None:
        if req.activation_status == "not_applicable" or req.status == "not_applicable":
            return QUEUE_REASON_BRANCH_CONDITION_PENDING
        if req.status == "resolved":
            return QUEUE_REASON_READY_FOR_EXPANSION
        if req.requirement_class == "user_input" and req.status == "missing":
            return QUEUE_REASON_WAITING_FOR_USER_INPUT
        if req.requirement_class == "equation_result" and req.status in {"missing", "blocked"}:
            return QUEUE_REASON_WAITING_FOR_UPSTREAM_EQUATION

    return QUEUE_REASON_WAITING_FOR_DEPENDENCY


def _visited_from_beginning(
    plan: EngineeringPlan,
    traversal: PlannerTraversalState,
    *,
    reader: StandardsReader | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in sorted(traversal.expanded_nodes, key=lambda node: node.expanded_at_order):
        rows.append(
            _node_item(
                item.node_id,
                item.node_type,
                title=item.title,
                reader=reader,
            )
        )
    return rows


def _visited_previous_step(
    plan: EngineeringPlan,
    traversal: PlannerTraversalState,
    *,
    reader: StandardsReader | None,
) -> list[dict[str, Any]]:
    resolved_events = [
        event
        for event in traversal.traversal_events
        if event.event_type == "parameter_resolved" and event.node_id
    ]
    if resolved_events:
        last = resolved_events[-1]
        node_id = str(last.node_id)
        node_type = "parameter" if node_id.startswith("PARAM-") else "unknown"
        return [
            _node_item(
                node_id,
                node_type,
                title=None,
                reader=reader,
            )
        ]

    current_id = traversal.current_active_node_id
    candidates = [
        item for item in traversal.expanded_nodes if item.node_id != current_id
    ]
    if not candidates:
        return []
    max_order = max(item.expanded_at_order for item in candidates)
    return [
        _node_item(item.node_id, item.node_type, title=item.title, reader=reader)
        for item in sorted(candidates, key=lambda node: node.expanded_at_order)
        if item.expanded_at_order == max_order
    ]


def _node_metadata_maps(
    traversal: PlannerTraversalState,
) -> tuple[dict[str, str], dict[str, str | None]]:
    node_types: dict[str, str] = {}
    node_titles: dict[str, str | None] = {}

    for item in traversal.expanded_nodes:
        node_types[item.node_id] = item.node_type
        node_titles[item.node_id] = item.title
    for item in traversal.pending_expansion_nodes:
        node_types[item.node_id] = item.node_type
        node_titles[item.node_id] = item.title
    for item in traversal.candidate_next_nodes:
        node_types[item.node_id] = item.node_type
        node_titles[item.node_id] = item.title
    if traversal.current_active_node is not None:
        active = traversal.current_active_node
        node_types[active.node_id] = active.node_type
        node_titles[active.node_id] = active.title
    return node_types, node_titles


def _excluded_nodes(
    plan: EngineeringPlan,
    traversal: PlannerTraversalState,
    *,
    reader: StandardsReader | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    node_types, node_titles = _node_metadata_maps(traversal)

    for event in traversal.traversal_events:
        if event.event_type not in _EXCLUDED_EVENT_TYPES:
            continue
        node_id = event.node_id
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        rows.append(
            _node_item(
                node_id,
                node_types.get(node_id, "unknown"),
                title=node_titles.get(node_id),
                reader=reader,
                status_reason=normalize_exclusion_reason(event.message),
            )
        )
    return rows


def _blocked_nodes(
    plan: EngineeringPlan,
    traversal: PlannerTraversalState,
    *,
    reader: StandardsReader | None,
) -> list[dict[str, Any]]:
    """Deprecated — blocked/waiting nodes are unified under queue_leaf_nodes."""
    return []


def _excluded_blocked(
    plan: EngineeringPlan,
    traversal: PlannerTraversalState,
    *,
    reader: StandardsReader | None,
) -> list[dict[str, Any]]:
    """Deprecated combined list — excluded first, then blocked."""
    return _excluded_nodes(plan, traversal, reader=reader) + _blocked_nodes(
        plan, traversal, reader=reader
    )


def _definition_equation_pending_items(
    task: Any,
    reader: StandardsReader | None,
) -> list[dict[str, Any]]:
    if task is None or reader is None:
        return []
    try:
        from engine.graph.definition_equations import (
            has_execution_trace,
            pending_definition_equation_inputs,
        )
        from engine.graph.graph_engine import normalize_root_id
        from engine.planner.tools import GraphTools
    except ImportError:
        return []

    if not has_execution_trace(task):
        return []

    workflow_id = str(
        task.outputs.get("workflow") or task.outputs.get("selected_root") or ""
    ).strip()
    if not workflow_id:
        return []

    slug = normalize_root_id(workflow_id)
    graph = GraphTools(reader)
    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id=slug,
        inputs=dict(task.fact_store.active_facts()),
    )
    pending_fields = pending_definition_equation_inputs(
        task,
        reader,
        preview.execution_order,
    )
    rows: list[dict[str, Any]] = []
    for field in pending_fields:
        node_id = param_node_id_for_input(field)
        rows.append(
            _node_item(
                node_id,
                "parameter",
                title=None,
                reader=reader,
                status_reason=QUEUE_REASON_WAITING_FOR_USER_INPUT,
            )
        )
    return rows


def _queue_leaf_nodes(
    plan: EngineeringPlan,
    traversal: PlannerTraversalState,
    *,
    reader: StandardsReader | None,
    excluded_ids: set[str],
    task: Any | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append_row(
        node_id: str,
        node_type: str,
        *,
        title: str | None,
        status_reason: str,
    ) -> None:
        if node_id in seen or node_id in excluded_ids:
            return
        seen.add(node_id)
        rows.append(
            _node_item(
                node_id,
                node_type,
                title=title,
                reader=reader,
                status_reason=status_reason,
            )
        )

    equation_pending = [
        item
        for item in traversal.pending_expansion_nodes
        if item.node_type == "equation"
        or "parameter gathering" in str(item.reason or "").lower()
    ]
    other_pending = [
        item for item in traversal.pending_expansion_nodes if item not in equation_pending
    ]

    for item in equation_pending:
        append_row(
            item.node_id,
            item.node_type,
            title=item.title,
            status_reason=_pending_status_reason(plan, traversal, item),
        )

    for item in other_pending:
        append_row(
            item.node_id,
            item.node_type,
            title=item.title,
            status_reason=_pending_status_reason(plan, traversal, item),
        )

    node_types, node_titles = _node_metadata_maps(traversal)
    for event in traversal.traversal_events:
        if event.event_type not in _BLOCKED_EVENT_TYPES:
            continue
        node_id = event.node_id
        if not node_id:
            continue
        append_row(
            node_id,
            node_types.get(node_id, "unknown"),
            title=node_titles.get(node_id),
            status_reason=normalize_queue_reason(event.message),
        )

    for item in traversal.candidate_next_nodes:
        append_row(
            item.node_id,
            item.node_type,
            title=item.title,
            status_reason=_status_reason_for_queue_node(
                plan,
                traversal,
                node_id=item.node_id,
                waiting_on=[],
                is_candidate=True,
            ),
        )

    for item in _definition_equation_pending_items(task, reader):
        append_row(
            item["node_id"],
            item["node_type"],
            title=item.get("label"),
            status_reason=str(
                item.get("status_reason") or QUEUE_REASON_WAITING_FOR_USER_INPUT
            ),
        )

    return rows


def _current_node_ref(
    traversal: PlannerTraversalState,
    *,
    reader: StandardsReader | None,
) -> dict[str, Any] | None:
    active = traversal.current_active_node
    if active is None:
        return None
    return _node_item(active.node_id, active.node_type, title=active.title, reader=reader)


def _goals(plan: EngineeringPlan, *, reader: StandardsReader | None) -> dict[str, Any]:
    main_goal = str(plan.root_goal.title or "").strip()
    if not main_goal and reader is not None and plan.workflow_id:
        main_goal = str(workflow_title_for_goal(reader, plan.workflow_id) or "").strip()
    if not main_goal:
        main_goal = plan.root_goal.key or plan.workflow_id or "Goal"

    subgoals: list[str] = []
    for field in plan.root_goal.required_outputs:
        title = None
        for req in plan.requirements.values():
            if req.field == field:
                title = req.resolved_title()
                break
        subgoals.append(title or field.replace("_", " ").title())

    if not subgoals and plan.phases:
        subgoals = [
            phase.title
            for phase in sorted(plan.phases, key=lambda item: item.order)
            if str(phase.title or "").strip()
        ]

    return {"main_goal": main_goal, "subgoals": subgoals}


def _empty_groups() -> dict[str, Any]:
    return {
        "visited_previous_step": [],
        "queue_leaf_nodes": [],
        "visited_from_beginning": [],
        "excluded_nodes": [],
        "blocked_nodes": [],
        "excluded_blocked": [],
    }


def build_planner_debug_view(
    plan: EngineeringPlan,
    *,
    reader: StandardsReader | None = None,
    task: Any | None = None,
) -> dict[str, Any]:
    """Workflow-agnostic minimal debugger view from plan.traversal and root goal."""
    goals = _goals(plan, reader=reader)
    traversal = plan.traversal

    if traversal is None:
        return {
            "current_node": None,
            "next_queued_node": None,
            "goals": goals,
            "groups": _empty_groups(),
        }

    excluded_ids = _excluded_node_ids(traversal)
    queue = _queue_leaf_nodes(
        plan,
        traversal,
        reader=reader,
        excluded_ids=excluded_ids,
        task=task,
    )
    current = _current_node_ref(traversal, reader=reader)
    next_queued = queue[0] if queue else None
    if next_queued is not None:
        next_queued = {
            "node_id": next_queued["node_id"],
            "node_type": next_queued["node_type"],
            "display_name": next_queued["display_name"],
            "label": next_queued.get("label"),
        }

    excluded = _excluded_nodes(plan, traversal, reader=reader)
    blocked = _blocked_nodes(plan, traversal, reader=reader)

    return {
        "current_node": current,
        "next_queued_node": next_queued,
        "goals": goals,
        "groups": {
            "visited_previous_step": _visited_previous_step(plan, traversal, reader=reader),
            "queue_leaf_nodes": queue,
            "visited_from_beginning": _visited_from_beginning(plan, traversal, reader=reader),
            "excluded_nodes": excluded,
            "blocked_nodes": blocked,
            "excluded_blocked": excluded + blocked,
        },
    }


def build_planner_debug_projection(
    plan: EngineeringPlan,
    *,
    reader: StandardsReader | None = None,
    task: Any | None = None,
) -> dict[str, Any]:
    """Read-only dev inspection view derived from engineering_plan. Never used for execution."""
    return build_planner_debug_view(plan, reader=reader, task=task)


def build_planner_debug_projection_from_dict(
    raw: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
    task: Any | None = None,
) -> dict[str, Any] | None:
    plan = engineering_plan_from_dict(raw)
    if plan is None:
        return None
    return build_planner_debug_projection(plan, reader=reader, task=task)


def planner_debug_projection_for_task(
    task,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any] | None:
    """Dev-only projection derived from task.outputs engineering_plan snapshot."""
    raw = task.outputs.get("engineering_plan")
    if isinstance(raw, dict) and "requirements" in raw and "root_goal" in raw:
        return build_planner_debug_projection_from_dict(raw, reader=reader, task=task)
    return None


__all__ = [
    "_STATUS_REASONS",
    "build_planner_debug_projection",
    "build_planner_debug_projection_from_dict",
    "build_planner_debug_view",
    "planner_debug_projection_for_task",
]
