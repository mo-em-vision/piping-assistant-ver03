"""Compact planner inspector summary from EngineeringPlan."""

from __future__ import annotations

from typing import Any

from models.engineering_plan import EngineeringPlan, PlanRequirement

_PHASE_TITLES = {
    "expansion_assumptions": "Expansion assumptions",
    "path_decisions": "Path decisions",
    "parameter_gathering": "Parameter gathering",
    "coefficient_resolution": "Coefficient resolution",
    "execution_assumptions": "Execution assumptions",
    "definition_equation_completion": "Definition / equation completion",
    "ready": "Ready to execute",
    "equation_execution": "Equation execution",
    "validation": "Validation",
    "reporting": "Reporting",
}

_STATUS_LABELS = {
    "missing": "Needed",
    "resolved": "Complete",
    "blocked": "Waiting on dependencies",
    "ready": "Ready to resolve",
    "not_applicable": "Not applicable",
    "complete": "Complete",
    "active": "In progress",
    "pending": "Pending",
}

_REQUIREMENT_CLASS_LABELS = {
    "user_input": "User input",
    "branch_decision": "Path decision",
    "table_lookup": "Table lookup",
    "equation_result": "Calculation",
    "report_output": "Report",
    "selection_goal": "Selection",
}

_SYSTEM_RESOLVED_CLASSES = frozenset(
    {"table_lookup", "equation_result", "report_output", "derived_value"}
)

_PHASE_ORDER = (
    "expansion_assumptions",
    "path_decisions",
    "parameter_gathering",
    "coefficient_resolution",
    "execution_assumptions",
    "definition_equation_completion",
    "equation_execution",
    "validation",
    "reporting",
)


def _phase_order_index(phase: str) -> int:
    try:
        return _PHASE_ORDER.index(phase)
    except ValueError:
        return len(_PHASE_ORDER)


def _is_outstanding_requirement(req: PlanRequirement) -> bool:
    if req.activation_status != "active":
        return False
    if req.status not in {"missing", "ready"}:
        return False
    if req.activation_status == "not_applicable":
        return False
    if req.requirement_class not in {"user_input", "branch_decision"}:
        return False
    if not req.question_spec:
        return False
    if req.question_spec.ask_policy in {"do_not_ask", "ask_if_needed"}:
        return False
    return True


def _input_entry_from_requirement(req: PlanRequirement) -> dict[str, Any]:
    spec = req.question_spec
    field = spec.field if spec else req.field
    label = spec.label if spec else field.replace("_", " ").title()
    entry: dict[str, Any] = {
        "field": field,
        "label": label,
        "phase": req.phase,
        "expected_value_class": spec.expected_value_class if spec else "selection",
        "priority": spec.priority if spec else 50,
    }
    if spec and spec.allowed_units:
        entry["allowed_units"] = list(spec.allowed_units)
    if req.activation_status != "active":
        entry["activation_status"] = req.activation_status
    return entry


def _requirement_matches_field(req: PlanRequirement, field: str) -> bool:
    if req.question_spec and req.question_spec.field == field:
        return True
    return req.field == field


def _build_next_input(plan: EngineeringPlan, requirements: dict[str, PlanRequirement]) -> dict[str, Any] | None:
    strategy = plan.input_strategy
    if strategy is None or not strategy.next_fields:
        return None

    field = strategy.next_fields[0]
    for req in requirements.values():
        if req.activation_status != "active":
            continue
        if not _requirement_matches_field(req, field):
            continue
        if req.status != "missing":
            continue
        if req.requirement_class not in {"user_input", "branch_decision"}:
            continue
        if not req.question_spec:
            continue
        if req.question_spec.ask_policy in {"do_not_ask", "ask_if_needed", "ask_later"}:
            continue
        return _input_entry_from_requirement(req)

    return {
        "field": field,
        "label": field.replace("_", " ").title(),
        "phase": strategy.current_phase,
        "expected_value_class": "selection",
        "priority": 0,
    }


def _resolve_current_phase(plan: EngineeringPlan) -> str:
    if plan.input_strategy and plan.input_strategy.current_phase:
        return plan.input_strategy.current_phase
    active_phases = [phase for phase in plan.phases if phase.status == "active"]
    if active_phases:
        return active_phases[0].id
    if plan.phases:
        return plan.phases[0].id
    return ""


def _conditional_requirements_summary(
    requirements: dict[str, PlanRequirement],
) -> list[dict[str, Any]]:
    items = [
        req
        for req in requirements.values()
        if req.activation_status == "conditional" and req.status != "not_applicable"
    ]
    items.sort(key=lambda req: (_phase_order_index(req.phase), req.field))
    return [
        {
            "field": req.field,
            "title": req.resolved_title(),
            "phase": req.phase,
            "activation_condition": (
                req.activation_condition.to_dict() if req.activation_condition else None
            ),
        }
        for req in items
    ]


def _calculations_summary(requirements: dict[str, PlanRequirement]) -> list[dict[str, Any]]:
    calculations = [
        req
        for req in requirements.values()
        if req.requirement_class == "equation_result" and req.activation_status != "not_applicable"
    ]
    calculations.sort(key=lambda req: (_phase_order_index(req.phase), req.field))
    return [
        {
            "field": req.field,
            "title": req.resolved_title(),
            "depends_on": dependency_ids_to_fields(req.depends_on, requirements),
            "status": req.status,
        }
        for req in calculations
    ]


def _build_planner_graph_summary(plan: EngineeringPlan) -> dict[str, int]:
    """Planner-selected graph metrics from engineering plan graph and dependencies."""
    graph = plan.graph
    return {
        "selected_subgraph_count": len(graph.selected_subgraph_node_ids),
        "expanded_node_count": len(graph.expanded_node_ids),
        "dependency_edge_count": len(plan.dependencies),
        "branch_decision_count": len(graph.selected_branch_decisions),
    }


def _traversal_support(plan: EngineeringPlan) -> dict[str, str | None]:
    if plan.traversal is not None:
        return {"level": "full", "note": None}
    return {
        "level": "limited",
        "note": "Traversal state is unavailable for this engineering plan snapshot.",
    }


def _resolution_label(*, resolution_kind: str, awaiting_user_input: bool) -> str:
    if awaiting_user_input:
        return "User input required"
    if resolution_kind == "table_lookup":
        return "Lookup-derived"
    if resolution_kind == "equation_result":
        return "Calculation output"
    if resolution_kind == "conditional":
        return "Conditional — not user input"
    return "System-resolved"


def _split_phase_inputs(
    outstanding_required_inputs: list[dict[str, Any]],
    current_phase: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    current_phase_inputs: list[dict[str, Any]] = []
    future_phase_inputs: list[dict[str, Any]] = []
    current_index = _phase_order_index(current_phase)
    for entry in outstanding_required_inputs:
        entry_index = _phase_order_index(str(entry.get("phase") or ""))
        if entry_index <= current_index:
            current_phase_inputs.append(entry)
        else:
            future_phase_inputs.append(entry)
    return current_phase_inputs, future_phase_inputs


def _derive_status_badge(plan: EngineeringPlan, *, has_validation_errors: bool) -> str:
    if has_validation_errors:
        return "invalidated"
    root_status = plan.root_goal.status
    if root_status == "complete":
        return "completed"
    strategy = plan.input_strategy
    current_phase = _resolve_current_phase(plan)
    if current_phase in {"equation_execution", "validation", "reporting"}:
        if root_status == "ready":
            return "executing"
    if root_status == "ready":
        return "ready"
    if root_status == "blocked":
        if strategy and strategy.next_fields:
            return "waiting_for_input"
        return "blocked"
    if strategy and strategy.next_fields:
        return "waiting_for_input"
    return "blocked"


def _build_why_here(plan: EngineeringPlan) -> str | None:
    if plan.traversal and plan.traversal.current_active_node:
        return plan.traversal.current_active_node.reason or None
    strategy = plan.input_strategy
    if strategy and strategy.next_fields:
        field = strategy.next_fields[0]
        for req in plan.requirements.values():
            if not _requirement_matches_field(req, field):
                continue
            if req.question_spec and req.question_spec.reason_code:
                return str(req.question_spec.reason_code)
        return f"Next required field: {field.replace('_', ' ')}"
    return None


def _build_planner_header(
    plan: EngineeringPlan,
    *,
    current_phase: str,
    next_input: dict[str, Any] | None,
    has_validation_errors: bool,
) -> dict[str, Any]:
    traversal_summary = None
    active_node_id: str | None = None
    active_node_title: str | None = None
    if plan.traversal is not None:
        from engine.planner.planner_traversal import build_traversal_summary

        traversal_summary = build_traversal_summary(plan.traversal)
        active_node_id = traversal_summary.get("current_active_node_id")
        active_node_title = traversal_summary.get("current_active_node_title")

    next_action: dict[str, Any] | None = None
    if next_input:
        next_action = {
            "field": next_input.get("field"),
            "label": next_input.get("label"),
        }

    traversal_support = _traversal_support(plan)

    return {
        "workflow_id": plan.workflow_id,
        "workflow_name": plan.workflow_id.replace("_", " ").replace("-", " ").title(),
        "current_phase": current_phase,
        "current_phase_label": _PHASE_TITLES.get(current_phase, current_phase.replace("_", " ").title()),
        "current_active_node_id": active_node_id,
        "current_active_node_title": active_node_title,
        "next_action": next_action,
        "status_badge": _derive_status_badge(plan, has_validation_errors=has_validation_errors),
        "why_here": _build_why_here(plan),
        "traversal_support_level": traversal_support["level"],
        "traversal_support_note": traversal_support["note"],
    }


def _build_phase_panel(
    plan: EngineeringPlan,
    *,
    current_phase: str,
    next_input: dict[str, Any] | None,
    outstanding_required_inputs: list[dict[str, Any]],
) -> dict[str, Any]:
    strategy = plan.input_strategy
    resolved_fields = list(strategy.resolved_fields) if strategy else []
    active_field = next_input.get("field") if next_input else None

    missing_in_phase: list[dict[str, Any]] = []
    future_fields: list[dict[str, Any]] = []
    current_index = _phase_order_index(current_phase)

    for entry in outstanding_required_inputs:
        entry_phase = str(entry.get("phase") or "")
        if entry_phase == current_phase:
            if entry.get("field") != active_field:
                missing_in_phase.append(entry)
        elif _phase_order_index(entry_phase) > current_index:
            future_fields.append(entry)

    completed_fields: list[dict[str, Any]] = []
    for field in resolved_fields:
        for req in plan.requirements.values():
            if req.field != field:
                continue
            if req.phase != current_phase:
                continue
            label = field.replace("_", " ").title()
            if req.question_spec:
                label = req.question_spec.label
            completed_fields.append({"field": field, "label": label})
            break

    return {
        "current_phase": current_phase,
        "current_phase_label": _PHASE_TITLES.get(current_phase, current_phase.replace("_", " ").title()),
        "active_field": active_field,
        "completed_fields": completed_fields,
        "missing_in_phase": missing_in_phase,
        "future_fields": future_fields,
    }


def _requirement_display_status(req_status: str, activation_status: str) -> str:
    if activation_status == "not_applicable":
        return "not_applicable"
    if req_status == "resolved":
        return "satisfied"
    if req_status == "blocked":
        return "blocked"
    if req_status in {"missing", "ready"}:
        return "pending"
    return req_status


def _build_requirements_panel(
    plan: EngineeringPlan,
    *,
    conditional_requirements: list[dict[str, Any]],
    derived_or_lookup_values: list[dict[str, Any]],
    calculations: list[dict[str, Any]],
    system_resolved_requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item in conditional_requirements:
        rows.append(
            {
                "id": f"conditional-{item['field']}",
                "field": item["field"],
                "label": item["title"],
                "category": "conditional",
                "resolution_kind": "conditional",
                "display_status": "pending",
                "awaiting_user_input": False,
                "depends_on": [],
                "source_node_id": None,
                "phase": item.get("phase"),
            }
        )

    for item in derived_or_lookup_values:
        rows.append(
            {
                "id": item.get("id"),
                "field": item["field"],
                "label": item.get("title") or item["field"],
                "category": "lookup_derived",
                "resolution_kind": "table_lookup",
                "display_status": _requirement_display_status(
                    str(item.get("status") or "missing"),
                    str(item.get("activation_status") or "active"),
                ),
                "awaiting_user_input": False,
                "depends_on": list(item.get("depends_on") or []),
                "source_node_id": item.get("source_node_id"),
                "phase": None,
            }
        )

    for item in calculations:
        rows.append(
            {
                "id": f"calc-{item['field']}",
                "field": item["field"],
                "label": item["title"],
                "category": "calculation",
                "resolution_kind": "equation_result",
                "display_status": _requirement_display_status(str(item.get("status") or "missing"), "active"),
                "awaiting_user_input": False,
                "depends_on": list(item.get("depends_on") or []),
                "source_node_id": None,
                "phase": None,
            }
        )

    for item in system_resolved_requirements:
        req_class = str(item.get("requirement_class") or "")
        if req_class == "table_lookup":
            continue
        rows.append(
            {
                "id": item.get("id"),
                "field": item["field"],
                "label": item.get("title") or item["field"],
                "category": "system_resolved",
                "resolution_kind": req_class,
                "display_status": _requirement_display_status(
                    str(item.get("status") or "missing"),
                    str(item.get("activation_status") or "active"),
                ),
                "awaiting_user_input": False,
                "depends_on": list(item.get("depends_on") or []),
                "source_node_id": item.get("source_node_id"),
                "phase": item.get("phase"),
            }
        )

    for row in rows:
        row["resolution_label"] = _resolution_label(
            resolution_kind=str(row["resolution_kind"]),
            awaiting_user_input=bool(row["awaiting_user_input"]),
        )

    return rows


def build_planner_inspector_summary(plan: EngineeringPlan) -> dict[str, Any]:
    root = plan.root_goal
    requirements = plan.requirements

    seen_fields: set[str] = set()
    outstanding_candidates: list[PlanRequirement] = []
    for req in requirements.values():
        if not _is_outstanding_requirement(req):
            continue
        field = req.question_spec.field if req.question_spec else req.field
        if field in seen_fields:
            continue
        seen_fields.add(field)
        outstanding_candidates.append(req)

    outstanding_candidates.sort(
        key=lambda req: (
            _phase_order_index(req.phase),
            req.question_spec.priority if req.question_spec else 50,
            req.question_spec.field if req.question_spec else req.field,
        )
    )
    outstanding_required_inputs = [
        _input_entry_from_requirement(req) for req in outstanding_candidates
    ]

    next_input = _build_next_input(plan, requirements)

    alternatives: list[dict[str, Any]] = []
    for req in requirements.values():
        if not req.alternatives:
            continue
        alternatives.append(
            {
                "resolves": req.alternatives[0].resolves,
                "options": [
                    {
                        "id": alt.id,
                        "label": alt.label,
                        "fields": list(alt.fields),
                        "method": alt.method,
                    }
                    for alt in req.alternatives
                ],
            }
        )

    derived_or_lookup_values = _derived_or_lookup_summary(requirements)
    system_resolved_requirements = _system_resolved_requirement_summary(requirements)
    conditional_requirements = _conditional_requirements_summary(requirements)
    calculations = _calculations_summary(requirements)
    current_phase = _resolve_current_phase(plan)

    warnings = list((plan.debug or {}).get("validation_warnings") or [])
    errors = list((plan.debug or {}).get("validation_errors") or [])
    warnings.extend(errors)
    has_validation_errors = bool(errors)

    traversal_summary = None
    planner_traversal_view = None
    traversal_path: list[dict[str, Any]] = []
    if plan.traversal is not None:
        from engine.planner.planner_traversal import (
            build_planner_traversal_inspector_view,
            build_traversal_path_view,
            build_traversal_summary,
        )

        traversal_summary = build_traversal_summary(plan.traversal)
        planner_traversal_view = build_planner_traversal_inspector_view(plan.traversal)
        traversal_path = build_traversal_path_view(plan.traversal)

    current_phase_inputs, future_phase_inputs = _split_phase_inputs(
        outstanding_required_inputs,
        current_phase,
    )

    return {
        "root_goal": {
            "title": root.title,
            "target_field": root.target_field,
            "status": root.status,
        },
        "current_phase": current_phase,
        "next_input": next_input,
        "outstanding_required_inputs": outstanding_required_inputs,
        "current_phase_inputs": current_phase_inputs,
        "future_phase_inputs": future_phase_inputs,
        "conditional_requirements": conditional_requirements,
        "alternatives": alternatives,
        "derived_or_lookup_values": derived_or_lookup_values,
        "calculations": calculations,
        "system_resolved_requirements": system_resolved_requirements,
        "planner_graph_summary": _build_planner_graph_summary(plan),
        "traversal_summary": traversal_summary,
        "planner_traversal_view": planner_traversal_view,
        "traversal_path": traversal_path,
        "header": _build_planner_header(
            plan,
            current_phase=current_phase,
            next_input=next_input,
            has_validation_errors=has_validation_errors,
        ),
        "phase_panel": _build_phase_panel(
            plan,
            current_phase=current_phase,
            next_input=next_input,
            outstanding_required_inputs=outstanding_required_inputs,
        ),
        "requirements_panel": _build_requirements_panel(
            plan,
            conditional_requirements=conditional_requirements,
            derived_or_lookup_values=derived_or_lookup_values,
            calculations=calculations,
            system_resolved_requirements=system_resolved_requirements,
        ),
        "warnings": warnings,
    }


def dependency_ids_to_fields(
    requirement_ids: list[str],
    requirements: dict[str, PlanRequirement],
) -> list[str]:
    """Map requirement dependency ids to output field names, preserving order."""
    fields: list[str] = []
    seen: set[str] = set()
    for requirement_id in requirement_ids:
        dep = requirements.get(requirement_id)
        if dep is None:
            continue
        field = dep.field
        if field in seen:
            continue
        seen.add(field)
        fields.append(field)
    return fields


def _lookup_summary_method(req: PlanRequirement) -> str:
    resolution = req.resolution or {}
    method = str(resolution.get("method") or "lookup")
    if req.id == "REQ-outside_diameter_lookup":
        return "lookup_if_nps_selected"
    if req.field == "weld_joint_strength_reduction_factor_W":
        return "lookup_or_default"
    return method


def _derived_or_lookup_summary(requirements: dict[str, PlanRequirement]) -> list[dict[str, Any]]:
    lookup_reqs = [
        req
        for req in requirements.values()
        if req.requirement_class == "table_lookup" and req.activation_status != "not_applicable"
    ]
    lookup_reqs.sort(key=lambda req: (req.phase, req.field))

    entries: list[dict[str, Any]] = []
    for req in lookup_reqs:
        resolution = req.resolution or {}
        entry: dict[str, Any] = {
            "id": req.id,
            "field": req.field,
            "title": req.resolved_title(),
            "method": _lookup_summary_method(req),
            "depends_on": dependency_ids_to_fields(req.depends_on, requirements),
            "status": req.status,
        }
        source_node_id = resolution.get("source_node_id")
        if source_node_id:
            entry["source_node_id"] = source_node_id
        if req.activation_status != "active":
            entry["activation_status"] = req.activation_status
        entries.append(entry)
    return entries


def _system_resolved_requirement_summary(
    requirements: dict[str, PlanRequirement],
) -> list[dict[str, Any]]:
    """Lookup, equation, and report requirements for planner inspector."""
    resolved_reqs = [
        req
        for req in requirements.values()
        if req.requirement_class in _SYSTEM_RESOLVED_CLASSES
        and req.activation_status != "not_applicable"
    ]
    resolved_reqs.sort(key=lambda req: (_phase_order_index(req.phase), req.field))

    entries: list[dict[str, Any]] = []
    for req in resolved_reqs:
        resolution = req.resolution or {}
        entry: dict[str, Any] = {
            "id": req.id,
            "field": req.field,
            "title": req.resolved_title(),
            "requirement_class": req.requirement_class,
            "method": str(resolution.get("method") or req.requirement_class),
            "depends_on": dependency_ids_to_fields(req.depends_on, requirements),
            "status": req.status,
            "phase": req.phase,
        }
        source_node_id = resolution.get("source_node_id")
        if source_node_id:
            entry["source_node_id"] = source_node_id
        if req.activation_status != "active":
            entry["activation_status"] = req.activation_status
        entries.append(entry)
    return entries


def build_engineering_plan_view(plan: EngineeringPlan) -> dict[str, Any]:
    """Human-readable engineering plan for task state and inspector UI."""
    requirements = plan.requirements
    field_by_id = {rid: req.field for rid, req in requirements.items()}

    def resolve_depends_on(req: PlanRequirement) -> list[str]:
        return [
            field_by_id[dep_id]
            for dep_id in req.depends_on
            if dep_id in field_by_id
        ]

    def requirement_entry(req: PlanRequirement) -> dict[str, Any]:
        label = req.resolved_title()
        if label == req.field.replace("_", " ").title() and req.question_spec and req.question_spec.label:
            label = req.question_spec.label
        entry: dict[str, Any] = {
            "field": req.field,
            "label": label,
            "kind": _REQUIREMENT_CLASS_LABELS.get(req.requirement_class, req.requirement_class),
            "status": req.status,
            "status_label": _STATUS_LABELS.get(req.status, req.status.replace("_", " ").title()),
        }
        depends = resolve_depends_on(req)
        if depends:
            entry["depends_on"] = depends
        if req.alternatives:
            entry["alternatives"] = [
                {
                    "label": alt.label,
                    "method": alt.method.replace("_", " "),
                    "fields": list(alt.fields),
                }
                for alt in req.alternatives
            ]
        if req.activation_status != "active":
            entry["activation_status"] = req.activation_status
        if req.activation_condition is not None:
            entry["activation_condition"] = req.activation_condition.to_dict()
        return entry

    phases: list[dict[str, Any]] = []
    for phase in sorted(plan.phases, key=lambda item: item.order):
        phase_reqs = [
            requirements[rid]
            for rid in phase.requirement_ids
            if rid in requirements and requirements[rid].status != "not_applicable"
        ]
        if not phase_reqs:
            continue
        phases.append(
            {
                "id": phase.id,
                "title": phase.title or _PHASE_TITLES.get(phase.id, phase.id.replace("_", " ").title()),
                "status": phase.status,
                "status_label": _STATUS_LABELS.get(phase.status, phase.status.replace("_", " ").title()),
                "requirements": [requirement_entry(req) for req in phase_reqs],
            }
        )

    branch_decisions = [
        {
            "field": decision.field,
            "value": decision.value.replace("_", " "),
            "selected_node": decision.selected_node,
        }
        for decision in plan.graph.selected_branch_decisions
    ]

    input_strategy = plan.input_strategy
    current_phase_id = input_strategy.current_phase if input_strategy else None
    if plan.phases:
        active_phases = [p for p in plan.phases if p.status == "active"]
        if active_phases:
            current_phase_id = active_phases[0].id
        elif current_phase_id is None:
            current_phase_id = plan.phases[0].id

    next_input: dict[str, Any] | None = None
    if input_strategy and input_strategy.next_fields:
        field = input_strategy.next_fields[0]
        for req in requirements.values():
            if req.field == field and req.question_spec:
                next_input = {
                    "field": field,
                    "label": req.question_spec.label,
                }
                break
        if next_input is None:
            next_input = {"field": field, "label": field.replace("_", " ").title()}

    resolved = sum(1 for req in requirements.values() if req.status == "resolved")
    needed = sum(
        1
        for req in requirements.values()
        if req.status in {"missing", "ready", "blocked"} and req.status != "not_applicable"
    )

    calculations = [
        requirement_entry(req)
        for req in requirements.values()
        if req.requirement_class == "equation_result" and req.status != "not_applicable"
    ]

    reports = [
        requirement_entry(req)
        for req in requirements.values()
        if req.requirement_class == "report_output" and req.status != "not_applicable"
    ]

    overview: dict[str, Any] = {
        "goal": plan.root_goal.title,
        "target": plan.root_goal.target_field,
        "goal_status": plan.root_goal.status,
        "goal_status_label": _STATUS_LABELS.get(plan.root_goal.status, plan.root_goal.status),
        "workflow_id": plan.workflow_id,
        "current_phase": _PHASE_TITLES.get(current_phase_id or "", current_phase_id),
        "resolved_count": resolved,
        "remaining_count": needed,
    }
    if next_input:
        overview["next_input"] = next_input

    payload: dict[str, Any] = {
        "overview": overview,
        "phases": phases,
        "calculations": calculations,
    }
    if reports:
        payload["reports"] = reports
    if branch_decisions:
        payload["branch_decisions"] = branch_decisions
    if plan.input_strategy:
        payload["input_strategy"] = {
            "mode": plan.input_strategy.mode.replace("_", " "),
            "resolved_fields": list(plan.input_strategy.resolved_fields),
            "blocked_fields": list(plan.input_strategy.blocked_fields),
            "next_fields": list(plan.input_strategy.next_fields),
        }
    warnings = list((plan.debug or {}).get("validation_warnings") or [])
    warnings.extend(list((plan.debug or {}).get("validation_errors") or []))
    if warnings:
        payload["warnings"] = warnings
    return payload


def build_planner_inspector_summary_from_dict(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Rebuild planner inspector summary from canonical engineering_plan dict."""
    plan = engineering_plan_from_dict(raw)
    if plan is None:
        return None
    return build_planner_inspector_summary(plan)


def planner_inspector_summary_for_task(task) -> dict[str, Any] | None:
    """Inspector summary derived from engineering_plan (canonical source of truth)."""
    raw = task.outputs.get("engineering_plan")
    if isinstance(raw, dict) and "requirements" in raw and "root_goal" in raw:
        summary = build_planner_inspector_summary_from_dict(raw)
        if summary is not None:
            return summary
    cached = task.outputs.get("planner_inspector_summary")
    if isinstance(cached, dict):
        return dict(cached)
    return None


def engineering_plan_from_dict(raw: dict[str, Any]) -> EngineeringPlan | None:
    """Rehydrate EngineeringPlan from persisted task output dict."""
    if not raw or "plan_id" not in raw or "requirements" not in raw or "root_goal" not in raw:
        return None
    try:
        from models.engineering_plan import (
            ActivationCondition,
            BranchDecision,
            CalculationGoal,
            InputStrategy,
            PlanDependency,
            PlanGraph,
            PlanPhase,
            PlanRequirement,
            PlannerTraversalState,
            QuestionSpec,
            RequirementAlternative,
            TraversalActiveNode,
            TraversalBranchDecision,
            TraversalEvent,
            TraversalExpandedNode,
            TraversalPendingNode,
        )

        root_raw = raw.get("root_goal") or {}
        root = CalculationGoal(
            id=str(root_raw.get("id", "")),
            key=str(root_raw.get("key", "")),
            title=str(root_raw.get("title", "")),
            target_parameter=str(root_raw.get("target_parameter", "")),
            target_field=str(root_raw.get("target_field", "")),
            status=str(root_raw.get("status", "blocked")),
            blocked_by=list(root_raw.get("blocked_by") or []),
            provisional_blocked_by=list(root_raw.get("provisional_blocked_by") or []),
            required_outputs=list(root_raw.get("required_outputs") or []),
        )

        requirements: dict[str, PlanRequirement] = {}
        for rid, req_raw in (raw.get("requirements") or {}).items():
            if not isinstance(req_raw, dict):
                continue
            qspec_raw = req_raw.get("question_spec")
            qspec = None
            if isinstance(qspec_raw, dict):
                qspec = QuestionSpec(
                    field=str(qspec_raw.get("field", "")),
                    label=str(qspec_raw.get("label", "")),
                    expected_value_class=str(qspec_raw.get("expected_value_class", "")),
                    priority=int(qspec_raw.get("priority") or 0),
                    ask_policy=str(qspec_raw.get("ask_policy", "")),
                    reason_code=qspec_raw.get("reason_code"),
                    allowed_units=qspec_raw.get("allowed_units"),
                    options_source=qspec_raw.get("options_source"),
                )
            alts_raw = req_raw.get("alternatives") or []
            alternatives = [
                RequirementAlternative(
                    id=str(alt.get("id", "")),
                    label=str(alt.get("label", "")),
                    fields=list(alt.get("fields") or []),
                    resolves=str(alt.get("resolves", "")),
                    method=str(alt.get("method", "")),
                )
                for alt in alts_raw
                if isinstance(alt, dict)
            ] or None
            activation_raw = req_raw.get("activation_condition")
            activation_condition = None
            if isinstance(activation_raw, dict):
                activation_condition = ActivationCondition(
                    field=str(activation_raw.get("field", "")),
                    operator=str(activation_raw.get("operator", "")),
                    value=activation_raw.get("value", ""),
                )
            requirements[str(rid)] = PlanRequirement(
                id=str(rid),
                field=str(req_raw.get("field", "")),
                key=str(req_raw.get("key", "") or req_raw.get("field", "")),
                title=str(req_raw.get("title", "") or ""),
                parameter_node_id=req_raw.get("parameter_node_id"),
                requirement_class=str(req_raw.get("requirement_class", "")),
                status=str(req_raw.get("status", "")),
                phase=str(req_raw.get("phase", "")),
                required_by=list(req_raw.get("required_by") or []),
                depends_on=list(req_raw.get("depends_on") or []),
                alternatives=alternatives,
                question_spec=qspec,
                resolution=req_raw.get("resolution"),
                activation_condition=activation_condition,
                activation_status=str(req_raw.get("activation_status") or "active"),
            )

        graph_raw = raw.get("graph") or {}
        graph = PlanGraph(
            selected_subgraph_node_ids=list(graph_raw.get("selected_subgraph_node_ids") or []),
            selected_branch_decisions=[
                BranchDecision(
                    field=str(item.get("field", "")),
                    value=str(item.get("value", "")),
                    selected_node=str(item.get("selected_node", "")),
                )
                for item in (graph_raw.get("selected_branch_decisions") or [])
                if isinstance(item, dict)
            ],
            expanded_node_ids=list(graph_raw.get("expanded_node_ids") or []),
        )

        dependencies = [
            PlanDependency(
                from_id=str(edge.get("from", "")),
                to_id=str(edge.get("to", "")),
                type=str(edge.get("type", "")),
            )
            for edge in (raw.get("dependencies") or [])
            if isinstance(edge, dict)
        ]

        phases = [
            PlanPhase(
                id=str(phase.get("id", "")),
                title=str(phase.get("title", "")),
                order=int(phase.get("order") or 0),
                requirement_ids=list(phase.get("requirement_ids") or []),
                status=str(phase.get("status", "pending")),
            )
            for phase in (raw.get("phases") or [])
            if isinstance(phase, dict)
        ]

        strategy_raw = raw.get("input_strategy")
        input_strategy = None
        if isinstance(strategy_raw, dict):
            input_strategy = InputStrategy(
                mode=str(strategy_raw.get("mode", "")),
                current_phase=str(strategy_raw.get("current_phase", "")),
                next_fields=list(strategy_raw.get("next_fields") or []),
                blocked_fields=list(strategy_raw.get("blocked_fields") or []),
                resolved_fields=list(strategy_raw.get("resolved_fields") or []),
            )

        traversal_raw = raw.get("traversal")
        traversal = None
        if isinstance(traversal_raw, dict):
            active_raw = traversal_raw.get("current_active_node")
            current_active_node = None
            if isinstance(active_raw, dict):
                current_active_node = TraversalActiveNode(
                    node_id=str(active_raw.get("node_id", "")),
                    node_type=str(active_raw.get("node_type", "")),
                    reason=str(active_raw.get("reason", "")),
                    title=active_raw.get("title"),
                    phase=active_raw.get("phase"),
                )
            pending_expansion_nodes = [
                TraversalPendingNode(
                    node_id=str(item.get("node_id", "")),
                    node_type=str(item.get("node_type", "")),
                    waiting_on=list(item.get("waiting_on") or []),
                    reason=str(item.get("reason", "")),
                    title=item.get("title"),
                    phase=item.get("phase"),
                )
                for item in (traversal_raw.get("pending_expansion_nodes") or [])
                if isinstance(item, dict)
            ]
            expanded_nodes = [
                TraversalExpandedNode(
                    node_id=str(item.get("node_id", "")),
                    node_type=str(item.get("node_type", "")),
                    expanded_at_order=int(item.get("expanded_at_order") or 0),
                    produced_requirements=list(item.get("produced_requirements") or []),
                    produced_edges=list(item.get("produced_edges") or []),
                    title=item.get("title"),
                )
                for item in (traversal_raw.get("expanded_nodes") or [])
                if isinstance(item, dict)
            ]
            branch_decisions = [
                TraversalBranchDecision(
                    field=str(item.get("field", "")),
                    value=item.get("value"),
                    selected_node=item.get("selected_node"),
                    candidate_nodes=list(item.get("candidate_nodes") or []),
                    status=str(item.get("status", "")),
                )
                for item in (traversal_raw.get("branch_decisions") or [])
                if isinstance(item, dict)
            ]
            traversal_events = [
                TraversalEvent(
                    order=int(item.get("order") or 0),
                    event_type=str(item.get("event_type", "")),
                    message=str(item.get("message", "")),
                    node_id=item.get("node_id"),
                    requirement_id=item.get("requirement_id"),
                    edge_id=item.get("edge_id"),
                )
                for item in (traversal_raw.get("traversal_events") or [])
                if isinstance(item, dict)
            ]
            traversal = PlannerTraversalState(
                traversal_id=str(traversal_raw.get("traversal_id", "")),
                current_active_node_id=traversal_raw.get("current_active_node_id"),
                current_active_node=current_active_node,
                pending_expansion_nodes=pending_expansion_nodes,
                expanded_nodes=expanded_nodes,
                branch_decisions=branch_decisions,
                traversal_events=traversal_events,
            )

        return EngineeringPlan(
            plan_id=str(raw.get("plan_id", "")),
            task_id=str(raw.get("task_id", "")),
            workflow_id=str(raw.get("workflow_id", "")),
            root_goal=root,
            requirements=requirements,
            dependencies=dependencies,
            input_strategy=input_strategy,
            graph=graph,
            phases=phases,
            traversal=traversal,
            legacy_goal_map=raw.get("legacy_goal_map"),
            debug=raw.get("debug"),
        )
    except Exception:
        return None


def build_engineering_plan_view_from_dict(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Rebuild readable plan view from persisted plan dict (e.g. on task reload)."""
    plan = engineering_plan_from_dict(raw)
    if plan is None:
        return None
    return build_engineering_plan_view(plan)


def engineering_plan_view_for_task(task) -> dict[str, Any] | None:
    """Readable engineering plan view from task outputs."""
    view = task.outputs.get("engineering_plan_view")
    if isinstance(view, dict):
        return view
    raw = task.outputs.get("engineering_plan")
    if isinstance(raw, dict):
        return build_engineering_plan_view_from_dict(raw)
    return None


def canonical_engineering_plan_for_task(task) -> dict[str, Any] | None:
    """Normalized EngineeringPlan dict (source of truth) from task outputs."""
    raw = task.outputs.get("engineering_plan")
    if not isinstance(raw, dict):
        return None
    if "plan_id" not in raw or "requirements" not in raw or "root_goal" not in raw:
        return None
    return dict(raw)
