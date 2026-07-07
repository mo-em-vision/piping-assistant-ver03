"""Build normalized EngineeringPlan objects from graph planning state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.navigation_phases import PhasedNavigation
from engine.graph.workflow_navigation import WorkflowNavigationConfig
from engine.planner.activation_conditions import resolve_activation_status
from engine.planner.pipe_wall_plan import (
    PIPE_WALL_WORKFLOW,
    build_pipe_wall_requirements,
    req_id,
    root_calculation_goal,
)
from engine.planner.workflow_goal_metadata import resolve_root_goal_spec
from engine.planner.plan_dependencies import build_plan_dependencies
from engine.planner.plan_phases import build_plan_phases_and_strategy
from engine.planner.plan_validation import validate_engineering_plan
from engine.planner.planner_traversal import build_planner_traversal_state
from engine.reference.parameter_keys import canonical_parameter_key, parameter_is_ready
from engine.reference.standards_reader import StandardsReader
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.engineering_plan import (
    BranchDecision,
    EngineeringPlan,
    PlanGraph,
    PlanRequirement,
    new_plan_id,
)
from models.fact import Fact
from models.task import Task


def _diameter_mode(existing_inputs: dict[str, Fact]) -> str | None:
    mode = field_value("d_input_mode", existing_inputs)
    if mode in {"direct_od", "nps_lookup", "direct_id"}:
        return str(mode)
    if parameter_is_ready(existing_inputs, "outside_diameter"):
        return "direct_od"
    if parameter_is_ready(existing_inputs, "nominal_pipe_size"):
        return "nps_lookup"
    if parameter_is_ready(existing_inputs, "inside_diameter"):
        return "direct_id"
    return None


def _requirement_status(
    requirement_id: str,
    *,
    existing_inputs: dict[str, Fact],
    requirements: dict,
    diameter_mode: str | None,
) -> str:
    req = requirements[requirement_id]
    field = req.field

    if requirement_id == "REQ-diameter_resolution":
        if diameter_mode == "direct_od" and parameter_is_ready(existing_inputs, "outside_diameter"):
            return "resolved"
        if diameter_mode == "nps_lookup":
            if parameter_is_ready(existing_inputs, "outside_diameter"):
                return "resolved"
            if parameter_is_ready(existing_inputs, "nominal_pipe_size"):
                return "blocked"
        if diameter_mode == "direct_id" and parameter_is_ready(existing_inputs, "inside_diameter"):
            return "resolved"
        return "missing"

    if requirement_id == "REQ-outside_diameter_lookup":
        if diameter_mode != "nps_lookup":
            return "not_applicable"
        if parameter_is_ready(existing_inputs, "outside_diameter"):
            return "resolved"
        if not parameter_is_ready(existing_inputs, "nominal_pipe_size"):
            return "blocked"
        return "ready"

    if requirement_id == req_id("nominal_pipe_size"):
        if diameter_mode == "direct_od":
            return "not_applicable"
        if parameter_is_ready(existing_inputs, "nominal_pipe_size"):
            return "resolved"
        if diameter_mode == "nps_lookup":
            return "missing"
        return "not_applicable"

    if req.requirement_class in {"table_lookup", "equation_result", "report_output"}:
        if parameter_is_ready(existing_inputs, field):
            return "resolved"
        for dep in req.depends_on:
            dep_status = _requirement_status(
                dep,
                existing_inputs=existing_inputs,
                requirements=requirements,
                diameter_mode=diameter_mode,
            )
            if dep_status not in {"resolved", "not_applicable"}:
                return "blocked"
        return "blocked"

    if req.requirement_class in {"user_input", "branch_decision", "selection_goal"}:
        canonical = canonical_parameter_key(field)
        if parameter_is_ready(existing_inputs, canonical):
            return "resolved"
        return "missing"

    return "missing"


def _apply_activation_statuses(
    requirements: dict,
    *,
    existing_inputs: dict[str, Fact],
) -> None:
    for req in requirements.values():
        req.activation_status = resolve_activation_status(req, existing_inputs)
        if req.activation_status == "not_applicable":
            req.status = "not_applicable"


def _apply_statuses(
    requirements: dict,
    *,
    existing_inputs: dict[str, Fact],
) -> None:
    diameter_mode = _diameter_mode(existing_inputs)
    for requirement_id in requirements:
        requirements[requirement_id].status = _requirement_status(
            requirement_id,
            existing_inputs=existing_inputs,
            requirements=requirements,
            diameter_mode=diameter_mode,
        )
    _apply_activation_statuses(requirements, existing_inputs=existing_inputs)


_GATE_REQUIREMENT_IDS = frozenset({req_id("straight_pipe_section"), req_id("pressure_loading")})


def _compute_root_blocking(requirements: dict) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    provisional: list[str] = []

    for requirement_id, req in requirements.items():
        if req.status in {"resolved", "not_applicable"}:
            continue
        if req.activation_status == "not_applicable":
            continue
        if req.status not in {"missing", "blocked", "ready"}:
            continue

        if requirement_id in _GATE_REQUIREMENT_IDS:
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


def build_pipe_wall_engineering_plan(
    task: Task,
    *,
    reader: StandardsReader | None = None,
    preview: Any | None = None,
    phased: PhasedNavigation | None = None,
    existing_inputs: dict[str, Fact] | None = None,
    path_decision: dict[str, str] | None = None,
    has_execution: bool = False,
    post_thickness_outputs: dict[str, Any] | None = None,
) -> EngineeringPlan:
    workflow_id = str(task.outputs.get("workflow") or PIPE_WALL_THICKNESS_DESIGN)
    inputs = dict(existing_inputs or task.fact_store.active_facts())

    if reader is None:
        from pathlib import Path

        reader = StandardsReader(
            Path(__file__).resolve().parents[2] / "knowledge" / "standards",
            standard="asme_b31.3",
        )

    root_spec = resolve_root_goal_spec(
        reader,
        workflow_id,
        fallback_target_field="minimum_required_thickness",
    )
    requirements = build_pipe_wall_requirements(root_goal_id=root_spec.id)
    _apply_statuses(requirements, existing_inputs=inputs)

    thickness_ready = bool(
        (post_thickness_outputs or {}).get("t") is not None
        or (post_thickness_outputs or {}).get("required_thickness") is not None
    )
    minimum_done = bool(
        (post_thickness_outputs or {}).get("minimum_required_thickness") is not None
        or (post_thickness_outputs or {}).get("t_m") is not None
    )
    corrosion = requirements.get(req_id("corrosion_allowance"))
    if corrosion and has_execution and thickness_ready and not minimum_done:
        corrosion.phase = "definition_equation_completion"
        if corrosion.question_spec:
            corrosion.question_spec.ask_policy = "ask_now"

    root = root_calculation_goal(root_spec)
    hard_blocked, provisional_blocked = _compute_root_blocking(requirements)
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
    )

    plan = EngineeringPlan(
        plan_id=plan_id,
        task_id=task.task_id,
        workflow_id=workflow_id,
        root_goal=root,
        requirements=requirements,
        dependencies=[],
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


def build_engineering_plan(
    task: Task,
    reader: StandardsReader,
    *,
    preview: Any | None = None,
    phased: PhasedNavigation | None = None,
    existing_inputs: dict[str, Fact] | None = None,
    path_decision: dict[str, str] | None = None,
    nav_config: WorkflowNavigationConfig | None = None,
) -> EngineeringPlan | None:
    del nav_config
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    slug = workflow_id.replace("-", "_")
    if slug not in {PIPE_WALL_WORKFLOW, PIPE_WALL_THICKNESS_DESIGN}:
        return None
    from engine.graph.definition_equations import has_execution_trace

    return build_pipe_wall_engineering_plan(
        task,
        reader=reader,
        preview=preview,
        phased=phased,
        existing_inputs=existing_inputs,
        path_decision=path_decision,
        has_execution=has_execution_trace(task),
        post_thickness_outputs=dict(task.outputs),
    )


@dataclass
class EngineeringPlanBuildContext:
    """Inputs for building a normalized engineering plan."""

    task: Task
    reader: StandardsReader | None = None
    preview: Any | None = None
    phased: PhasedNavigation | None = None
    existing_inputs: dict[str, Fact] | None = None
    path_decision: dict[str, str] | None = None
    nav_config: WorkflowNavigationConfig | None = None


def build_engineering_plan_from_context(context: EngineeringPlanBuildContext) -> EngineeringPlan | None:
    """Build normalized EngineeringPlan from a structured context object."""
    if context.reader is None:
        raise ValueError("EngineeringPlanBuildContext.reader is required")
    return build_engineering_plan(
        context.task,
        context.reader,
        preview=context.preview,
        phased=context.phased,
        existing_inputs=context.existing_inputs,
        path_decision=context.path_decision,
        nav_config=context.nav_config,
    )
