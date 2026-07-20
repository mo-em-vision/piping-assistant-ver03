"""Planner-owned projections for composer parameters and timeline reveal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.navigation.composer_mapping import composer_parameter_ids
from engine.navigation.submittable_projection import collection_step_order
from engine.navigation.timeline_projection import (
    HIDDEN_TIMELINE_INPUTS,
    ensure_diameter_timeline_pair,
    hidden_timeline_inputs,
    step_applies_for_timeline,
)
from engine.planner.plan_phases import strategy_field
from engine.planner.plan_selection import (
    engineering_plan_for_task,
    planner_submittable_fields_from_task,
    task_has_stored_engineering_plan,
)
from engine.navigation.timeline_row_ids import timeline_row_id
from engine.reference.parameter_keys import api_parameter_id
from engine.router import is_supported_planning_workflow
from models.fact import ValidationStatus, fact_scalar_value
from models.task import Task

if TYPE_CHECKING:
    from engine.reference.standards_reader import StandardsReader

_TIMELINE_ROW_ID_FOR_CANONICAL: dict[str, str] = {}


def _timeline_row_id(parameter_key: str) -> str:
    return timeline_row_id(parameter_key)


def _task_workflow_id(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")


def uses_planner_input_projection(task: Task) -> bool:
    """True when gatherable inputs must follow stored EngineeringPlan only."""
    return task_has_stored_engineering_plan(task) and is_supported_planning_workflow(
        _task_workflow_id(task)
    )


def planner_active_input_ids(task: Task) -> list[str]:
    """Current submittable field ids from engineering_plan.input_strategy."""
    return list(planner_submittable_fields_from_task(task) or [])


def _is_outstanding_gatherable_requirement(req) -> bool:
    if req.activation_status != "active":
        return False
    if req.status not in {"missing", "ready"}:
        return False
    if req.requirement_class not in {"user_input", "branch_decision"}:
        return False
    if not req.question_spec:
        return False
    if req.question_spec.ask_policy in {"do_not_ask", "ask_if_needed", "ask_later"}:
        return False
    return True


def planner_outstanding_gatherable_field_ids(task: Task) -> list[str]:
    """Gatherable fields still outstanding on the stored engineering plan."""
    plan = engineering_plan_for_task(task)
    if plan is None:
        return []

    ordered: list[str] = []
    seen: set[str] = set()
    for phase in plan.phases:
        for req_id in phase.requirement_ids:
            req = plan.requirements.get(req_id)
            if req is None or not _is_outstanding_gatherable_requirement(req):
                continue
            field = strategy_field(req)
            if not field or field in seen:
                continue
            seen.add(field)
            ordered.append(field)
    return ordered


def _timeline_fact_ids(task: Task) -> set[str]:
    """Fact-backed timeline rows (confirmed inputs and resolved lookup outputs)."""
    hidden = hidden_timeline_inputs(task)
    fact_ids: set[str] = set()
    for input_id, fact in task.fact_store.active_facts().items():
        if input_id in hidden:
            continue
        if not step_applies_for_timeline(task, input_id):
            continue
        if fact_scalar_value(fact) is not None or isinstance(fact_scalar_value(fact), bool):
            fact_ids.add(_timeline_row_id(input_id))
            continue
        if fact.validation.status in {ValidationStatus.CONFIRMED, ValidationStatus.VALIDATED}:
            fact_ids.add(_timeline_row_id(input_id))
    return fact_ids


def _planner_timeline_field_ids(task: Task) -> list[str]:
    """All planned gatherable fields on the active path for timeline presentation."""
    plan = engineering_plan_for_task(task)
    if plan is None:
        return []

    ordered: list[str] = []
    seen: set[str] = set()
    for phase in plan.phases:
        for req_id in phase.requirement_ids:
            req = plan.requirements.get(req_id)
            if req is None:
                continue
            if req.activation_status == "not_applicable":
                continue
            if req.status in {"resolved", "not_applicable"}:
                continue
            if req.requirement_class not in {"user_input", "branch_decision"}:
                continue
            if not req.question_spec:
                continue
            if req.question_spec.ask_policy in {"do_not_ask"}:
                continue
            field = strategy_field(req)
            if not field or field in seen:
                continue
            seen.add(field)
            ordered.append(field)
    return ordered


def _ensure_diameter_timeline_pair(task: Task, revealed: set[str]) -> None:
    ensure_diameter_timeline_pair(task, revealed)


def composer_parameter_ids_for_task(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
    editing_parameter: str | None = None,
) -> list[str]:
    """Parameter ids exposed in the composer for supported planning workflows."""
    del planning, reader
    active_ids = planner_active_input_ids(task)
    if not active_ids:
        return [editing_parameter] if editing_parameter else []

    requested = composer_parameter_ids(task, active_ids)
    if editing_parameter and editing_parameter not in requested:
        requested = [editing_parameter, *requested]
    return requested


def timeline_revealed_input_ids(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    """Timeline row ids: confirmed facts, active planner field, and pending upcoming."""
    hidden = hidden_timeline_inputs(task)
    revealed: set[str] = set(_timeline_fact_ids(task))

    for field_id in planner_active_input_ids(task):
        canonical = _timeline_row_id(field_id)
        if canonical not in hidden and step_applies_for_timeline(task, canonical):
            revealed.add(canonical)

    step_order = collection_step_order(task, planning, reader=reader)
    planned_fields = {_timeline_row_id(field_id) for field_id in _planner_timeline_field_ids(task)}
    if step_order:
        for step_id in step_order:
            canonical = _timeline_row_id(step_id)
            if canonical in planned_fields and canonical not in hidden:
                if step_applies_for_timeline(task, canonical):
                    revealed.add(canonical)
    else:
        revealed.update(
            field_id
            for field_id in planned_fields
            if field_id not in hidden and step_applies_for_timeline(task, field_id)
        )

    if task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None:
        revealed.add("allowable_stress")

    _ensure_diameter_timeline_pair(task, revealed)
    return _order_timeline_revealed_ids(task, revealed, planning=planning, reader=reader)


def _step_order_index(step_order: tuple[str, ...], step_id: str) -> int:
    canonical = _timeline_row_id(step_id)
    try:
        return step_order.index(canonical)
    except ValueError:
        return 999_999


def _order_timeline_revealed_ids(
    task: Task,
    revealed: set[str],
    *,
    planning: dict[str, Any],
    reader: StandardsReader | None = None,
) -> list[str]:
    hidden = hidden_timeline_inputs(task)
    revealed_visible = {_timeline_row_id(step_id) for step_id in revealed if step_id not in hidden}
    step_order = tuple(_timeline_row_id(step_id) for step_id in collection_step_order(task, planning, reader=reader))

    stored = task.outputs.get("timeline_input_order")
    if uses_planner_input_projection(task):
        stored = None

    if isinstance(stored, list):
        ordered: list[str] = []
        seen: set[str] = set()
        for step_id in stored:
            canonical = _timeline_row_id(str(step_id))
            if canonical in revealed_visible and canonical not in seen:
                ordered.append(canonical)
                seen.add(canonical)
        for step_id in step_order:
            if step_id in revealed_visible and step_id not in seen:
                ordered.append(step_id)
                seen.add(step_id)
        new_ids = revealed_visible.difference(seen)
        if new_ids:
            for new_id in sorted(
                new_ids,
                key=lambda item: (_step_order_index(step_order, item), item),
            ):
                ordered.append(new_id)
        return ordered

    ordered = [step_id for step_id in step_order if step_id in revealed_visible]
    remaining = sorted(
        revealed_visible.difference(ordered),
        key=lambda item: (_step_order_index(step_order, item), item),
    )
    ordered.extend(remaining)
    return ordered
