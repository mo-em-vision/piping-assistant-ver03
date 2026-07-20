"""Legacy timeline reveal for tasks without a stored EngineeringPlan."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.navigation.composer_mapping import composer_parameter_id
from engine.navigation.submittable_projection import collection_step_order
from engine.navigation.timeline_projection import (
    HIDDEN_TIMELINE_INPUTS,
    ensure_diameter_timeline_pair,
    step_applies_for_timeline,
)
from engine.navigation.timeline_row_ids import consolidate_timeline_row_ids, timeline_row_id
from engine.reference.parameter_keys import (
    LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
    api_parameter_id,
)
from models.planning import NavigationPhase
from models.task import Task

if TYPE_CHECKING:
    from engine.reference.standards_reader import StandardsReader

_NAVIGATION_PHASE_SEQUENCE: tuple[str, ...] = (
    NavigationPhase.EXPANSION_ASSUMPTIONS.value,
    NavigationPhase.PATH_DECISIONS.value,
    NavigationPhase.PARAMETER_GATHERING.value,
    NavigationPhase.COEFFICIENT_RESOLUTION.value,
    NavigationPhase.EXECUTION_ASSUMPTIONS.value,
    NavigationPhase.DEFINITION_EQUATION_COMPLETION.value,
)


def _step_order_index(step_order: tuple[str, ...], step_id: str) -> int:
    canonical = timeline_row_id(step_id)
    normalized_order = tuple(timeline_row_id(item) for item in step_order)
    try:
        return normalized_order.index(canonical)
    except ValueError:
        return 999_999


def _navigation_fields_through_current_phase(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader,
) -> set[str]:
    from engine.graph.workflow_navigation import load_workflow_navigation

    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    config = load_workflow_navigation(reader, workflow_id)
    current_phase = str(planning.get("current_phase") or "")
    fields: set[str] = set()
    for phase, phase_fields in config.phase_order:
        if phase == NavigationPhase.READY:
            break
        for field in phase_fields:
            fields.add(str(field))
        if phase.value == current_phase:
            break
    return fields


def _current_phase_index(planning: dict[str, Any]) -> int:
    current_phase = str(planning.get("current_phase") or "")
    try:
        return _NAVIGATION_PHASE_SEQUENCE.index(current_phase)
    except ValueError:
        return len(_NAVIGATION_PHASE_SEQUENCE) - 1


def _field_phase_index(
    field_id: str,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> int:
    canonical = api_parameter_id(field_id)
    phase_missing = planning.get("phase_missing") or {}
    if isinstance(phase_missing, dict):
        for index, phase_id in enumerate(_NAVIGATION_PHASE_SEQUENCE):
            fields = [api_parameter_id(str(item)) for item in (phase_missing.get(phase_id) or [])]
            if canonical in fields or field_id in fields:
                return index

    if canonical in {"corrosion_allowance"}:
        return _NAVIGATION_PHASE_SEQUENCE.index(NavigationPhase.DEFINITION_EQUATION_COMPLETION.value)
    if canonical in {
        "allowable_stress",
        LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
        "weld_joint_efficiency",
        "weld_strength_reduction_factor_w",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_y",
        "temperature_coefficient_Y",
    }:
        return _NAVIGATION_PHASE_SEQUENCE.index(NavigationPhase.COEFFICIENT_RESOLUTION.value)

    if reader is not None:
        from engine.reference.parameter_keys import load_parameter_node_metadata, param_node_id_for_input

        metadata = load_parameter_node_metadata(param_node_id_for_input(canonical))
        nested = (metadata or {}).get("metadata") or {}
        if isinstance(nested, dict):
            resolution = nested.get("resolution") or {}
            if isinstance(resolution, dict) and str(resolution.get("method") or "").strip() == "lookup":
                return _NAVIGATION_PHASE_SEQUENCE.index(NavigationPhase.COEFFICIENT_RESOLUTION.value)
            if str(nested.get("role") or "").strip() == "path_decision":
                return _NAVIGATION_PHASE_SEQUENCE.index(NavigationPhase.PATH_DECISIONS.value)
            if str(nested.get("kind") or "").strip() == "assumption":
                return _NAVIGATION_PHASE_SEQUENCE.index(NavigationPhase.EXPANSION_ASSUMPTIONS.value)

    if canonical.endswith("_section"):
        return _NAVIGATION_PHASE_SEQUENCE.index(NavigationPhase.EXPANSION_ASSUMPTIONS.value)

    return _NAVIGATION_PHASE_SEQUENCE.index(NavigationPhase.PARAMETER_GATHERING.value)


def _reveal_goal_prefix_fields(
    task: Task,
    planning: dict[str, Any],
    revealed: set[str],
    *,
    reader: StandardsReader | None = None,
) -> None:
    """Reveal upcoming gatherable fields on the path up to the active goal."""
    from engine.planner.goal_navigation import next_actionable_goal
    from models.goal import goal_parameter_key

    step_order = collection_step_order(task, planning, reader=reader)
    if not step_order:
        return

    touch_indices: list[int] = []
    for item in revealed:
        index = _step_order_index(step_order, item)
        if index < 999_999:
            touch_indices.append(index)

    goal = next_actionable_goal(task)
    if goal is not None:
        param = goal_parameter_key(goal)
        for candidate in (param, composer_parameter_id(task, param), api_parameter_id(param)):
            index = _step_order_index(step_order, candidate)
            if index < 999_999:
                touch_indices.append(index)

    if not touch_indices:
        return

    max_idx = max(touch_indices)
    current_idx = _current_phase_index(planning)
    for step_id in step_order:
        if _step_order_index(step_order, step_id) > max_idx:
            break
        if step_id in HIDDEN_TIMELINE_INPUTS:
            continue
        if not step_applies_for_timeline(task, step_id):
            continue
        if _field_phase_index(step_id, planning, reader=reader) > current_idx:
            continue
        if reader is not None and not _is_composer_timeline_field(step_id, reader):
            continue
        revealed.add(step_id)
        revealed.add(api_parameter_id(step_id))


def _is_composer_timeline_field(field_id: str, reader: StandardsReader) -> bool:
    from engine.reference.parameter_composer_spec import build_composer_parameter_spec

    try:
        spec = build_composer_parameter_spec(field_id, reader=reader)
    except Exception:
        return True
    if not spec:
        return False
    return str(spec.get("type") or "").strip().lower() != "hidden"


def _consolidate_timeline_parameter_aliases(revealed: set[str]) -> None:
    consolidated = consolidate_timeline_row_ids(revealed)
    revealed.clear()
    revealed.update(consolidated)


def _sort_ids_by_step_order(ids: set[str], step_order: tuple[str, ...]) -> list[str]:
    return sorted(ids, key=lambda step_id: (_step_order_index(step_order, step_id), step_id))


def _insert_new_timeline_ids(
    ordered: list[str],
    new_ids: set[str],
    step_order: tuple[str, ...],
) -> None:
    for new_id in _sort_ids_by_step_order(new_ids, step_order):
        new_idx = _step_order_index(step_order, new_id)
        insert_at = len(ordered)
        for position, existing in enumerate(ordered):
            if _step_order_index(step_order, existing) > new_idx:
                insert_at = position
                break
        ordered.insert(insert_at, new_id)


def _order_revealed_ids(
    task: Task,
    revealed: set[str],
    *,
    planning: dict[str, Any],
    reader: StandardsReader | None = None,
) -> list[str]:
    hidden = HIDDEN_TIMELINE_INPUTS
    revealed_visible = {step_id for step_id in revealed if step_id not in hidden}
    step_order = collection_step_order(task, planning, reader=reader)

    stored = task.outputs.get("timeline_input_order")
    if isinstance(stored, list):
        ordered: list[str] = []
        seen: set[str] = set()
        for step_id in stored:
            if step_id in revealed_visible and step_id not in seen:
                ordered.append(step_id)
                seen.add(step_id)
        for step_id in step_order:
            if step_id in revealed_visible and step_id not in seen:
                ordered.append(step_id)
                seen.add(step_id)
        new_ids = revealed_visible.difference(seen)
        if new_ids:
            _insert_new_timeline_ids(ordered, new_ids, tuple(step_order))
        return ordered

    ordered = [step_id for step_id in step_order if step_id in revealed_visible]
    remaining = sorted(
        revealed_visible.difference(ordered),
        key=lambda item: (_step_order_index(tuple(step_order), item), item),
    )
    ordered.extend(remaining)
    return ordered


def legacy_timeline_revealed_input_ids(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    phase_missing = planning.get("phase_missing") or {}
    current_phase = str(planning.get("current_phase") or "")

    revealed: set[str] = set()
    for input_id in task.fact_store.active_facts():
        if input_id not in HIDDEN_TIMELINE_INPUTS:
            revealed.add(input_id)

    if current_phase and isinstance(phase_missing, dict):
        for phase in _NAVIGATION_PHASE_SEQUENCE:
            if phase == NavigationPhase.READY.value:
                break
            fields = phase_missing.get(phase) or []
            if isinstance(fields, list):
                revealed.update(str(item) for item in fields)
            if phase == current_phase:
                break
    else:
        for key in ("missing_inputs", "missing_assumptions"):
            revealed.update(
                str(item)
                for item in (planning.get(key) or [])
                if str(item) not in HIDDEN_TIMELINE_INPUTS
            )

    if task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None:
        revealed.add("allowable_stress")

    if reader is not None:
        revealed.update(_navigation_fields_through_current_phase(task, planning, reader=reader))
    _reveal_goal_prefix_fields(task, planning, revealed, reader=reader)

    for source in (planning.get("collection_field_order"), task.outputs.get("collection_field_order")):
        if isinstance(source, list):
            for field_id in source:
                field_name = str(field_id).strip()
                if not field_name or field_name in HIDDEN_TIMELINE_INPUTS:
                    continue
                if step_applies_for_timeline(task, field_name):
                    revealed.add(field_name)

    ensure_diameter_timeline_pair(task, revealed)
    _consolidate_timeline_parameter_aliases(revealed)

    revealed = {
        step_id
        for step_id in revealed
        if step_id not in HIDDEN_TIMELINE_INPUTS and step_applies_for_timeline(task, step_id)
    }
    return _order_revealed_ids(task, revealed, planning=planning, reader=reader)
