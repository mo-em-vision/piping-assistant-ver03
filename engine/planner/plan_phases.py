"""Derive engineering plan phases and input strategy from requirement state."""

from __future__ import annotations

from models.engineering_plan import EngineeringPlan, InputStrategy, PlanPhase, PlanRequirement
from models.fact import Fact
from models.planning import NavigationPhase

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

_COMPUTATION_PHASES = frozenset({"equation_execution", "validation", "reporting"})

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

_PHASE_REQUIREMENT_ORDER: dict[str, tuple[str, ...]] = {
    "coefficient_resolution": (
        "REQ-pipe_construction_type",
        "REQ-metallurgical_group_lookup",
        "REQ-allowable_stress_lookup",
        "REQ-temperature_coefficient_Y_lookup",
        "REQ-weld_joint_efficiency_lookup",
        "REQ-weld_strength_reduction_factor_W_lookup",
    ),
}


def strategy_field(req: PlanRequirement) -> str:
    """Composer / input-strategy field (may differ from requirement output field)."""
    if req.question_spec and req.question_spec.field:
        return req.question_spec.field
    return req.field


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


def _askable_fields_for_phase(requirements: dict[str, PlanRequirement], phase: str) -> list[tuple[int, str]]:
    askable: list[tuple[int, str]] = []
    for req in requirements.values():
        if req.phase != phase:
            continue
        if not _is_askable_requirement(req):
            continue
        askable.append((req.question_spec.priority, strategy_field(req)))
    askable.sort(key=lambda item: (item[0], item[1]))
    return askable


def first_incomplete_phase(requirements: dict[str, PlanRequirement]) -> str:
    """First phase with an active, unresolved askable requirement."""
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


def _requirement_ids_for_phase(
    requirements: dict[str, PlanRequirement],
    phase_id: str,
) -> list[str]:
    req_ids = [
        rid
        for rid, req in requirements.items()
        if req.phase == phase_id
        and req.status != "not_applicable"
        and req.activation_status != "not_applicable"
    ]
    order = _PHASE_REQUIREMENT_ORDER.get(phase_id)
    if order:
        rank = {rid: index for index, rid in enumerate(order)}
        req_ids.sort(key=lambda rid: (rank.get(rid, len(order)), rid))
    else:
        req_ids.sort()
    return req_ids


def _phase_is_complete(requirements: dict[str, PlanRequirement], req_ids: list[str]) -> bool:
    if not req_ids:
        return False
    return all(requirements[rid].status in {"resolved", "not_applicable"} for rid in req_ids)


def _legacy_phase_status(requirements: dict[str, PlanRequirement], req_ids: list[str]) -> str:
    statuses = [requirements[rid].status for rid in req_ids]
    if all(status == "resolved" for status in statuses):
        return "complete"
    if any(status in {"missing", "ready"} for status in statuses):
        return "active"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    return "pending"


def derive_plan_phases(
    requirements: dict[str, PlanRequirement],
    known_facts: dict[str, Fact] | None = None,
    *,
    input_strategy: InputStrategy | None = None,
) -> list[PlanPhase]:
    """Derive ordered plan phases with statuses from requirement and activation state."""
    del known_facts
    active_phase = (
        input_strategy.current_phase
        if input_strategy and input_strategy.current_phase
        else first_incomplete_phase(requirements)
    )
    single_next = bool(
        input_strategy is None or input_strategy.mode == "single_next_question"
    )
    active_index = _PHASE_ORDER.index(active_phase) if active_phase in _PHASE_ORDER else -1

    phases: list[PlanPhase] = []
    output_order = 0
    for index, phase_id in enumerate(_PHASE_ORDER):
        req_ids = _requirement_ids_for_phase(requirements, phase_id)
        if not req_ids:
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
            status = _legacy_phase_status(requirements, req_ids)

        phases.append(
            PlanPhase(
                id=phase_id,
                title=_PHASE_TITLES.get(phase_id, phase_id.replace("_", " ").title()),
                order=output_order,
                requirement_ids=req_ids,
                status=status,
            )
        )
        output_order += 1
    return phases


def _blocked_fields(
    requirements: dict[str, PlanRequirement],
    phases: list[PlanPhase],
    next_fields: list[str],
) -> list[str]:
    next_set = set(next_fields)
    blocked: list[str] = []
    seen: set[str] = set()
    for phase in phases:
        for requirement_id in phase.requirement_ids:
            req = requirements[requirement_id]
            if req.status == "resolved":
                continue
            if req.activation_status == "not_applicable":
                continue
            if req.requirement_class == "report_output":
                continue
            field = strategy_field(req)
            if field in next_set or field in seen:
                continue
            seen.add(field)
            blocked.append(field)
    return blocked


def _resolved_input_fields(requirements: dict[str, PlanRequirement]) -> list[str]:
    return [
        strategy_field(req)
        for req in requirements.values()
        if req.status == "resolved"
        and req.requirement_class in {"user_input", "branch_decision"}
    ]


def derive_input_strategy(
    plan: EngineeringPlan,
    known_facts: dict[str, Fact] | None = None,
) -> InputStrategy:
    """Derive single-next-question input strategy from plan requirements and phase state."""
    del known_facts
    requirements = plan.requirements
    phases = list(plan.phases)
    if not phases:
        phases = derive_plan_phases(requirements)

    current_phase = first_incomplete_phase(requirements)
    askable = _askable_fields_for_phase(requirements, current_phase)
    next_fields = [field for _, field in askable[:1]]

    return InputStrategy(
        mode="single_next_question",
        current_phase=current_phase,
        next_fields=next_fields,
        blocked_fields=_blocked_fields(requirements, phases, next_fields),
        resolved_fields=_resolved_input_fields(requirements),
    )


def build_plan_phases_and_strategy(
    requirements: dict[str, PlanRequirement],
    known_facts: dict[str, Fact] | None = None,
) -> tuple[list[PlanPhase], InputStrategy]:
    """Derive phases and input strategy together for plan construction."""
    del known_facts
    current_phase = first_incomplete_phase(requirements)
    askable = _askable_fields_for_phase(requirements, current_phase)
    next_fields = [field for _, field in askable[:1]]
    strategy_shell = InputStrategy(
        mode="single_next_question",
        current_phase=current_phase,
        next_fields=next_fields,
        blocked_fields=[],
        resolved_fields=[],
    )
    phases = derive_plan_phases(
        requirements,
        input_strategy=strategy_shell,
    )
    strategy = InputStrategy(
        mode="single_next_question",
        current_phase=current_phase,
        next_fields=next_fields,
        blocked_fields=_blocked_fields(requirements, phases, next_fields),
        resolved_fields=_resolved_input_fields(requirements),
    )
    return phases, strategy


# Backward-compatible alias used by older planner tests and docs.
derive_plan_phase_statuses = derive_plan_phases
