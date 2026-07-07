"""Build normalized EngineeringPlan objects from graph planning state."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.navigation_phases import PhasedNavigation
from engine.graph.workflow_navigation import WorkflowNavigationConfig
from engine.planner.activation_conditions import evaluate_activation_condition
from engine.planner.pipe_wall_plan import (
    PIPE_WALL_WORKFLOW,
    ROOT_GOAL_ID,
    build_pipe_wall_dependencies,
    build_pipe_wall_requirements,
    req_id,
    root_calculation_goal,
)
from engine.planner.plan_validation import validate_engineering_plan
from engine.planner.planner_traversal import build_planner_traversal_state
from engine.reference.parameter_keys import canonical_parameter_key, parameter_is_ready
from engine.reference.standards_reader import StandardsReader
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.engineering_plan import (
    BranchDecision,
    EngineeringPlan,
    InputStrategy,
    PlanGraph,
    PlanPhase,
    PlanRequirement,
    new_plan_id,
)
from models.fact import Fact
from models.planning import NavigationPhase
from models.task import Task

_PHASE_ORDER = [
    NavigationPhase.EXPANSION_ASSUMPTIONS.value,
    NavigationPhase.PATH_DECISIONS.value,
    NavigationPhase.PARAMETER_GATHERING.value,
    NavigationPhase.COEFFICIENT_RESOLUTION.value,
    NavigationPhase.EXECUTION_ASSUMPTIONS.value,
    NavigationPhase.DEFINITION_EQUATION_COMPLETION.value,
    "equation_execution",
    "validation",
    "reporting",
]

_USER_INPUT_PHASES = frozenset(
    {
        NavigationPhase.EXPANSION_ASSUMPTIONS.value,
        NavigationPhase.PATH_DECISIONS.value,
        NavigationPhase.PARAMETER_GATHERING.value,
    }
)

_COMPUTATION_PHASES = frozenset({"equation_execution", "validation", "reporting"})

_SYNTHETIC_PHASES = frozenset({"validation", "reporting"})

_OPTIONAL_EMPTY_PHASES = frozenset(
    {
        NavigationPhase.EXECUTION_ASSUMPTIONS.value,
        NavigationPhase.DEFINITION_EQUATION_COMPLETION.value,
    }
)

_PHASE_TITLES = {
    NavigationPhase.EXPANSION_ASSUMPTIONS.value: "Expansion assumptions",
    NavigationPhase.PATH_DECISIONS.value: "Path decisions",
    NavigationPhase.PARAMETER_GATHERING.value: "Parameter gathering",
    NavigationPhase.COEFFICIENT_RESOLUTION.value: "Coefficient resolution",
    NavigationPhase.EXECUTION_ASSUMPTIONS.value: "Execution assumptions",
    NavigationPhase.DEFINITION_EQUATION_COMPLETION.value: "Definition equation completion",
    NavigationPhase.READY.value: "Ready",
    "equation_execution": "Equation execution",
    "validation": "Validation",
    "reporting": "Reporting",
}


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

    if req.requirement_class in {"table_lookup", "equation_result"}:
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
        condition = req.activation_condition
        if condition is None:
            req.activation_status = "active"
            continue

        outcome = evaluate_activation_condition(condition, existing_inputs)
        if outcome is None:
            req.activation_status = "conditional"
            continue
        if outcome:
            req.activation_status = "active"
            continue

        req.activation_status = "not_applicable"
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


def _is_gathering_blocker(requirement_id: str, req: PlanRequirement) -> bool:
    if requirement_id == req_id("nominal_pipe_size"):
        return False
    if req.requirement_class in {"user_input", "branch_decision"} and req.phase in {
        "parameter_gathering",
        "coefficient_resolution",
    }:
        return True
    if requirement_id == "REQ-diameter_resolution" and req.status != "resolved":
        return True
    return False


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

        if not _is_gathering_blocker(requirement_id, req):
            continue

        if req.activation_status == "conditional":
            provisional.append(requirement_id)
        else:
            hard.append(requirement_id)

    return hard, provisional


def _requirements_for_phase(requirements: dict, phase_id: str) -> list[str]:
    return [
        rid
        for rid, req in requirements.items()
        if req.phase == phase_id
        and req.status != "not_applicable"
        and req.activation_status != "not_applicable"
    ]


def _phase_is_complete(requirements: dict, req_ids: list[str]) -> bool:
    if not req_ids:
        return False
    return all(requirements[rid].status in {"resolved", "not_applicable"} for rid in req_ids)


def _legacy_phase_status(requirements: dict, req_ids: list[str]) -> str:
    statuses = [requirements[rid].status for rid in req_ids]
    if all(status == "resolved" for status in statuses):
        return "complete"
    if any(status in {"missing", "ready"} for status in statuses):
        return "active"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    return "pending"


def derive_plan_phase_statuses(
    requirements: dict,
    *,
    input_strategy: InputStrategy | None = None,
) -> list[PlanPhase]:
    """Derive ordered plan phase statuses from requirement states and input strategy."""
    active_phase = (
        input_strategy.current_phase
        if input_strategy and input_strategy.current_phase
        else _first_incomplete_phase(requirements)
    )
    single_next = bool(input_strategy and input_strategy.mode == "single_next_question")
    active_index = _PHASE_ORDER.index(active_phase) if active_phase in _PHASE_ORDER else -1

    phases: list[PlanPhase] = []
    for index, phase_id in enumerate(_PHASE_ORDER):
        req_ids = _requirements_for_phase(requirements, phase_id)
        is_synthetic = phase_id in _SYNTHETIC_PHASES

        if not req_ids and phase_id in _OPTIONAL_EMPTY_PHASES:
            continue
        if not req_ids and not is_synthetic and phase_id not in _COMPUTATION_PHASES:
            continue

        if _phase_is_complete(requirements, req_ids):
            status = "complete"
        elif single_next:
            if phase_id == active_phase:
                status = "active"
            elif phase_id in _COMPUTATION_PHASES or (
                phase_id == NavigationPhase.COEFFICIENT_RESOLUTION.value
                and phase_id != active_phase
            ):
                status = "blocked"
            elif active_index >= 0 and index > active_index:
                status = "pending"
            else:
                status = "pending"
        else:
            status = _legacy_phase_status(requirements, req_ids) if req_ids else "blocked"

        phases.append(
            PlanPhase(
                id=phase_id,
                title=_PHASE_TITLES.get(phase_id, phase_id.replace("_", " ").title()),
                order=index,
                requirement_ids=req_ids,
                status=status,
            )
        )
    return phases


def _build_phases(
    requirements: dict,
    *,
    input_strategy: InputStrategy | None = None,
) -> list[PlanPhase]:
    return derive_plan_phase_statuses(requirements, input_strategy=input_strategy)


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


def _askable_fields_for_phase(requirements: dict, phase: str) -> list[tuple[int, str]]:
    askable: list[tuple[int, str]] = []
    for req in requirements.values():
        if req.phase != phase:
            continue
        if not _is_askable_requirement(req):
            continue
        askable.append((req.question_spec.priority, req.question_spec.field))
    askable.sort(key=lambda item: (item[0], item[1]))
    return askable


def _first_incomplete_phase(requirements: dict) -> str:
    for phase in _PHASE_ORDER:
        if _askable_fields_for_phase(requirements, phase):
            return phase
    for phase in _PHASE_ORDER:
        for req in requirements.values():
            if req.phase != phase:
                continue
            if req.activation_status != "active":
                continue
            if req.status != "missing":
                continue
            if req.requirement_class not in {"user_input", "branch_decision"}:
                continue
            if req.question_spec and req.question_spec.ask_policy != "do_not_ask":
                return phase
    return NavigationPhase.READY.value


def _build_input_strategy(
    requirements: dict,
    *,
    phased: PhasedNavigation | None,
    existing_inputs: dict[str, Fact],
) -> InputStrategy:
    del phased, existing_inputs
    current_phase = _first_incomplete_phase(requirements)
    askable = _askable_fields_for_phase(requirements, current_phase)
    next_fields = [field for _, field in askable[:1]]

    resolved = [
        req.field
        for req in requirements.values()
        if req.status == "resolved" and req.requirement_class in {"user_input", "branch_decision"}
    ]
    blocked = [
        req.field
        for req in requirements.values()
        if req.status == "blocked" and req.activation_status == "active"
    ]

    return InputStrategy(
        mode="single_next_question",
        current_phase=current_phase,
        next_fields=next_fields,
        blocked_fields=blocked,
        resolved_fields=resolved,
    )


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
    del reader
    workflow_id = str(task.outputs.get("workflow") or PIPE_WALL_THICKNESS_DESIGN)
    inputs = dict(existing_inputs or task.fact_store.active_facts())

    requirements = build_pipe_wall_requirements()
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

    root = root_calculation_goal()
    hard_blocked, provisional_blocked = _compute_root_blocking(requirements)
    root.blocked_by = hard_blocked
    root.provisional_blocked_by = provisional_blocked
    if not hard_blocked and not provisional_blocked:
        root.status = "ready"

    execution_order = list(getattr(preview, "execution_order", ()) or [])
    expanded = list(getattr(preview, "expanded_nodes", ()) or execution_order)

    input_strategy = _build_input_strategy(requirements, phased=phased, existing_inputs=inputs)

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
        dependencies=build_pipe_wall_dependencies(),
        input_strategy=input_strategy,
        graph=graph,
        phases=_build_phases(requirements, input_strategy=input_strategy),
        traversal=traversal,
    )

    validation = validate_engineering_plan(plan)
    if validation.warnings or validation.errors:
        plan.debug = {
            "validation_errors": validation.errors,
            "validation_warnings": validation.warnings,
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
