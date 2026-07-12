"""Workflow-agnostic engineering plan assembly from graph planning state."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.expansion_traversal_trace import load_expansion_trace
from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id
from engine.graph.navigation_phases import PhasedNavigation
from engine.planner.activation_conditions import resolve_activation_status
from engine.planner.graph_requirements import (
    apply_alternative_resolution_statuses,
    build_graph_requirements,
    required_outputs_for_plan,
    synthesize_planning_facts,
    _preview_too_shallow,
)
from engine.planner.plan_dependencies import build_plan_dependencies
from engine.planner.plan_phases import build_plan_phases_and_strategy
from engine.planner.plan_validation import validate_engineering_plan
from engine.planner.planner_traversal import build_planner_traversal_state
from engine.planner.question_spec_builder import build_question_spec
from engine.planner.tools import GraphTools
from engine.planner.workflow_goal_metadata import (
    lookup_fields_for_workflow,
    resolve_root_goal_spec,
    selection_fields_for_workflow,
)
from engine.reference.parameter_keys import canonical_parameter_key, param_node_id_for_input, parameter_is_ready
from engine.reference.standards_reader import StandardsReader
from models.engineering_plan import (
    BranchDecision,
    CalculationGoal,
    EngineeringPlan,
    PlanGraph,
    PlanRequirement,
    new_plan_id,
)
from models.fact import Fact
from models.task import Task

_GATE_PHASES = frozenset({"expansion_assumptions", "path_decisions"})


def _requirement_id(field: str) -> str:
    return f"REQ-{field}"


def _requirement_class_for_field(
    field: str,
    *,
    selection_fields: frozenset[str],
    lookup_fields: frozenset[str],
) -> str:
    if field in selection_fields:
        return "branch_decision"
    if field in lookup_fields:
        return "table_lookup"
    return "user_input"


def _phase_for_field(field: str, phased: PhasedNavigation | None) -> str:
    if phased is not None:
        for phase, fields in phased.phase_missing.items():
            if field in fields:
                return phase
        for phase, fields in phased.phase_questions.items():
            if field in fields:
                return phase
    return "parameter_gathering"


def _collect_planning_fields(
    *,
    phased: PhasedNavigation | None,
    missing_inputs: list[str] | None,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    if phased is not None:
        for field in phased.all_missing:
            if field not in seen:
                ordered.append(field)
                seen.add(field)
        for fields in phased.phase_missing.values():
            for field in fields:
                if field not in seen:
                    ordered.append(field)
                    seen.add(field)
    for field in missing_inputs or []:
        if field not in seen:
            ordered.append(field)
            seen.add(field)
    return ordered


def build_generic_requirements(
    *,
    reader: StandardsReader,
    workflow_id: str,
    root_goal_id: str,
    phased: PhasedNavigation | None,
    missing_inputs: list[str] | None = None,
) -> dict[str, PlanRequirement]:
    selection_fields = selection_fields_for_workflow(reader, workflow_id)
    lookup_fields = lookup_fields_for_workflow(reader, workflow_id)
    requirements: dict[str, PlanRequirement] = {}

    for field in _collect_planning_fields(phased=phased, missing_inputs=missing_inputs):
        requirement_class = _requirement_class_for_field(
            field,
            selection_fields=selection_fields,
            lookup_fields=lookup_fields,
        )
        phase = _phase_for_field(field, phased)
        param_node_id = param_node_id_for_input(field)
        requirements[_requirement_id(field)] = PlanRequirement(
            id=_requirement_id(field),
            field=field,
            parameter_node_id=param_node_id,
            requirement_class=requirement_class,
            status="missing",
            phase=phase,
            required_by=[root_goal_id],
            depends_on=[],
            question_spec=build_question_spec(field),
        )

    return requirements


def _depends_on_unresolved(
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


def apply_generic_requirement_statuses(
    requirements: dict[str, PlanRequirement],
    *,
    existing_inputs: dict[str, Fact],
) -> None:
    for req in requirements.values():
        req.activation_status = resolve_activation_status(req, existing_inputs)
        if req.activation_status == "not_applicable":
            req.status = "not_applicable"
            continue

        field = canonical_parameter_key(req.field)
        if req.requirement_class in {"user_input", "branch_decision"}:
            req.status = "resolved" if parameter_is_ready(existing_inputs, field) else "missing"
            continue

        if req.requirement_class == "table_lookup":
            if parameter_is_ready(existing_inputs, field):
                req.status = "resolved"
            elif _depends_on_unresolved(req, requirements):
                req.status = "blocked"
            else:
                req.status = "ready"
            continue

        if req.requirement_class in {"equation_result", "derived_value", "validation_check", "report_output"}:
            if parameter_is_ready(existing_inputs, field):
                req.status = "resolved"
            elif _depends_on_unresolved(req, requirements):
                req.status = "blocked"
            else:
                req.status = "missing"
            continue

        req.status = "resolved" if parameter_is_ready(existing_inputs, field) else "missing"


def _gate_requirement_ids(requirements: dict[str, PlanRequirement]) -> frozenset[str]:
    return frozenset(
        req.id
        for req in requirements.values()
        if req.phase in _GATE_PHASES
        and req.requirement_class in {"user_input", "branch_decision"}
    )


def _compute_root_blocking(
    requirements: dict[str, PlanRequirement],
    *,
    gate_requirement_ids: frozenset[str],
) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    provisional: list[str] = []

    for requirement_id, req in requirements.items():
        if req.status in {"resolved", "not_applicable"}:
            continue
        if req.activation_status == "not_applicable":
            continue
        if req.status not in {"missing", "blocked", "ready"}:
            continue

        if requirement_id in gate_requirement_ids:
            hard.append(requirement_id)
            continue

        if req.activation_status == "conditional":
            provisional.append(requirement_id)
            continue

        hard.append(requirement_id)

    return hard, provisional


def _branch_decisions(path_decision: dict[str, str] | None) -> list[BranchDecision]:
    if not path_decision:
        return []
    field = str(path_decision.get("field") or "")
    value = str(path_decision.get("value") or "")
    selected_node = str(path_decision.get("selected_node") or "")
    if not field:
        return []
    return [BranchDecision(field=field, value=value, selected_node=selected_node)]


def _resolve_missing_inputs(
    reader: StandardsReader,
    workflow_id: str,
    *,
    existing_inputs: dict[str, Fact],
    preview: Any | None,
) -> list[str]:
    slug = normalize_root_id(workflow_id)
    graph = GraphTools(reader)
    return list(
        graph.required_user_inputs(
            slug,
            existing_inputs=set(existing_inputs.keys()),
            task_inputs=existing_inputs,
            plan=preview,
        )
    )


def build_generic_engineering_plan(
    task: Task,
    reader: StandardsReader,
    *,
    preview: Any | None = None,
    phased: PhasedNavigation | None = None,
    existing_inputs: dict[str, Fact] | None = None,
    path_decision: dict[str, str] | None = None,
) -> EngineeringPlan | None:
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()
    if not workflow_id:
        return None

    inputs = dict(existing_inputs or task.fact_store.active_facts())
    slug = normalize_root_id(workflow_id)

    if preview is None:
        graph = GraphTools(reader)
        engine = GraphEngine()
        lazy_plan = engine.uses_micro_graph(reader, slug) and not engine.expansion_gate_ready(
            slug,
            reader,
            existing_inputs=inputs,
        )
        preview = graph.preview_plan(
            task_id=task.task_id,
            root_id=slug,
            inputs=inputs,
            lazy=lazy_plan,
        )

    discovery_inputs = synthesize_planning_facts(
        reader,
        workflow_id,
        inputs,
        task_id=task.task_id,
    )
    discovery_preview = preview
    if _preview_too_shallow(preview):
        graph = GraphTools(reader)
        discovery_preview = graph.preview_plan(
            task_id=task.task_id,
            root_id=slug,
            inputs=discovery_inputs,
            lazy=False,
        )

    root_spec = resolve_root_goal_spec(reader, workflow_id)
    missing_inputs = _resolve_missing_inputs(reader, workflow_id, existing_inputs=inputs, preview=preview)
    requirements = build_graph_requirements(
        reader=reader,
        workflow_id=workflow_id,
        root_goal_id=root_spec.id,
        preview=discovery_preview,
        phased=phased,
        missing_inputs=missing_inputs,
        target_field=root_spec.target_field,
        planning_inputs=discovery_inputs,
    )
    if not requirements:
        return None

    apply_generic_requirement_statuses(requirements, existing_inputs=inputs)
    apply_alternative_resolution_statuses(requirements, existing_inputs=inputs)

    root = CalculationGoal(
        id=root_spec.id,
        key=root_spec.key,
        title=root_spec.title,
        target_parameter=root_spec.target_parameter,
        target_field=root_spec.target_field,
        status="blocked",
        blocked_by=[],
        provisional_blocked_by=[],
        required_outputs=required_outputs_for_plan(
            requirements,
            target_field=root_spec.target_field,
            has_report="REQ-calculation_report" in requirements,
        ),
    )
    gate_ids = _gate_requirement_ids(requirements)
    hard_blocked, provisional_blocked = _compute_root_blocking(requirements, gate_requirement_ids=gate_ids)
    root.blocked_by = hard_blocked
    root.provisional_blocked_by = provisional_blocked
    if not hard_blocked and not provisional_blocked:
        root.status = "ready"

    execution_order = list(getattr(preview, "execution_order", ()) or [])
    expanded = list(getattr(preview, "expanded_nodes", ()) or execution_order)

    phases, input_strategy = build_plan_phases_and_strategy(requirements, known_facts=inputs)
    plan_id = new_plan_id()
    graph = PlanGraph(
        selected_subgraph_node_ids=execution_order,
        selected_branch_decisions=_branch_decisions(path_decision),
        expanded_node_ids=expanded,
    )
    traversal = build_planner_traversal_state(
        plan_id=plan_id,
        workflow_id=workflow_id,
        requirements=requirements,
        input_strategy=input_strategy,
        graph=graph,
        path_decision=path_decision,
        existing_inputs=inputs,
        reader=reader,
        preview=preview,
        expansion_trace=load_expansion_trace(task.outputs),
    )

    plan = EngineeringPlan(
        plan_id=plan_id,
        task_id=task.task_id,
        workflow_id=workflow_id,
        root_goal=root,
        requirements=requirements,
        dependencies=build_plan_dependencies(requirements, workflow_id=workflow_id),
        input_strategy=input_strategy,
        graph=graph,
        phases=phases,
        traversal=traversal,
    )

    from engine.planner.legacy_goal_adapter import finalize_engineering_plan

    plan = finalize_engineering_plan(plan)
    validation = validate_engineering_plan(plan)
    if validation.warnings or validation.errors:
        plan.debug = {
            "validation_warnings": list(validation.warnings),
            "validation_errors": list(validation.errors),
            "source": "plan_validation",
        }

    return plan


def branch_value_from_inputs(field: str, inputs: dict[str, Any]) -> str | None:
    raw = field_value(field, inputs)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None
