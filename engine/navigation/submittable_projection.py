"""Submittable parameter projection and collection ordering for navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.graph.navigation_phases import allowed_fields_for_phase
from engine.graph.graph_timeline import graph_input_step_order
from engine.graph.workflow_navigation import workflow_collection_field_order
from engine.navigation.composer_mapping import composer_parameter_id, composer_parameter_ids
from engine.navigation.timeline_projection import (
    hidden_timeline_inputs,
    step_applies_for_timeline,
    uses_inside_diameter_path,
)
from engine.reference.parameter_keys import api_parameter_id
from engine.state.goal_projection import missing_input_keys
from engine.state.task_facts import active_facts
from models.fact import Fact, FactClass, ValidationStatus
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
    NavigationPhase.READY.value,
)


def _prioritize_submittable_by_phase(
    planning: dict[str, Any],
    candidates: list[str],
) -> list[str]:
    """Pick the earliest navigation-phase missing field among candidates."""
    if not candidates:
        return []
    phase_missing = planning.get("phase_missing") or {}
    if not isinstance(phase_missing, dict):
        return candidates
    candidate_set = set(candidates)
    for phase_id in _NAVIGATION_PHASE_SEQUENCE:
        for field in phase_missing.get(phase_id) or []:
            field_id = str(field)
            if field_id in candidate_set:
                return [field_id]
    return candidates


def _task_workflow_id(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")


def _step_order_index(step_order: tuple[str, ...], step_id: str) -> int:
    canonical_order = tuple(api_parameter_id(item) for item in step_order)
    try:
        return canonical_order.index(api_parameter_id(step_id))
    except ValueError:
        return 999_999


def _resolve_graph_input_order(task: Task, reader: StandardsReader) -> tuple[str, ...]:
    from engine.graph.graph_engine import GraphEngine, normalize_root_id

    workflow_id = _task_workflow_id(task)
    if not workflow_id:
        return ()
    try:
        plan = GraphEngine().build_plan(
            task_id=task.task_id,
            root_id=normalize_root_id(workflow_id),
            inputs=dict(active_facts(task)),
            reader=reader,
        )
    except Exception:
        return ()
    return graph_input_step_order(reader, plan)


def _resolve_collection_field_order(task: Task, reader: StandardsReader) -> tuple[str, ...]:
    workflow_id = _task_workflow_id(task)
    if not workflow_id:
        return ()
    try:
        return workflow_collection_field_order(reader, workflow_id)
    except Exception:
        return ()


def _resolved_graph_input_order(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> tuple[str, ...]:
    for source in (planning.get("graph_input_order"), task.outputs.get("graph_input_order")):
        if isinstance(source, list) and source:
            return tuple(str(item) for item in source if str(item).strip())
    if reader is not None:
        return _resolve_graph_input_order(task, reader)
    return ()


def _resolved_navigation_field_order(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> tuple[str, ...]:
    for source in (planning.get("collection_field_order"), task.outputs.get("collection_field_order")):
        if isinstance(source, list) and source:
            return tuple(str(item) for item in source if str(item).strip())
    if reader is not None:
        return _resolve_collection_field_order(task, reader)
    return ()


def _planning_phase_field_order(planning: dict[str, Any]) -> tuple[str, ...]:
    phase_missing = planning.get("phase_missing") or {}
    if not isinstance(phase_missing, dict):
        return ()
    ordered: list[str] = []
    seen: set[str] = set()
    for phase_id in _NAVIGATION_PHASE_SEQUENCE:
        for field in phase_missing.get(phase_id) or []:
            field_id = str(field).strip()
            if field_id and field_id not in seen:
                seen.add(field_id)
                ordered.append(field_id)
    return tuple(ordered)


def _workflow_expansion_field_order(
    task: Task,
    *,
    reader: StandardsReader | None = None,
) -> tuple[str, ...]:
    if reader is None:
        return ()
    from engine.graph.expansion_policy import collect_workflow_expansion_fields
    from engine.graph.graph_engine import normalize_root_id, resolve_workflow_node_id
    from engine.graph.graph_store import GraphStore

    workflow_id = _task_workflow_id(task)
    if not workflow_id:
        return ()
    store = GraphStore(reader.pack_root)
    if not store.available:
        return ()
    slug = normalize_root_id(workflow_id)
    resolved = resolve_workflow_node_id(slug)
    root_id = resolved if store.get_node(resolved) is not None else slug
    return tuple(collect_workflow_expansion_fields(store, root_id))


def _merge_step_orders(*sources: tuple[str, ...]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for source in sources:
        for field in source:
            field_id = str(field).strip()
            if not field_id or field_id in seen:
                continue
            seen.add(field_id)
            ordered.append(field_id)
    return tuple(ordered)


def _planner_goal_sequence_order(task: Task) -> tuple[str, ...]:
    """Parameter ids in goal-tree order (planner build sequence from phased expansion)."""
    from models.goal import GoalClass, goal_parameter_key

    roots = task.goal_store.roots()
    if not roots:
        return ()
    children = [
        goal
        for goal in task.goal_store.children(roots[0].id)
        if goal.goal_class in {GoalClass.INPUT, GoalClass.SELECTION, GoalClass.LOOKUP}
    ]
    children.sort(
        key=lambda goal: (int(goal.metadata.get("order") or 10_000), goal.key),
    )
    ordered: list[str] = []
    seen: set[str] = set()
    for goal in children:
        param = goal_parameter_key(goal)
        if param in seen:
            continue
        seen.add(param)
        ordered.append(param)
    return tuple(ordered)


def _split_graph_input_order(graph_order: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    from engine.reference.parameter_keys import load_parameter_node_metadata, param_node_id_for_input
    from engine.reference.parameter_metadata import is_path_decision_parameter

    path_decisions: list[str] = []
    parameter_gathering: list[str] = []
    for field_id in graph_order:
        metadata = load_parameter_node_metadata(param_node_id_for_input(field_id))
        if is_path_decision_parameter(metadata):
            path_decisions.append(field_id)
        else:
            parameter_gathering.append(field_id)
    return tuple(path_decisions), tuple(parameter_gathering)


def _inject_diameter_gathering_order(step_order: tuple[str, ...]) -> tuple[str, ...]:
    """Keep NPS/outside-diameter pair together after design pressure when both appear."""
    anchor = "internal_design_gage_pressure"
    if anchor not in step_order:
        return step_order
    diameter_fields = [field for field in ("nominal_pipe_size", "outside_diameter") if field in step_order]
    if not diameter_fields:
        return step_order
    fields = list(step_order)
    insert_at = fields.index(anchor) + 1
    for diam in diameter_fields:
        fields.remove(diam)
    for offset, diam in enumerate(("nominal_pipe_size", "outside_diameter")):
        if diam in diameter_fields:
            fields.insert(insert_at + offset, diam)
    return tuple(fields)


def _inject_pressure_temperature_order(step_order: tuple[str, ...]) -> tuple[str, ...]:
    """Collect design pressure before design temperature in timeline ordering."""
    if "design_temperature" not in step_order:
        return step_order
    fields = list(step_order)
    insert_at = fields.index("design_temperature")
    for pressure_field in ("internal_design_gage_pressure", "external_design_gage_pressure"):
        if pressure_field in fields:
            fields.remove(pressure_field)
            fields.insert(insert_at, pressure_field)
            insert_at += 1
    return tuple(fields)


def _inject_material_temperature_order(step_order: tuple[str, ...]) -> tuple[str, ...]:
    """Keep material selection before design temperature in timeline ordering."""
    if "material_grade" not in step_order or "design_temperature" not in step_order:
        return step_order
    fields = list(step_order)
    fields.remove("design_temperature")
    fields.insert(fields.index("material_grade") + 1, "design_temperature")
    return tuple(fields)


def collection_step_order(
    task: Task,
    planning: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> tuple[str, ...]:
    """Parameter ids in expansion, navigation, graph, and goal presentation order."""
    planning = planning or {}
    from engine.planner.goal_navigation import goal_collection_parameter_ids

    explicit_nav = _resolved_navigation_field_order(task, planning, reader=reader)
    if explicit_nav:
        return _merge_step_orders(
            _workflow_expansion_field_order(task, reader=reader),
            explicit_nav,
        )

    for source in (planning.get("graph_input_order"), task.outputs.get("graph_input_order")):
        if isinstance(source, list) and source:
            explicit_graph = tuple(str(item) for item in source if str(item).strip())
            if explicit_graph:
                return _merge_step_orders(
                    _workflow_expansion_field_order(task, reader=reader),
                    explicit_graph,
                )

    graph_order = _resolved_graph_input_order(task, planning, reader=reader)
    path_order, gather_order = _split_graph_input_order(graph_order)

    return _inject_material_temperature_order(
        _inject_pressure_temperature_order(
            _inject_diameter_gathering_order(
                _merge_step_orders(
                    _workflow_expansion_field_order(task, reader=reader),
                    path_order,
                    gather_order,
                    _planning_phase_field_order(planning),
                    _planner_goal_sequence_order(task),
                    tuple(goal_collection_parameter_ids(task) or []),
                )
            )
        )
    )


def _sort_ids_by_step_order(ids: set[str], step_order: tuple[str, ...]) -> list[str]:
    return sorted(ids, key=lambda step_id: (_step_order_index(step_order, step_id), step_id))


def _ordered_submittable_ids(
    task: Task,
    candidates: set[str],
    planning: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    hidden = hidden_timeline_inputs(task)
    step_order = collection_step_order(task, planning, reader=reader)
    ordered: list[str] = []
    for step_id in step_order:
        if step_id in candidates and step_applies_for_timeline(task, step_id):
            ordered.append(step_id)
    for item in _sort_ids_by_step_order(candidates.difference(ordered), step_order):
        if item not in hidden and step_applies_for_timeline(task, item):
            ordered.append(item)
    return ordered


def _phase_allowed_input_ids(
    task: Task,
    current_phase: str,
    planning: dict[str, Any] | None = None,
) -> frozenset[str]:
    allowlists = (planning or {}).get("phase_allowed_fields")
    if isinstance(allowlists, dict) and current_phase in allowlists:
        return frozenset(str(item) for item in allowlists[current_phase] if str(item))
    try:
        workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
        return allowed_fields_for_phase(
            NavigationPhase(current_phase),
            workflow=workflow_id or None,
        )
    except ValueError:
        return frozenset()


def _is_proposed_default(fact: Fact) -> bool:
    return (
        fact.fact_class == FactClass.DEFAULT_CONFIRMED
        and fact.validation.status == ValidationStatus.PENDING
    )


def _unconfirmed_proposed_defaults_for_phase(
    task: Task,
    *,
    allowed_ids: frozenset[str],
    phase_fields: set[str],
    step_order: tuple[str, ...] = (),
) -> list[str]:
    hidden = hidden_timeline_inputs(task)
    permitted = allowed_ids | frozenset(step_order) | phase_fields
    extras: list[str] = []
    for input_id, existing in task.fact_store.active_facts().items():
        if (
            input_id in permitted
            and input_id not in phase_fields
            and input_id not in hidden
            and _is_proposed_default(existing)
        ):
            extras.append(input_id)
    return extras


def _with_resolution_branch_submittable(task: Task, parameter_ids: list[str]) -> list[str]:
    """Expose branch fact keys when the anchor parameter is submittable but branch is unset."""
    from engine.graph.resolution_branches import (
        active_resolution_branch_id,
        resolution_branch_fact_key,
    )

    if "outside_diameter" not in parameter_ids:
        return parameter_ids
    if active_resolution_branch_id("outside_diameter", active_facts(task)) is not None:
        return parameter_ids
    branch_key = resolution_branch_fact_key("outside_diameter")
    if branch_key in parameter_ids:
        return parameter_ids
    expanded = list(parameter_ids)
    anchor_index = expanded.index("outside_diameter")
    expanded.insert(anchor_index + 1, branch_key)
    return expanded


def submittable_parameter_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    """Parameters the user may submit on the current navigation phase."""
    edit_session = task.outputs.get("edit_session")
    if isinstance(edit_session, dict) and edit_session.get("parameter"):
        return composer_parameter_ids(task, [str(edit_session["parameter"])])

    from engine.planner.plan_selection import planner_submittable_fields_from_task

    planner_fields = planner_submittable_fields_from_task(task)
    if planner_fields is not None:
        return composer_parameter_ids(task, planner_fields)

    return _with_resolution_branch_submittable(
        task,
        legacy_submittable_parameter_ids(task, planning),
    )


def legacy_submittable_parameter_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    """Legacy/no-plan forward-submission projection."""
    return _raw_submittable_parameter_ids(task, planning)


def _raw_submittable_parameter_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    """Legacy forward-submission algorithm for tasks without Planner projection."""
    from engine.planner.goal_navigation import goal_guided_parameter_ids

    hidden = hidden_timeline_inputs(task)
    goal_params = goal_guided_parameter_ids(task)
    if goal_params:
        filtered = [
            param
            for param in goal_params
            if param not in hidden and step_applies_for_timeline(task, param)
        ]
        missing_keys = set(missing_input_keys(task))
        filtered = list(dict.fromkeys([*filtered, *[p for p in missing_keys if p not in hidden]]))
        if filtered:
            current_phase = str(planning.get("current_phase") or "")
            phase_missing = planning.get("phase_missing") or {}
            if isinstance(phase_missing, dict) and current_phase:
                phase_fields = [
                    str(item)
                    for item in (phase_missing.get(current_phase) or [])
                    if str(item) not in hidden
                    and step_applies_for_timeline(task, str(item))
                ]
                allowed_ids = _phase_allowed_input_ids(task, current_phase, planning)
                step_order = collection_step_order(task, planning)
                extras = _unconfirmed_proposed_defaults_for_phase(
                    task,
                    allowed_ids=allowed_ids,
                    phase_fields=set(phase_fields),
                    step_order=step_order,
                )
                ordered = _ordered_submittable_ids(
                    task,
                    set(filtered) | set(phase_fields) | set(extras),
                    planning,
                )
                ordered = _prioritize_submittable_by_phase(planning, ordered)
                return composer_parameter_ids(task, ordered)
            prioritized = _prioritize_submittable_by_phase(planning, filtered)
            return composer_parameter_ids(task, prioritized)

    phase_missing = planning.get("phase_missing") or {}
    current_phase = str(planning.get("current_phase") or "")
    if isinstance(phase_missing, dict) and current_phase:
        phase_fields = [
            str(item)
            for item in (phase_missing.get(current_phase) or [])
            if str(item) not in hidden
            and step_applies_for_timeline(task, str(item))
        ]
        if phase_fields:
            allowed_ids = _phase_allowed_input_ids(task, current_phase, planning)
            step_order = collection_step_order(task, planning)
            extras = _unconfirmed_proposed_defaults_for_phase(
                task,
                allowed_ids=allowed_ids,
                phase_fields=set(phase_fields),
                step_order=step_order,
            )
            return composer_parameter_ids(
                task,
                _ordered_submittable_ids(task, set(phase_fields) | set(extras), planning),
            )

    requested_ids: list[str] = []
    for key in ("missing_assumptions", "missing_execution_assumptions", "missing_inputs"):
        for item in planning.get(key) or []:
            item_id = str(item)
            if item_id in hidden:
                continue
            if not step_applies_for_timeline(task, item_id):
                continue
            if item_id not in requested_ids:
                requested_ids.append(item_id)

    for input_id, existing in task.fact_store.active_facts().items():
        if (
            input_id not in hidden
            and _is_proposed_default(existing)
            and input_id not in requested_ids
            and step_applies_for_timeline(task, input_id)
        ):
            requested_ids.append(input_id)

    return composer_parameter_ids(task, requested_ids)
