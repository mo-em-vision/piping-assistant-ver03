"""Build graph_navigation snapshots from normalized engineering plans."""

from __future__ import annotations

from typing import Any, TypeVar

from models.engineering_plan import EngineeringPlan, PlanRequirement
from models.planning import NavigationPhase

T = TypeVar("T")

_PHASE_MISSING_ORDER = (
    NavigationPhase.EXPANSION_ASSUMPTIONS.value,
    NavigationPhase.PATH_DECISIONS.value,
    NavigationPhase.PARAMETER_GATHERING.value,
    NavigationPhase.COEFFICIENT_RESOLUTION.value,
    NavigationPhase.EXECUTION_ASSUMPTIONS.value,
    NavigationPhase.DEFINITION_EQUATION_COMPLETION.value,
    "equation_execution",
    "validation",
    "reporting",
)


def unique_stable(items: list[T]) -> list[T]:
    """Return items in first-seen order with duplicates removed."""
    seen: set[T] = set()
    result: list[T] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _missing_collectable_field(req: PlanRequirement) -> str | None:
    if req.activation_status != "active":
        return None
    if req.status != "missing":
        return None
    if req.requirement_class not in {"user_input", "branch_decision"}:
        return None
    if req.question_spec is None:
        return None
    if req.question_spec.ask_policy in {"ask_later", "do_not_ask", "ask_if_needed"}:
        return None
    return req.question_spec.field


def _visible_missing_field(req: PlanRequirement) -> str | None:
    """Missing fields shown in phase_missing, including conditional future work."""
    if req.activation_status == "not_applicable":
        return None
    if req.status != "missing":
        return None
    if req.requirement_class not in {"user_input", "branch_decision"}:
        return None
    if req.question_spec is None:
        return None
    if req.question_spec.ask_policy in {"ask_later", "do_not_ask", "ask_if_needed"}:
        return None
    return req.question_spec.field


def _missing_fields_for_phase(requirements: dict[str, PlanRequirement], phase_id: str) -> list[str]:
    fields: list[str] = []
    for req in requirements.values():
        if req.phase != phase_id:
            continue
        field = _visible_missing_field(req)
        if field:
            fields.append(field)
    return unique_stable(fields)


def _requirement_id_for_field(
    requirements: dict[str, PlanRequirement],
    field: str | None,
) -> str | None:
    if not field:
        return None
    for req in requirements.values():
        if _missing_collectable_field(req) == field:
            return req.id
        if req.field == field and req.status == "missing" and req.activation_status == "active":
            return req.id
    return None


def validate_graph_navigation(nav: dict[str, Any]) -> list[str]:
    """Return invariant violations for graph_navigation missing-field lists."""
    errors: list[str] = []
    list_keys = (
        "missing_expansion_assumptions",
        "missing_path_decisions",
        "missing_user_inputs",
        "missing_coefficient_inputs",
        "missing_execution_assumptions",
    )
    for key in list_keys:
        items = list(nav.get(key) or [])
        if len(items) != len(set(items)):
            errors.append(f"duplicate fields in graph_navigation.{key}")

    phase_missing = nav.get("phase_missing") or {}
    if isinstance(phase_missing, dict):
        for phase, fields in phase_missing.items():
            field_list = list(fields or [])
            if len(field_list) != len(set(field_list)):
                errors.append(f"duplicate fields in graph_navigation.phase_missing[{phase!r}]")

    return errors


_PHASE_PREVIEW_SKIP = frozenset(
    {
        "equation_execution",
        "validation",
        "reporting",
        "definition_equation_completion",
    }
)

_NAV_DISPLAY_FIELD_ALIASES = {
    "outside_diameter": "outside_diameter__resolution_branch",
}


def _merge_provisional_phase_missing(
    plan: EngineeringPlan,
    phase_missing: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Add graph-derived phased preview fields for phases not yet on the plan requirements."""
    preview: dict[str, Any] = {}
    if isinstance(plan.debug, dict):
        raw = plan.debug.get("phased_preview") or plan.debug.get("navigation_preview")
        if isinstance(raw, dict):
            preview = raw
    if not preview:
        return phase_missing

    current_phase = (
        plan.input_strategy.current_phase
        if plan.input_strategy and plan.input_strategy.current_phase
        else None
    )
    phase_order = list(_PHASE_MISSING_ORDER)
    start_index = phase_order.index(current_phase) + 1 if current_phase in phase_order else 0

    merged = {phase_id: list(fields or []) for phase_id, fields in phase_missing.items()}
    for phase_id in phase_order[start_index:]:
        if phase_id in _PHASE_PREVIEW_SKIP:
            continue
        nav_fields = preview.get(phase_id) or []
        if not nav_fields:
            continue
        display_fields = [
            _NAV_DISPLAY_FIELD_ALIASES.get(str(field), str(field)) for field in nav_fields
        ]
        existing = list(merged.get(phase_id) or [])
        merged[phase_id] = unique_stable(existing + display_fields)
    return merged


def build_graph_navigation_from_plan(plan: EngineeringPlan) -> dict[str, Any]:
    """Derive categorized graph navigation state from a normalized engineering plan."""
    requirements = plan.requirements
    input_strategy = plan.input_strategy

    current_phase = (
        input_strategy.current_phase
        if input_strategy and input_strategy.current_phase
        else NavigationPhase.READY.value
    )
    next_fields = unique_stable(list(input_strategy.next_fields if input_strategy else []))
    active_field = next_fields[0] if next_fields else None

    phase_missing: dict[str, list[str]] = {}
    for phase_id in _PHASE_MISSING_ORDER:
        fields = _missing_fields_for_phase(requirements, phase_id)
        phase_missing[phase_id] = fields
    phase_missing = _merge_provisional_phase_missing(plan, phase_missing)

    missing_expansion_assumptions = list(
        phase_missing.get(NavigationPhase.EXPANSION_ASSUMPTIONS.value) or []
    )
    missing_path_decisions = list(phase_missing.get(NavigationPhase.PATH_DECISIONS.value) or [])
    missing_execution_assumptions = list(
        phase_missing.get(NavigationPhase.EXECUTION_ASSUMPTIONS.value) or []
    )

    missing_user_inputs: list[str] = []
    if current_phase == NavigationPhase.PARAMETER_GATHERING.value:
        parameter_fields = set(
            phase_missing.get(NavigationPhase.PARAMETER_GATHERING.value) or []
        )
        missing_user_inputs = unique_stable(
            [field for field in next_fields if field in parameter_fields]
        )

    missing_coefficient_inputs: list[str] = []
    if current_phase == NavigationPhase.COEFFICIENT_RESOLUTION.value:
        coefficient_fields = set(
            phase_missing.get(NavigationPhase.COEFFICIENT_RESOLUTION.value) or []
        )
        missing_coefficient_inputs = unique_stable(
            [field for field in next_fields if field in coefficient_fields]
        )

    payload: dict[str, Any] = {
        "current_phase": current_phase,
        "phase_missing": phase_missing,
        "missing_expansion_assumptions": missing_expansion_assumptions,
        "missing_path_decisions": missing_path_decisions,
        "missing_user_inputs": missing_user_inputs,
        "missing_coefficient_inputs": missing_coefficient_inputs,
        "missing_execution_assumptions": missing_execution_assumptions,
        "active_field": active_field,
        "active_requirement_id": _requirement_id_for_field(requirements, active_field),
        "warnings": [],
    }

    if next_fields and active_field != next_fields[0]:
        payload["warnings"].append(
            "graph_navigation.active_field must match engineering plan input_strategy.next_fields[0]"
        )

    invariant_errors = validate_graph_navigation(payload)
    if invariant_errors:
        payload["warnings"] = invariant_errors

    return payload


def graph_navigation_has_collectable_missing(nav: dict[str, Any] | None) -> bool:
    """Return True when graph navigation still has user-facing fields to collect."""
    if not nav:
        return True
    if nav.get("active_field"):
        return True
    return bool(
        nav.get("missing_expansion_assumptions")
        or nav.get("missing_path_decisions")
        or nav.get("missing_user_inputs")
        or nav.get("missing_coefficient_inputs")
        or nav.get("missing_execution_assumptions")
    )
