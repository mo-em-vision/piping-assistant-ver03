"""Derive engineering plan phases and input strategy from requirement state."""

from __future__ import annotations

from models.engineering_plan import EngineeringPlan, InputStrategy, PlanPhase, PlanRequirement
from models.fact import Fact, FactClass, ValidationStatus
from models.planning import NavigationPhase
from engine.planner.requirement_ordering import (
    RequirementOrderContext,
    build_requirement_order_context,
    requirement_sort_key,
)

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

def strategy_field(req: PlanRequirement) -> str:
    """Composer / input-strategy field (may differ from requirement output field)."""
    if req.question_spec and req.question_spec.field:
        return req.question_spec.field
    return req.field


_LOOKUP_OUTPUT_METHODS = frozenset({"table_lookup", "catalog_lookup", "lookup"})
_NON_ASKABLE_CLASSES = frozenset(
    {"equation_result", "derived_value", "report_output", "validation_check"}
)


def _is_lookup_produced_output(req: PlanRequirement) -> bool:
    """True when the requirement value is produced by lookup/equation execution."""
    if req.requirement_class in _NON_ASKABLE_CLASSES:
        return True
    resolution = req.resolution or {}
    role = str(resolution.get("role") or "").strip()
    if role == "lookup_output":
        return True
    if role == "lookup_key":
        return False
    if req.requirement_class == "table_lookup":
        method = str(resolution.get("method") or "").strip()
        output_field = resolution.get("output_field")
        if method in _LOOKUP_OUTPUT_METHODS:
            return True
        if output_field and str(output_field) == req.field and method in _LOOKUP_OUTPUT_METHODS:
            return True
        if req.id.endswith("_lookup") and method in _LOOKUP_OUTPUT_METHODS:
            return True
    method = str(resolution.get("method") or "").strip()
    output_field = resolution.get("output_field")
    if method in _LOOKUP_OUTPUT_METHODS and output_field and str(output_field) == req.field:
        return True
    return False


def _ask_policy_allows_next_field(req: PlanRequirement) -> bool:
    if req.question_spec is None:
        return False
    policy = req.question_spec.ask_policy
    if policy == "ask_now":
        return True
    if policy in {"ask_later", "do_not_ask"}:
        return False
    if policy == "ask_if_needed":
        if req.activation_status != "active" or req.status != "missing":
            return False
        if _is_lookup_produced_output(req):
            return False
        return req.requirement_class in {"user_input", "branch_decision"}
    return False


def _is_askable_requirement(req: PlanRequirement) -> bool:
    if req.activation_status != "active":
        return False
    if req.status != "missing":
        return False
    if req.requirement_class not in {"user_input", "branch_decision"}:
        return False
    if not _ask_policy_allows_next_field(req):
        return False
    return True


def _askable_fields_for_phase(
    requirements: dict[str, PlanRequirement],
    phase: str,
    order_context: RequirementOrderContext | None = None,
) -> list[str]:
    askable: list[tuple[tuple, str]] = []
    for req_id, req in requirements.items():
        if req.phase != phase:
            continue
        if not _is_askable_requirement(req):
            continue
        askable.append(
            (
                requirement_sort_key(
                    req_id,
                    req,
                    order_context,
                    strategy_field_name=strategy_field(req),
                ),
                strategy_field(req),
            )
        )
    askable.sort(key=lambda item: (item[0], item[1]))
    return [field for _, field in askable]


def first_incomplete_phase(
    requirements: dict[str, PlanRequirement],
    order_context: RequirementOrderContext | None = None,
) -> str:
    """First phase with an active, unresolved askable requirement."""
    for phase in _PHASE_ORDER:
        if _askable_fields_for_phase(requirements, phase, order_context):
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
    order_context: RequirementOrderContext | None = None,
) -> list[str]:
    req_ids = [
        rid
        for rid, req in requirements.items()
        if req.phase == phase_id
        and req.status != "not_applicable"
        and req.activation_status != "not_applicable"
    ]
    req_ids.sort(
        key=lambda rid: requirement_sort_key(
            rid,
            requirements[rid],
            order_context,
            strategy_field_name=strategy_field(requirements[rid]),
        )
    )
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
    order_context: RequirementOrderContext | None = None,
) -> list[PlanPhase]:
    """Derive ordered plan phases with statuses from requirement and activation state."""
    del known_facts
    active_phase = (
        input_strategy.current_phase
        if input_strategy and input_strategy.current_phase
        else first_incomplete_phase(requirements, order_context)
    )
    single_next = bool(
        input_strategy is None or input_strategy.mode == "single_next_question"
    )
    active_index = _PHASE_ORDER.index(active_phase) if active_phase in _PHASE_ORDER else -1

    phases: list[PlanPhase] = []
    output_order = 0
    for index, phase_id in enumerate(_PHASE_ORDER):
        req_ids = _requirement_ids_for_phase(requirements, phase_id, order_context)
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


def _is_gatherable_submittable_requirement(req: PlanRequirement) -> bool:
    if req.activation_status != "active":
        return False
    if req.status != "missing":
        return False
    if req.requirement_class in _NON_ASKABLE_CLASSES:
        return False
    if req.requirement_class not in {"user_input", "branch_decision"}:
        return False
    if _is_lookup_produced_output(req):
        return False
    return True


def _resolution_branch_submittable_extras(
    requirements: dict[str, PlanRequirement],
    next_fields: list[str],
    known_facts: dict[str, Fact] | None,
) -> list[str]:
    """Metadata-driven branch fact keys when an anchor with alternatives is submittable."""
    if not next_fields:
        return []
    next_set = set(next_fields)
    extras: list[str] = []
    for req in requirements.values():
        if not req.alternatives:
            continue
        anchor = str(req.field).strip()
        if not anchor or anchor not in next_set:
            continue
        from engine.graph.resolution_branches import (
            active_resolution_branch_id,
            resolution_branch_fact_key,
        )

        if active_resolution_branch_id(anchor, known_facts or {}) is not None:
            continue
        branch_key = resolution_branch_fact_key(anchor)
        if branch_key in next_set or branch_key in extras:
            continue
        extras.append(branch_key)
    return extras


def _proposed_default_confirmation_fields(
    requirements: dict[str, PlanRequirement],
    *,
    current_phase: str,
    next_fields: list[str],
    known_facts: dict[str, Fact] | None,
) -> list[str]:
    """Unresolved proposed-default confirmations represented as missing planner requirements."""
    if not known_facts or not next_fields:
        return []
    next_field = next_fields[0]
    for req in requirements.values():
        if req.phase != current_phase:
            continue
        if not _is_gatherable_submittable_requirement(req):
            continue
        field = strategy_field(req)
        if field != next_field:
            continue
        for candidate_key in (field, req.field):
            existing = known_facts.get(candidate_key)
            if existing is None:
                continue
            if (
                existing.fact_class == FactClass.DEFAULT_CONFIRMED
                and existing.validation.status == ValidationStatus.PENDING
            ):
                return []
    return []


def derive_submittable_fields(
    requirements: dict[str, PlanRequirement],
    *,
    next_fields: list[str],
    current_phase: str,
    mode: str,
    known_facts: dict[str, Fact] | None = None,
) -> list[str]:
    """Planner-owned forward-submission fields for the current plan state."""
    if current_phase in {NavigationPhase.READY.value, *_COMPUTATION_PHASES}:
        return []
    if not next_fields:
        return []

    if mode == "single_next_question":
        submittable = list(dict.fromkeys(next_fields))
        for extra in _resolution_branch_submittable_extras(
            requirements,
            submittable,
            known_facts,
        ):
            if extra not in submittable:
                submittable.append(extra)
        _proposed_default_confirmation_fields(
            requirements,
            current_phase=current_phase,
            next_fields=submittable,
            known_facts=known_facts,
        )
        return submittable

    return list(dict.fromkeys(next_fields))


def derive_input_strategy(
    plan: EngineeringPlan,
    known_facts: dict[str, Fact] | None = None,
    *,
    order_context: RequirementOrderContext | None = None,
) -> InputStrategy:
    """Derive single-next-question input strategy from plan requirements and phase state."""
    requirements = plan.requirements
    phases = list(plan.phases)
    if not phases:
        phases = derive_plan_phases(requirements, order_context=order_context)

    current_phase = first_incomplete_phase(requirements, order_context)
    askable = _askable_fields_for_phase(requirements, current_phase, order_context)
    next_fields = askable[:1]
    mode = "single_next_question"
    submittable_fields = derive_submittable_fields(
        requirements,
        next_fields=next_fields,
        current_phase=current_phase,
        mode=mode,
        known_facts=known_facts,
    )

    return InputStrategy(
        mode=mode,
        current_phase=current_phase,
        next_fields=next_fields,
        submittable_fields=submittable_fields,
        blocked_fields=_blocked_fields(requirements, phases, next_fields),
        resolved_fields=_resolved_input_fields(requirements),
    )


def build_plan_phases_and_strategy(
    requirements: dict[str, PlanRequirement],
    known_facts: dict[str, Fact] | None = None,
    *,
    reader=None,
    execution_order: list[str] | None = None,
) -> tuple[list[PlanPhase], InputStrategy]:
    """Derive phases and input strategy together for plan construction."""
    order_context = build_requirement_order_context(
        requirements,
        reader=reader,
        execution_order=execution_order,
    )
    from engine.planner.requirement_ordering import sync_question_spec_priorities

    sync_question_spec_priorities(requirements, order_context)

    current_phase = first_incomplete_phase(requirements, order_context)
    askable = _askable_fields_for_phase(requirements, current_phase, order_context)
    next_fields = askable[:1]
    mode = "single_next_question"
    strategy_shell = InputStrategy(
        mode=mode,
        current_phase=current_phase,
        next_fields=next_fields,
        submittable_fields=[],
        blocked_fields=[],
        resolved_fields=[],
    )
    phases = derive_plan_phases(
        requirements,
        input_strategy=strategy_shell,
        order_context=order_context,
    )
    submittable_fields = derive_submittable_fields(
        requirements,
        next_fields=next_fields,
        current_phase=current_phase,
        mode=mode,
        known_facts=known_facts,
    )
    strategy = InputStrategy(
        mode=mode,
        current_phase=current_phase,
        next_fields=next_fields,
        submittable_fields=submittable_fields,
        blocked_fields=_blocked_fields(requirements, phases, next_fields),
        resolved_fields=_resolved_input_fields(requirements),
    )
    return phases, strategy


# Backward-compatible alias used by older planner tests and docs.
derive_plan_phase_statuses = derive_plan_phases


def refresh_stored_plan_input_strategy(
    task: Task,
    known_facts: dict[str, Fact] | None = None,
) -> bool:
    """Re-derive phases and input strategy on a stored plan without rebuilding requirements."""
    from engine.graph.definition_equations import has_execution_trace
    from engine.planner.legacy_goal_adapter import store_engineering_plan_on_task
    from engine.planner.plan_selection import engineering_plan_for_task
    from engine.state.task_facts import active_facts

    plan = engineering_plan_for_task(task)
    if plan is None or not plan.requirements:
        return False

    facts = known_facts if known_facts is not None else dict(active_facts(task))
    from engine.planner.engineering_plan_builder import _promote_late_phase_inputs
    from engine.planner.generic_plan import (
        apply_alternative_resolution_statuses,
        apply_generic_requirement_statuses,
    )

    apply_generic_requirement_statuses(plan.requirements, existing_inputs=facts)
    apply_alternative_resolution_statuses(plan.requirements, existing_inputs=facts)
    if has_execution_trace(task):
        _promote_late_phase_inputs(plan)
    phases, strategy = build_plan_phases_and_strategy(
        plan.requirements,
        known_facts=facts,
        execution_order=list(plan.graph.selected_subgraph_node_ids or ()),
    )
    plan.phases = phases
    plan.input_strategy = strategy
    store_engineering_plan_on_task(task, plan)
    return True
