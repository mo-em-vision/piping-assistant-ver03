"""Dynamic workflow timeline and revealed parameter ordering."""



from __future__ import annotations



from typing import TYPE_CHECKING, Any



from engine.graph.graph_timeline import graph_input_step_order, graph_step_titles

from engine.navigation import (

    HIDDEN_TIMELINE_INPUTS,

    collect_all_missing,

    collection_step_order,

    composer_parameter_id,

    composer_parameter_ids,

    hidden_timeline_inputs,

    is_mawp_task,

    is_pipe_wall_thickness_task,

    pipe_wall_step_applies,

    pipe_wall_uses_inside_diameter,

    step_applies_for_timeline,

    submittable_parameter_ids,

    timeline_revealed_input_ids,

    timeline_step_id_for_parameter,

    uses_planner_input_projection,

)

from engine.reference.parameter_keys import api_parameter_id

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



# Backward-compatible private aliases for API modules that import underscore names.

_HIDDEN_TIMELINE_INPUTS = HIDDEN_TIMELINE_INPUTS

_pipe_wall_uses_inside_diameter = pipe_wall_uses_inside_diameter

_pipe_wall_step_applies = pipe_wall_step_applies

_hidden_timeline_inputs = hidden_timeline_inputs

_step_applies_for_timeline = step_applies_for_timeline





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

    if pipe_wall_uses_inside_diameter(task):

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

    hidden = hidden_timeline_inputs(task)

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





def revealed_pipe_wall_input_ids(

    task: Task,

    planning: dict[str, Any],

    *,

    reader: StandardsReader | None = None,

) -> list[str]:

    """Input ids that should appear in timeline and parameter state for the active path."""

    if uses_planner_input_projection(task):

        return timeline_revealed_input_ids(task, planning, reader=reader)

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

        if step_id not in HIDDEN_TIMELINE_INPUTS and pipe_wall_step_applies(task, step_id)

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





def _plan_field_resolved(task: Task, field: str) -> bool:
    """Return True when EngineeringPlan marks the parameter requirement resolved."""
    from engine.planner.plan_selection import engineering_plan_for_task

    plan = engineering_plan_for_task(task)
    if plan is None:
        return False
    canonical = api_parameter_id(field)
    for req in plan.requirements.values():
        if req.field not in {field, canonical}:
            continue
        if req.status == "resolved":
            return True
    return False





def _timeline_input_step_resolved(
    task: Task,
    step_id: str,
    all_missing: set[str],
) -> bool:
    """Timeline input done: plan requirement resolved or confirmed fact — not calc outputs."""
    from engine.reference.parameter_keys import active_fact_for_key

    canonical_id = api_parameter_id(step_id)
    existing = active_fact_for_key(task, canonical_id)
    if existing is not None:
        if _is_proposed_default(existing):
            return False
        missing_canonical = {api_parameter_id(item) for item in all_missing}
        if fact_scalar_value(existing) is not None and canonical_id not in missing_canonical:
            return True
    return _plan_field_resolved(task, canonical_id)





def pipe_wall_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:

    return _timeline_input_step_resolved(task, step_id, all_missing)





def mawp_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:

    if _timeline_input_step_resolved(task, step_id, all_missing):

        return True



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


