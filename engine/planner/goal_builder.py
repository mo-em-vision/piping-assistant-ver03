"""Build runtime goal trees from graph-driven workflow planning."""

from __future__ import annotations

from typing import Any

from engine.graph.navigation_phases import build_workflow_phased_navigation
from engine.graph.workflow_navigation import load_workflow_navigation
from engine.messaging.parameter_input_prompt import build_parameter_input_prompt
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.planner.workflow_goal_metadata import (
    lookup_fields_for_workflow,
    root_target_for_workflow,
    selection_fields_for_workflow,
    workflow_title_for_goal,
)
from engine.state.goal_satisfaction import refresh_goal_satisfaction
from engine.state.task_facts import active_facts
from engine.state.task_goals import clear_goal_store, expand_goal, store_goal
from models.goal import (
    calculation_goal,
    input_goal,
    lookup_goal,
    selection_goal,
)
from models.goal_store import GoalStore
from models.planning import NavigationPhase
from models.task import Task

_DEFAULT_ROOT_TARGET_FALLBACK = "required-wall-thickness"


def _short_label_for_field(field_id: str) -> str:
    from engine.planner.question_spec_builder import build_question_spec

    return build_question_spec(field_id).label


def _child_goal_for_field(
    *,
    field_id: str,
    phase: str,
    order: int,
    task: Task,
    workflow_id: str,
    root_id: str,
    selection_fields: frozenset[str],
    lookup_fields: frozenset[str],
) -> Any:
    name = _short_label_for_field(field_id)
    if field_id in selection_fields:
        return selection_goal(
            key=f"select-{field_id}",
            name=name,
            target_parameter=field_id,
            task_id=task.task_id,
            prompt="",
            workflow_id=workflow_id,
            parent_goal=root_id,
            phase=phase,
            order=order,
        )
    if field_id in lookup_fields:
        return lookup_goal(
            key=f"lookup-{field_id}",
            name=name,
            target_parameter=field_id,
            task_id=task.task_id,
            required_facts=["material_grade", "design_temperature"],
            workflow_id=workflow_id,
            parent_goal=root_id,
            phase=phase,
            order=order,
        )
    return input_goal(
        key=f"input-{field_id}",
        name=name,
        target_parameter=field_id,
        task_id=task.task_id,
        prompt="",
        workflow_id=workflow_id,
        parent_goal=root_id,
        phase=phase,
        order=order,
    )


def _build_with_engineering_plan(
    task: Task,
    reader: StandardsReader,
    *,
    preview: Any,
    phased: Any,
    existing_inputs: dict,
    path_decision: dict[str, str] | None,
) -> GoalStore | None:
    from engine.planner.engineering_plan_builder import build_engineering_plan
    from engine.planner.legacy_goal_adapter import (
        apply_engineering_plan_to_goal_store,
        store_engineering_plan_on_task,
    )

    plan = build_engineering_plan(
        task,
        reader,
        preview=preview,
        phased=phased,
        existing_inputs=existing_inputs,
        path_decision=path_decision,
    )
    if plan is None:
        return None
    store_engineering_plan_on_task(task, plan)
    return apply_engineering_plan_to_goal_store(task, plan)


def build_goal_tree(
    task: Task,
    reader: StandardsReader,
    *,
    preview: Any | None = None,
    question_map: dict[str, str] | None = None,
    phased: Any | None = None,
    root_slug: str | None = None,
) -> GoalStore:
    """Replace task.goal_store with a tree derived from graph planning state."""
    from engine.graph.graph_engine import GraphEngine, normalize_root_id

    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if not workflow_id:
        return task.goal_store

    slug = root_slug or normalize_root_id(workflow_id)
    graph = GraphTools(reader)
    existing_inputs = dict(active_facts(task))

    if preview is None:
        engine = GraphEngine()
        lazy_plan = engine.uses_micro_graph(reader, slug) and not engine.expansion_gate_ready(
            slug, reader, existing_inputs=existing_inputs
        )
        preview = graph.preview_plan(
            task_id=task.task_id,
            root_id=slug,
            inputs=existing_inputs,
            lazy=lazy_plan,
        )

    assumption_eval = graph.evaluate_assumptions(slug, existing_inputs=existing_inputs, plan=preview)
    expansion_eval = graph.evaluate_expansion_interactions(slug, existing_inputs=existing_inputs, plan=preview)
    missing_inputs = graph.required_user_inputs(
        slug,
        existing_inputs=set(existing_inputs.keys()),
        task_inputs=existing_inputs,
        plan=preview,
    )
    from api.workflow_timeline import composer_parameter_ids

    missing_inputs = composer_parameter_ids(task, missing_inputs)
    execution_eval = graph.evaluate_execution_assumptions(slug, existing_inputs=existing_inputs, plan=preview)
    from engine.graph.definition_equations import has_execution_trace, pending_definition_equation_inputs

    if has_execution_trace(task):
        for input_id in pending_definition_equation_inputs(
            task,
            reader,
            preview.execution_order,
        ):
            if input_id not in execution_eval.missing_fields:
                execution_eval.missing_fields.append(input_id)

    qmap: dict[str, str] = {}
    field_ids = list(
        dict.fromkeys(
            list(assumption_eval.missing_fields)
            + list(expansion_eval.missing_fields)
            + list(execution_eval.missing_fields)
            + list(missing_inputs)
        )
    )
    for field_id in field_ids:
        prompt = build_parameter_input_prompt(reader, task, field_id)
        if prompt:
            qmap[field_id] = prompt
    for eval_obj in (expansion_eval, assumption_eval, execution_eval):
        for field_id, question in eval_obj.field_questions.items():
            qmap.setdefault(field_id, question)
    if question_map:
        for field_id, question in question_map.items():
            if question:
                qmap[field_id] = question

    if phased is None:
        nav_config = load_workflow_navigation(reader, slug)
        phased = build_workflow_phased_navigation(
            config=nav_config,
            assumption_eval=assumption_eval,
            expansion_eval=expansion_eval,
            user_inputs=missing_inputs,
            execution_eval=execution_eval,
            question_map=qmap,
            existing_inputs=existing_inputs,
            post_thickness_outputs=dict(task.outputs),
            has_execution=has_execution_trace(task),
        )

    path_decision = task.outputs.get("path_decision")
    if not isinstance(path_decision, dict):
        path_decision = None

    plan_store = _build_with_engineering_plan(
        task,
        reader,
        preview=preview,
        phased=phased,
        existing_inputs=existing_inputs,
        path_decision=path_decision,
    )
    if plan_store is not None:
        return plan_store

    clear_goal_store(task)
    target = root_target_for_workflow(
        reader,
        workflow_id,
        fallback=_DEFAULT_ROOT_TARGET_FALLBACK,
    )
    selection_fields = selection_fields_for_workflow(reader, workflow_id)
    lookup_fields = lookup_fields_for_workflow(reader, workflow_id)
    title = workflow_title_for_goal(reader, workflow_id)
    root = calculation_goal(
        key="verify-engineering-goal",
        name=title,
        target_parameter=target,
        task_id=task.task_id,
        workflow_id=workflow_id,
    )
    root.provenance.created_from_user_intent = workflow_id
    store_goal(task, root, as_root=True)

    order = 0
    phase_missing: dict[str, list[str]] = dict(getattr(phased, "phase_missing", {}) or {})
    for phase in NavigationPhase:
        fields = phase_missing.get(phase.value, [])
        for field_id in fields:
            if field_id in {"outside_diameter", "nominal_pipe_size"}:
                continue
            order += 1
            child = _child_goal_for_field(
                field_id=field_id,
                phase=phase.value,
                order=order,
                task=task,
                workflow_id=workflow_id,
                root_id=root.id,
                selection_fields=selection_fields,
                lookup_fields=lookup_fields,
            )
            expand_goal(task, root.id, child)

    for field_id in missing_inputs:
        if field_id in {"outside_diameter", "nominal_pipe_size"}:
            continue
        if any(g.key in {f"input-{field_id}", f"select-{field_id}", f"lookup-{field_id}"} for g in task.goal_store.goals.values()):
            continue
        order += 1
        child = _child_goal_for_field(
            field_id=field_id,
            phase=str(getattr(phased, "current_phase", NavigationPhase.PARAMETER_GATHERING).value),
            order=order,
            task=task,
            workflow_id=workflow_id,
            root_id=root.id,
            selection_fields=selection_fields,
            lookup_fields=lookup_fields,
        )
        expand_goal(task, root.id, child)

    refresh_goal_satisfaction(task)
    return task.goal_store


def refresh_goal_tree(
    task: Task,
    reader: StandardsReader,
    *,
    preview: Any | None = None,
    question_map: dict[str, str] | None = None,
    phased: Any | None = None,
    root_slug: str | None = None,
) -> None:
    """Rebuild goal tree and refresh satisfaction."""
    build_goal_tree(
        task,
        reader,
        preview=preview,
        question_map=question_map,
        phased=phased,
        root_slug=root_slug,
    )
