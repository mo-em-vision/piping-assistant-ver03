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
    "selection_goal": "Selection",
}

_PHASE_ORDER = (
    "expansion_assumptions",
    "path_decisions",
    "parameter_gathering",
    "coefficient_resolution",
    "execution_assumptions",
    "definition_equation_completion",
)


def _phase_order_index(phase: str) -> int:
    try:
        return _PHASE_ORDER.index(phase)
    except ValueError:
        return len(_PHASE_ORDER)


def _is_outstanding_requirement(req: PlanRequirement) -> bool:
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


def _build_planner_graph_summary(plan: EngineeringPlan) -> dict[str, int]:
    """Planner-selected graph metrics from engineering plan graph and dependencies."""
    graph = plan.graph
    return {
        "selected_subgraph_count": len(graph.selected_subgraph_node_ids),
        "expanded_node_count": len(graph.expanded_node_ids),
        "dependency_edge_count": len(plan.dependencies),
        "branch_decision_count": len(graph.selected_branch_decisions),
    }


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

    warnings = list((plan.debug or {}).get("validation_warnings") or [])
    errors = list((plan.debug or {}).get("validation_errors") or [])
    warnings.extend(errors)

    traversal_summary = None
    planner_traversal_view = None
    if plan.traversal is not None:
        from engine.planner.planner_traversal import (
            build_planner_traversal_inspector_view,
            build_traversal_summary,
        )

        traversal_summary = build_traversal_summary(plan.traversal)
        planner_traversal_view = build_planner_traversal_inspector_view(plan.traversal)

    return {
        "root_goal": {
            "title": root.title,
            "target_field": root.target_field,
            "status": root.status,
        },
        "next_input": next_input,
        "outstanding_required_inputs": outstanding_required_inputs,
        "alternatives": alternatives,
        "derived_or_lookup_values": derived_or_lookup_values,
        "planner_graph_summary": _build_planner_graph_summary(plan),
        "traversal_summary": traversal_summary,
        "planner_traversal_view": planner_traversal_view,
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
    if req.id == "REQ-weld_strength_reduction_factor_W_lookup":
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
        entries.append(
            {
                "field": req.field,
                "method": _lookup_summary_method(req),
                "depends_on": dependency_ids_to_fields(req.depends_on, requirements),
                "status": req.status,
            }
        )
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
        label = req.field.replace("_", " ").title()
        if req.question_spec and req.question_spec.label:
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


def build_engineering_plan_view_from_dict(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Rebuild readable plan view from persisted plan dict (e.g. on task reload)."""
    if not raw:
        return None
    try:
        from models.engineering_plan import (
            ActivationCondition,
            BranchDecision,
            CalculationGoal,
            InputStrategy,
            PlanGraph,
            PlanPhase,
            PlanRequirement,
            QuestionSpec,
            RequirementAlternative,
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
                parameter_node_id=str(req_raw.get("parameter_node_id", "")),
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

        plan = EngineeringPlan(
            plan_id=str(raw.get("plan_id", "")),
            task_id=str(raw.get("task_id", "")),
            workflow_id=str(raw.get("workflow_id", "")),
            root_goal=root,
            requirements=requirements,
            dependencies=[],
            input_strategy=input_strategy,
            graph=graph,
            phases=phases,
            debug=raw.get("debug"),
        )
        return build_engineering_plan_view(plan)
    except Exception:
        return None


def engineering_plan_view_for_task(task) -> dict[str, Any] | None:
    """Readable engineering plan view from task outputs."""
    view = task.outputs.get("engineering_plan_view")
    if isinstance(view, dict):
        return view
    raw = task.outputs.get("engineering_plan")
    if isinstance(raw, dict):
        return build_engineering_plan_view_from_dict(raw)
    return None
