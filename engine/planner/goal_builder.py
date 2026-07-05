"""Build runtime goal trees from graph-driven workflow planning."""

from __future__ import annotations

from typing import Any

from engine.graph.navigation_phases import build_workflow_phased_navigation
from engine.graph.workflow_navigation import load_workflow_navigation
from engine.planner.planner import _INPUT_QUESTIONS
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.planner.workflow_goal_metadata import (
    lookup_fields_for_workflow,
    root_target_for_workflow,
    selection_fields_for_workflow,
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
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN

_DEFAULT_ROOT_TARGETS = {
    PIPE_WALL_THICKNESS_DESIGN: "minimum-required-thickness",
    MAWP_DESIGN: "maximum-allowable-working-pressure",
}


def _resolve_goal_title(reader: StandardsReader, workflow_id: str, graph: GraphTools) -> str:
    from engine.graph.graph_engine import GraphEngine, normalize_root_id

    root_slug = normalize_root_id(workflow_id)
    engine = GraphEngine()
    try:
        if engine.uses_micro_graph(reader, root_slug):
            micro = engine._micro_engine(reader)
            if micro is not None:
                resolved = engine._resolve_micro_root(root_slug, reader)
                wf = micro.store.get_node(resolved)
                if wf is not None:
                    return str(wf.metadata.get("title") or workflow_id)
        root_record = reader.load(root_slug)
        return str(root_record.metadata.get("title") or root_record.metadata.get("purpose") or workflow_id)
    except FileNotFoundError:
        return workflow_id.replace("_", " ")


def _child_goal_for_field(
    *,
    field_id: str,
    phase: str,
    order: int,
    task: Task,
    workflow_id: str,
    root_id: str,
    question_map: dict[str, str],
    selection_fields: frozenset[str],
    lookup_fields: frozenset[str],
) -> Any:
    prompt = question_map.get(field_id) or _INPUT_QUESTIONS.get(field_id) or f"Provide {field_id.replace('_', ' ')}"
    name = prompt.split(".")[0] if "." in prompt else prompt
    if field_id in selection_fields:
        return selection_goal(
            key=f"select-{field_id}",
            name=name,
            target_parameter=field_id,
            task_id=task.task_id,
            prompt=prompt,
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
            required_facts=["material", "design_temperature"],
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
        prompt=prompt,
        workflow_id=workflow_id,
        parent_goal=root_id,
        phase=phase,
        order=order,
    )


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
    execution_eval = graph.evaluate_execution_assumptions(slug, existing_inputs=existing_inputs, plan=preview)

    qmap: dict[str, str] = dict(_INPUT_QUESTIONS)
    if question_map:
        qmap.update(question_map)

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
        )

    clear_goal_store(task)
    fallback_target = _DEFAULT_ROOT_TARGETS.get(slug, "required-wall-thickness")
    target = root_target_for_workflow(reader, workflow_id, fallback=fallback_target)
    selection_fields = selection_fields_for_workflow(reader, workflow_id)
    lookup_fields = lookup_fields_for_workflow(reader, workflow_id)
    title = _resolve_goal_title(reader, workflow_id, graph)
    root = calculation_goal(
        key="verify-engineering-goal",
        name=title,
        target_parameter=target,
        task_id=task.task_id,
        workflow_id=workflow_id,
    )
    root.provenance.created_from_user_intent = workflow_id
    root.metadata["selected_nodes"] = list(getattr(preview, "execution_order", ()) or [])
    store_goal(task, root, as_root=True)

    order = 0
    phase_missing: dict[str, list[str]] = dict(getattr(phased, "phase_missing", {}) or {})
    for phase in NavigationPhase:
        fields = phase_missing.get(phase.value, [])
        for field_id in fields:
            order += 1
            child = _child_goal_for_field(
                field_id=field_id,
                phase=phase.value,
                order=order,
                task=task,
                workflow_id=workflow_id,
                root_id=root.id,
                question_map=qmap,
                selection_fields=selection_fields,
                lookup_fields=lookup_fields,
            )
            expand_goal(task, root.id, child)

    for field_id in missing_inputs:
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
            question_map=qmap,
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
