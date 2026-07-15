"""Dynamic workflow timeline and revealed parameter ordering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.graph.assumption_checker import field_value
from engine.graph.navigation_phases import allowed_fields_for_phase
from engine.graph.graph_timeline import graph_input_step_order, graph_step_titles
from engine.graph.workflow_navigation import workflow_collection_field_order
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.reference.parameter_keys import (
    MATERIAL_GRADE_KEY,
    api_parameter_id,
    canonical_parameter_key,
    is_material_grade_parameter,
)
from engine.state.goal_projection import missing_input_keys
from engine.state.task_facts import active_facts
from models.fact import Fact, FactClass, ValidationStatus, fact_scalar_value
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


_HIDDEN_TIMELINE_INPUTS = frozenset(
    {"d_input_mode", "thin_wall", "outside_diameter__resolution_branch"}
)


def is_mawp_task(task: Task) -> bool:
    workflow = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if workflow in {MAWP_DESIGN, "B313-MAWP-DESIGN", "mawp_design"}:
        return True
    return "mawp" in workflow.lower()


def is_pipe_wall_thickness_task(task: Task) -> bool:
    if is_mawp_task(task):
        return False
    workflow = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if workflow in {PIPE_WALL_THICKNESS_DESIGN, "B313-PIPE-WALL-THICKNESS-DESIGN"}:
        return True
    if "pipe_wall_thickness" in workflow.lower():
        return True
    loading = task.fact_store.active_fact("pressure_loading")
    loading_value = fact_scalar_value(loading) if loading is not None else None
    return loading_value in {"internal_pressure", "external_pressure"}


def collect_all_missing(planning: dict[str, Any]) -> set[str]:
    all_missing: set[str] = set()
    for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
        all_missing.update(str(item) for item in (planning.get(key) or []))
    phase_missing = planning.get("phase_missing") or {}
    if isinstance(phase_missing, dict):
        for fields in phase_missing.values():
            if isinstance(fields, list):
                all_missing.update(str(item) for item in fields)
    return all_missing


def _task_workflow_id(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")


def _step_order_index(step_order: tuple[str, ...], step_id: str) -> int:
    canonical_order = tuple(api_parameter_id(item) for item in step_order)
    try:
        return canonical_order.index(api_parameter_id(step_id))
    except ValueError:
        return 999_999


def _timeline_row_id(step_id: str) -> str:
    return api_parameter_id(step_id)


def _merge_step_orders(*orders: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for order in orders:
        for step_id in order:
            if step_id and step_id not in seen:
                merged.append(step_id)
                seen.add(step_id)
    return tuple(merged)


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


def collection_step_order(
    task: Task,
    planning: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> tuple[str, ...]:
    """Parameter ids in planner order: navigation scaffold, graph expansion, then goals."""
    planning = planning or {}

    nav_order = _resolved_navigation_field_order(task, planning, reader=reader)
    if nav_order:
        return nav_order

    graph_order = _resolved_graph_input_order(task, planning, reader=reader)
    if graph_order:
        return graph_order

    goal_order = _planner_goal_sequence_order(task)
    if goal_order:
        return goal_order

    from engine.planner.goal_navigation import goal_collection_parameter_ids

    fallback = goal_collection_parameter_ids(task)
    if fallback:
        return tuple(fallback)

    return ()


def parameter_collection_index(
    task: Task,
    planning: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, int]:
    """Lookup index for sorting parameters by planner presentation order."""
    step_order = collection_step_order(task, planning, reader=reader)
    index: dict[str, int] = {}
    for position, step_id in enumerate(step_order):
        index.setdefault(api_parameter_id(step_id), position)
    return index


def _navigation_fields_through_current_phase(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None,
) -> set[str]:
    """Navigation-config fields for the active phase and all earlier phases."""
    workflow_id = _task_workflow_id(task)
    if not workflow_id or reader is None:
        return set()
    try:
        from engine.graph.workflow_navigation import load_workflow_navigation

        config = load_workflow_navigation(reader, workflow_id)
    except Exception:
        return set()

    current_phase = str(planning.get("current_phase") or "")
    fields: set[str] = set()
    for phase, phase_fields in config.phase_order:
        if phase == NavigationPhase.READY.value:
            break
        for field in phase_fields:
            fields.add(str(field))
        if phase == current_phase:
            break
    return fields


def _reveal_planner_sequence_prefix(
    task: Task,
    planning: dict[str, Any],
    revealed: set[str],
    *,
    reader: StandardsReader | None = None,
) -> None:
    """Include expansion-sequence parameters from the first through the active planner ask."""
    step_order = collection_step_order(task, planning, reader=reader)
    if not step_order:
        return

    touch_indices: list[int] = []
    for item in revealed:
        index = _step_order_index(step_order, item)
        if index < 999_999:
            touch_indices.append(index)

    from engine.planner.goal_navigation import next_actionable_goal
    from models.goal import goal_parameter_key

    goal = next_actionable_goal(task)
    if goal is not None:
        param = goal_parameter_key(goal)
        for candidate in (param, composer_parameter_id(task, param), _timeline_row_id(param)):
            index = _step_order_index(step_order, candidate)
            if index < 999_999:
                touch_indices.append(index)

    if not touch_indices:
        return

    max_idx = max(touch_indices)
    for step_id in step_order:
        if _step_order_index(step_order, step_id) > max_idx:
            break
        revealed.add(step_id)
        revealed.add(_timeline_row_id(step_id))


def _ensure_diameter_timeline_fields(task: Task, revealed: set[str]) -> None:
    """Keep NPS and outside diameter visible together on the standard pipe-wall path."""
    if _pipe_wall_uses_inside_diameter(task):
        return
    if "nominal_pipe_size" in revealed or "outside_diameter" in revealed:
        revealed.add("nominal_pipe_size")
        revealed.add("outside_diameter")


def _consolidate_timeline_parameter_aliases(revealed: set[str]) -> None:
    """Collapse legacy aliases to canonical PARAM node keys for API payloads."""
    canonical = {api_parameter_id(step_id) for step_id in revealed}
    revealed.clear()
    revealed.update(canonical)


def _sort_ids_by_step_order(ids: set[str], step_order: tuple[str, ...]) -> list[str]:
    return sorted(ids, key=lambda step_id: (_step_order_index(step_order, step_id), step_id))


def _insert_new_timeline_ids(
    ordered: list[str],
    new_ids: set[str],
    step_order: tuple[str, ...],
) -> None:
    """Place newly revealed ids by collection order without reshuffling existing rows."""
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
    hidden = _hidden_timeline_inputs(task)
    revealed_visible = {step_id for step_id in revealed if step_id not in hidden}
    step_order = collection_step_order(task, planning, reader=reader)

    stored = task.outputs.get("timeline_input_order")
    if isinstance(stored, list):
        ordered: list[str] = []
        seen: set[str] = set()
        for step_id in stored:
            timeline_id = _timeline_row_id(str(step_id))
            if timeline_id in revealed_visible and timeline_id not in seen:
                ordered.append(timeline_id)
                seen.add(timeline_id)
        new_ids = revealed_visible.difference(seen)
        if new_ids:
            _insert_new_timeline_ids(ordered, new_ids, step_order)
        return ordered

    if not step_order:
        return sorted(revealed_visible)

    ordered: list[str] = []
    seen: set[str] = set()
    for step_id in step_order:
        timeline_id = _timeline_row_id(step_id)
        if timeline_id in revealed_visible and timeline_id not in seen:
            ordered.append(timeline_id)
            seen.add(timeline_id)
    new_ids = revealed_visible.difference(seen)
    if new_ids:
        _insert_new_timeline_ids(ordered, new_ids, step_order)
    return ordered


def sync_timeline_input_order(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> None:
    """Persist timeline row order: keep existing rows, append newly revealed inputs at the bottom."""
    if is_mawp_task(task):
        revealed = revealed_mawp_input_ids(task, planning, reader=reader)
    else:
        revealed = revealed_pipe_wall_input_ids(task, planning, reader=reader)
    task.outputs["timeline_input_order"] = revealed


def _pipe_wall_uses_inside_diameter(task: Task) -> bool:
    return field_value("inside_diameter", active_facts(task)) is not None


def _pipe_wall_step_applies(task: Task, step_id: str) -> bool:
    if is_mawp_task(task):
        return True
    if _pipe_wall_uses_inside_diameter(task):
        return step_id not in {"nominal_pipe_size", "outside_diameter"}
    return step_id != "inside_diameter"


def composer_parameter_id(task: Task, parameter_id: str) -> str:
    """Map graph parameter ids to the parameter id shown in the workflow composer."""
    return parameter_id


def composer_parameter_ids(task: Task, parameter_ids: list[str]) -> list[str]:
    mapped: list[str] = []
    for parameter_id in parameter_ids:
        resolved = composer_parameter_id(task, parameter_id)
        if resolved not in mapped:
            mapped.append(resolved)
    return mapped


def timeline_step_id_for_parameter(
    task: Task,
    parameter_id: str,
    *,
    revealed: list[str] | None = None,
) -> str:
    """Map composer/current_ask parameter ids to timeline row ids."""
    parameter_id = api_parameter_id(parameter_id)
    candidates = [parameter_id]
    if parameter_id in {"nominal_pipe_size", "outside_diameter"}:
        candidates.extend(["nominal_pipe_size", "outside_diameter"])
    if revealed:
        revealed_set = {api_parameter_id(item) for item in revealed}
        for candidate in candidates:
            if api_parameter_id(candidate) in revealed_set:
                return api_parameter_id(candidate)
    return parameter_id


def revealed_pipe_wall_input_ids(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    """Input ids that should appear in timeline and parameter state for the active path."""
    phase_missing = planning.get("phase_missing") or {}
    current_phase = str(planning.get("current_phase") or "")

    revealed: set[str] = set()
    for input_id in task.fact_store.active_facts():
        if input_id not in _HIDDEN_TIMELINE_INPUTS:
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
                if str(item) not in _HIDDEN_TIMELINE_INPUTS
            )

    if task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None:
        revealed.add("allowable_stress")

    if reader is not None:
        revealed.update(
            _navigation_fields_through_current_phase(task, planning, reader=reader)
        )
    else:
        _reveal_planner_sequence_prefix(task, planning, revealed, reader=reader)
    _ensure_diameter_timeline_fields(task, revealed)
    _consolidate_timeline_parameter_aliases(revealed)

    revealed = {
        step_id
        for step_id in revealed
        if step_id not in _HIDDEN_TIMELINE_INPUTS and _pipe_wall_step_applies(task, step_id)
    }
    return _order_revealed_ids(task, revealed, planning=planning, reader=reader)


def revealed_mawp_input_ids(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    """MAWP timeline uses the same graph-driven reveal rules as other workflows."""
    return revealed_pipe_wall_input_ids(task, planning, reader=reader)


def _workflow_id(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")


def _hidden_timeline_inputs(task: Task) -> frozenset[str]:
    return _HIDDEN_TIMELINE_INPUTS


def _resolve_graph_step_titles(
    task: Task,
    planning: dict[str, Any] | None,
    *,
    reader: StandardsReader | None,
) -> dict[str, str]:
    if planning:
        titles = planning.get("graph_step_titles")
        if isinstance(titles, dict) and titles:
            return {str(key): str(value) for key, value in titles.items()}
    cached = task.outputs.get("graph_step_titles")
    if isinstance(cached, dict) and cached:
        return {str(key): str(value) for key, value in cached.items()}
    if reader is None:
        return {}
    try:
        from engine.graph.graph_engine import GraphEngine, normalize_root_id

        workflow_id = _task_workflow_id(task)
        if not workflow_id:
            return {}
        plan = GraphEngine().build_plan(
            task_id=task.task_id,
            root_id=normalize_root_id(workflow_id),
            inputs=dict(active_facts(task)),
            reader=reader,
        )
        return graph_step_titles(reader, plan)
    except Exception:
        return {}


def _step_title_from_graph(
    task: Task,
    step_id: str,
    planning: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> str:
    from engine.reports.block_renderer import has_timeline_input_label, input_label_for_timeline

    canonical_id = api_parameter_id(step_id)
    if has_timeline_input_label(canonical_id):
        return input_label_for_timeline(canonical_id)
    titles = _resolve_graph_step_titles(task, planning, reader=reader)
    if canonical_id in titles:
        return titles[canonical_id]
    if step_id in titles:
        return titles[step_id]
    return input_label_for_timeline(canonical_id)


def revealed_input_ids(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    if is_mawp_task(task):
        return revealed_mawp_input_ids(task, planning, reader=reader)
    return revealed_pipe_wall_input_ids(task, planning, reader=reader)


def _step_applies_for_timeline(task: Task, step_id: str) -> bool:
    if is_pipe_wall_thickness_task(task):
        return _pipe_wall_step_applies(task, step_id)
    return True


def _ordered_submittable_ids(
    task: Task,
    candidates: set[str],
    planning: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    hidden = _hidden_timeline_inputs(task)
    step_order = collection_step_order(task, planning, reader=reader)
    ordered: list[str] = []
    for step_id in step_order:
        if step_id in candidates and _step_applies_for_timeline(task, step_id):
            ordered.append(step_id)
    for item in _sort_ids_by_step_order(candidates.difference(ordered), step_order):
        if item not in hidden and _step_applies_for_timeline(task, item):
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
        workflow = "mawp_design" if is_mawp_task(task) else None
        return allowed_fields_for_phase(NavigationPhase(current_phase), workflow=workflow)
    except ValueError:
        return frozenset()


def _unconfirmed_proposed_defaults_for_phase(
    task: Task,
    *,
    allowed_ids: frozenset[str],
    phase_fields: set[str],
    step_order: tuple[str, ...] = (),
) -> list[str]:
    hidden = _hidden_timeline_inputs(task)
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
    from engine.state.task_facts import active_facts

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
    return _with_resolution_branch_submittable(
        task,
        _raw_submittable_parameter_ids(task, planning),
    )


def _raw_submittable_parameter_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    """Parameters the user may submit on the current navigation phase."""
    from engine.planner.goal_navigation import goal_guided_parameter_ids, goal_parameter_key, next_actionable_goal

    edit_session = task.outputs.get("edit_session")
    if isinstance(edit_session, dict) and edit_session.get("parameter"):
        return [str(edit_session["parameter"])]

    hidden = _hidden_timeline_inputs(task)
    goal_params = goal_guided_parameter_ids(task)
    if goal_params:
        filtered = [
            param
            for param in goal_params
            if param not in hidden and _step_applies_for_timeline(task, param)
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
                    and _step_applies_for_timeline(task, str(item))
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
            and _step_applies_for_timeline(task, str(item))
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
            if not _step_applies_for_timeline(task, item_id):
                continue
            if item_id not in requested_ids:
                requested_ids.append(item_id)

    for input_id, existing in task.fact_store.active_facts().items():
        if (
            input_id not in hidden
            and _is_proposed_default(existing)
            and input_id not in requested_ids
            and _step_applies_for_timeline(task, input_id)
        ):
            requested_ids.append(input_id)

    return composer_parameter_ids(task, requested_ids)


def workflow_step_title(
    task: Task,
    step_id: str,
    planning: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> str:
    return _step_title_from_graph(task, step_id, planning, reader=reader)


def pipe_wall_step_title(
    step_id: str,
    planning: dict[str, Any] | None = None,
    *,
    task: Task | None = None,
    reader: StandardsReader | None = None,
) -> str:
    if task is not None:
        return _step_title_from_graph(task, step_id, planning, reader=reader)
    if planning:
        graph_titles = planning.get("graph_step_titles")
        if isinstance(graph_titles, dict) and step_id in graph_titles:
            return str(graph_titles[step_id])
    return step_id.replace("_", " ").title()


def mawp_step_title(
    step_id: str,
    planning: dict[str, Any] | None = None,
    *,
    task: Task | None = None,
    reader: StandardsReader | None = None,
) -> str:
    if task is not None:
        return _step_title_from_graph(task, step_id, planning, reader=reader)
    if planning:
        graph_titles = planning.get("graph_step_titles")
        if isinstance(graph_titles, dict) and step_id in graph_titles:
            return str(graph_titles[step_id])
    return step_id.replace("_", " ").title()


def workflow_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    if is_mawp_task(task):
        return mawp_input_step_done(task, step_id, all_missing)
    return pipe_wall_input_step_done(task, step_id, all_missing)


def _is_proposed_default(fact: Fact) -> bool:
    return (
        fact.fact_class == FactClass.DEFAULT_CONFIRMED
        and fact.validation.status == ValidationStatus.PENDING
    )


def pipe_wall_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    from engine.reference.parameter_keys import active_fact_for_key

    canonical_id = api_parameter_id(step_id)
    existing = active_fact_for_key(task, canonical_id)
    if existing is not None:
        if _is_proposed_default(existing):
            return False
        if fact_scalar_value(existing) is not None and canonical_id not in {
            api_parameter_id(item) for item in all_missing
        }:
            return True

    if canonical_id == "allowable_stress":
        return task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None

    return False


def mawp_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    existing = task.fact_store.active_fact(step_id)
    if existing is not None:
        if _is_proposed_default(existing):
            return False
        if fact_scalar_value(existing) is not None and step_id not in all_missing:
            return True

    if step_id == "allowable_stress":
        return task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None

    od = task.fact_store.active_fact("outside_diameter")
    if step_id == "outside_diameter" and od is not None:
        if (
            fact_scalar_value(od) is not None
            and not _is_proposed_default(od)
            and step_id not in all_missing
        ):
            return True

    thickness = task.fact_store.active_fact("actual_wall_thickness")
    if step_id == "actual_wall_thickness" and thickness is not None:
        if (
            fact_scalar_value(thickness) is not None
            and not _is_proposed_default(thickness)
            and step_id not in all_missing
        ):
            return True

    return False
