"""Read-only developer inspection projection derived from EngineeringPlan.

Never used for workflow execution, user-facing output, graph traversal,
equation evaluation, validation, or parameter resolution.
"""

from __future__ import annotations

from typing import Any

from engine.planner.plan_inspector import (
    _PHASE_TITLES,
    _derive_status_badge,
    _derived_or_lookup_summary,
    _is_outstanding_requirement,
    _requirement_matches_field,
    _resolve_current_phase,
    build_planner_inspector_summary,
    dependency_ids_to_fields,
    engineering_plan_from_dict,
)
from engine.planner.planner_traversal import build_traversal_path_view
from engine.planner.workflow_goal_metadata import workflow_title_for_goal
from engine.reference.parameter_keys import load_parameter_node_metadata, param_node_id_for_input
from engine.reference.standards_reader import StandardsReader
from engine.units.unit_ids import symbol_from_unit_id
from models.engineering_plan import EngineeringPlan, PlanRequirement

_UNRESOLVED_STATUSES = frozenset({"missing", "ready", "blocked"})
_TIMELINE_STATE_MAP = {
    "completed": "visited",
    "current": "active",
    "pending": "pending",
    "blocked": "blocked",
    "skipped": "skipped",
}


def _workflow_title(plan: EngineeringPlan, *, reader: StandardsReader | None) -> str | None:
    title = str(plan.root_goal.title or "").strip()
    if title:
        return title
    if reader is not None and plan.workflow_id:
        return workflow_title_for_goal(reader, plan.workflow_id)
    return None


def _planner_confidence_from_plan(plan: EngineeringPlan) -> float | None:
    # TODO: persist planner selection confidence/reason on task for debug projection
    debug = plan.debug or {}
    raw = debug.get("planner_confidence")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _planner_reason_from_plan(plan: EngineeringPlan) -> str | None:
    # TODO: persist planner selection confidence/reason on task for debug projection
    debug = plan.debug or {}
    raw = debug.get("planner_reason")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _param_unit(meta: dict[str, Any] | None, req: PlanRequirement) -> str | None:
    if req.question_spec and req.question_spec.allowed_units:
        return req.question_spec.allowed_units[0]
    if meta is None:
        return None
    unit = str(meta.get("unit") or "").strip()
    if unit:
        return unit
    unit_id = str(meta.get("canonical_unit") or meta.get("unit_id") or "").strip()
    if unit_id.startswith("UNIT-"):
        return symbol_from_unit_id(unit_id)
    return None


def _required_input_rows(plan: EngineeringPlan) -> list[dict[str, Any]]:
    requirements = plan.requirements
    seen_fields: set[str] = set()
    rows: list[dict[str, Any]] = []

    candidates = [req for req in requirements.values() if _is_outstanding_requirement(req)]
    candidates.sort(
        key=lambda req: (
            req.question_spec.priority if req.question_spec else 50,
            req.question_spec.field if req.question_spec else req.field,
        )
    )

    for req in candidates:
        spec = req.question_spec
        field = spec.field if spec else req.field
        if field in seen_fields:
            continue
        seen_fields.add(field)

        param_node_id = req.parameter_node_id or param_node_id_for_input(field)
        meta = load_parameter_node_metadata(param_node_id) if param_node_id else None
        symbol = None
        if meta is not None:
            symbol = str(meta.get("symbol") or meta.get("canonical_symbol") or "").strip() or None

        label = spec.label if spec else req.resolved_title()
        if meta is not None:
            name = str(meta.get("name") or "").strip()
            if name:
                label = name

        rows.append(
            {
                "key": field,
                "symbol": symbol,
                "label": label,
                "status": req.status,
                "expected_input_type": spec.expected_value_class if spec else "selection",
                "unit": _param_unit(meta, req),
                "reason_required": spec.reason_code if spec and spec.reason_code else req.phase,
            }
        )

    return rows


def _active_node(plan: EngineeringPlan) -> dict[str, Any] | None:
    if plan.traversal and plan.traversal.current_active_node is not None:
        active = plan.traversal.current_active_node
        return {
            "node_id": active.node_id,
            "title": active.title,
            "node_type": active.node_type,
            "why_active": active.reason,
        }

    strategy = plan.input_strategy
    if strategy and strategy.next_fields:
        field = strategy.next_fields[0]
        for req in plan.requirements.values():
            if not _requirement_matches_field(req, field):
                continue
            if req.activation_status != "active":
                continue
            param_node_id = req.parameter_node_id or param_node_id_for_input(field)
            return {
                "node_id": param_node_id,
                "title": req.resolved_title(),
                "node_type": "parameter",
                "why_active": (
                    req.question_spec.reason_code
                    if req.question_spec and req.question_spec.reason_code
                    else f"Next required field: {field}"
                ),
            }

    return None


def _visited_timeline(plan: EngineeringPlan) -> list[dict[str, Any]]:
    if plan.traversal is None:
        return []
    rows = build_traversal_path_view(plan.traversal)
    timeline: list[dict[str, Any]] = []
    for row in rows:
        raw_state = str(row.get("state") or "pending")
        timeline.append(
            {
                "node_id": row.get("node_id"),
                "title": row.get("title"),
                "node_type": row.get("node_type"),
                "why_visited": row.get("reason"),
                "status": _TIMELINE_STATE_MAP.get(raw_state, raw_state),
                "waiting_on": list(row.get("waiting_on") or []),
            }
        )
    return timeline


def _pending_nodes(plan: EngineeringPlan) -> list[dict[str, Any]]:
    if plan.traversal is None:
        return []
    rows: list[dict[str, Any]] = []
    for item in plan.traversal.pending_expansion_nodes:
        rows.append(
            {
                "node_id": item.node_id,
                "title": item.title,
                "node_type": item.node_type,
                "reason": item.reason,
                "waiting_on": list(item.waiting_on),
            }
        )
    for item in plan.traversal.candidate_next_nodes:
        rows.append(
            {
                "node_id": item.node_id,
                "title": item.title,
                "node_type": item.node_type,
                "reason": item.reason,
                "waiting_on": [],
            }
        )
    return rows


def _pending_calculations(plan: EngineeringPlan) -> list[dict[str, Any]]:
    requirements = plan.requirements
    items = [
        req
        for req in requirements.values()
        if req.requirement_class == "equation_result"
        and req.activation_status == "active"
        and req.status in _UNRESOLVED_STATUSES
    ]
    items.sort(key=lambda req: req.field)
    return [
        {
            "field": req.field,
            "title": req.resolved_title(),
            "status": req.status,
            "depends_on": dependency_ids_to_fields(req.depends_on, requirements),
            "reason": f"Calculation {req.status}",
        }
        for req in items
    ]


def _pending_validations(plan: EngineeringPlan) -> list[dict[str, Any]]:
    requirements = plan.requirements
    items = [
        req
        for req in requirements.values()
        if req.phase == "validation"
        and req.activation_status == "active"
        and req.status in _UNRESOLVED_STATUSES
    ]
    items.sort(key=lambda req: req.field)
    return [
        {
            "field": req.field,
            "title": req.resolved_title(),
            "status": req.status,
            "reason": f"Validation {req.status}",
        }
        for req in items
    ]


def _pending_lookups(plan: EngineeringPlan) -> list[dict[str, Any]]:
    requirements = plan.requirements
    entries = _derived_or_lookup_summary(requirements)
    pending = [
        item
        for item in entries
        if str(item.get("status") or "") in _UNRESOLVED_STATUSES
        and str(item.get("activation_status") or "active") == "active"
    ]
    return [
        {
            "field": item["field"],
            "title": item.get("title") or item["field"],
            "status": item.get("status"),
            "depends_on": list(item.get("depends_on") or []),
            "reason": f"Lookup {item.get('status')}",
        }
        for item in pending
    ]


def _outstanding_user_inputs(plan: EngineeringPlan) -> list[PlanRequirement]:
    return [req for req in plan.requirements.values() if _is_outstanding_requirement(req)]


def _requirement_by_id(requirements: dict[str, PlanRequirement], requirement_id: str) -> PlanRequirement | None:
    return requirements.get(requirement_id)


def _depends_on_unresolved(req: PlanRequirement, requirements: dict[str, PlanRequirement]) -> list[str]:
    unresolved: list[str] = []
    for dep_id in req.depends_on:
        dep = _requirement_by_id(requirements, dep_id)
        if dep is None:
            continue
        if dep.status in {"missing", "blocked"}:
            unresolved.append(dep.field)
    return unresolved


def _blocked_reason(
    plan: EngineeringPlan,
    *,
    required_inputs: list[dict[str, Any]],
) -> dict[str, Any]:
    requirements = plan.requirements
    debug = plan.debug or {}
    validation_errors = list(debug.get("validation_errors") or [])

    if plan.root_goal.status == "complete":
        return {
            "kind": "complete",
            "message": "Workflow complete",
            "missing_item": None,
        }

    if validation_errors:
        return {
            "kind": "blocked_by_validation",
            "message": str(validation_errors[0]),
            "missing_item": None,
        }

    outstanding = _outstanding_user_inputs(plan)
    if outstanding:
        first = outstanding[0]
        field = first.question_spec.field if first.question_spec else first.field
        return {
            "kind": "waiting_for_user_input",
            "message": f"Waiting for user input: {first.resolved_title()}",
            "missing_item": field,
        }

    lookup_pending = _pending_lookups(plan)
    if lookup_pending:
        first = lookup_pending[0]
        return {
            "kind": "waiting_for_lookup_resolution",
            "message": f"Waiting for lookup: {first['title']}",
            "missing_item": first["field"],
        }

    for req in requirements.values():
        if req.requirement_class != "equation_result":
            continue
        if req.status != "blocked":
            continue
        unresolved = _depends_on_unresolved(req, requirements)
        if unresolved:
            return {
                "kind": "waiting_for_equation_dependency",
                "message": f"Equation blocked on: {', '.join(unresolved)}",
                "missing_item": req.field,
            }

    if required_inputs:
        return {
            "kind": "not_available",
            "message": "Plan has required inputs but blocker could not be classified from snapshot",
            "missing_item": required_inputs[0].get("key"),
        }

    return {
        "kind": "not_available",
        "message": "Insufficient plan evidence to classify blocker",
        "missing_item": None,
    }


def _next_expected_action(
    blocked_reason: dict[str, Any],
    *,
    required_inputs: list[dict[str, Any]],
    active_node: dict[str, Any] | None,
) -> str | None:
    kind = str(blocked_reason.get("kind") or "")
    if kind == "complete":
        return "Workflow complete"
    if kind == "waiting_for_user_input" and required_inputs:
        first = required_inputs[0]
        return f"Collect user input for {first.get('label') or first.get('key')}"
    if kind == "waiting_for_lookup_resolution":
        return f"Resolve lookup for {blocked_reason.get('missing_item') or 'pending parameter'}"
    if kind == "waiting_for_equation_dependency":
        return f"Resolve equation dependencies for {blocked_reason.get('missing_item') or 'calculation'}"
    if kind == "blocked_by_validation":
        return "Resolve validation errors before continuing"
    if active_node and active_node.get("title"):
        return f"Continue at {active_node['title']}"
    return None


def build_planner_debug_projection(
    plan: EngineeringPlan,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any]:
    """Read-only dev inspection view derived from engineering_plan. Never used for execution."""
    current_phase = _resolve_current_phase(plan)
    debug = plan.debug or {}
    validation_errors = list(debug.get("validation_errors") or [])
    warnings = list(debug.get("validation_warnings") or [])
    warnings.extend(validation_errors)

    required_inputs = _required_input_rows(plan)
    blocked = _blocked_reason(plan, required_inputs=required_inputs)
    active_node = _active_node(plan)
    inspector_summary = build_planner_inspector_summary(plan)

    return {
        "workflow_title": _workflow_title(plan, reader=reader),
        "workflow_slug": plan.workflow_id,
        "planner_confidence": _planner_confidence_from_plan(plan),
        "planner_reason": _planner_reason_from_plan(plan),
        "current_step": {
            "phase": current_phase,
            "phase_label": _PHASE_TITLES.get(
                current_phase,
                current_phase.replace("_", " ").title(),
            ),
            "status_badge": _derive_status_badge(
                plan,
                has_validation_errors=bool(validation_errors),
            ),
        },
        "active_node": active_node,
        "visited_timeline": _visited_timeline(plan),
        "pending_nodes": _pending_nodes(plan),
        "pending_calculations": _pending_calculations(plan),
        "pending_validations": _pending_validations(plan),
        "pending_lookups": _pending_lookups(plan),
        "required_inputs": required_inputs,
        "blocked_reason": blocked,
        "next_expected_action": _next_expected_action(
            blocked,
            required_inputs=required_inputs,
            active_node=active_node,
        ),
        "warnings": warnings,
        "raw_planner_state": {
            "engineering_plan": plan.to_dict(),
            "planner_inspector_summary": inspector_summary,
        },
    }


def build_planner_debug_projection_from_dict(
    raw: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any] | None:
    plan = engineering_plan_from_dict(raw)
    if plan is None:
        return None
    return build_planner_debug_projection(plan, reader=reader)


def planner_debug_projection_for_task(
    task,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any] | None:
    """Dev-only projection derived from task.outputs engineering_plan snapshot."""
    raw = task.outputs.get("engineering_plan")
    if isinstance(raw, dict) and "requirements" in raw and "root_goal" in raw:
        return build_planner_debug_projection_from_dict(raw, reader=reader)
    return None
