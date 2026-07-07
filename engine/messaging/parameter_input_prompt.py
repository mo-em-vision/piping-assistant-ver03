"""Build desktop/API parameter input prompts from interaction, equation, and lookup context."""

from __future__ import annotations

from typing import Any

from engine.graph.graph_timeline import graph_question_for_field
from engine.graph.node_interaction import (
    NodeInteractionSpec,
    collect_path_interactions,
    collect_root_interactions,
    find_interaction,
    question_for_interaction,
)
from engine.messaging.formula_parameter_prompt import guidance_for_parameter_input
from engine.messaging.workflow_parameter_prompts import default_workflow_parameter_prompt
from engine.reference.standards_reader import StandardsReader
from models.task import Task


def interaction_specs_for_task(reader: StandardsReader, task: Task) -> list[NodeInteractionSpec]:
    """Merge workflow-root and path interaction specs for the active task."""
    from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id

    root = (
        task.outputs.get("selected_root")
        or task.outputs.get("workflow")
        or "pipe_wall_thickness_design"
    )
    slug = normalize_root_id(str(root))
    engine = GraphEngine()
    facts = dict(task.fact_store.active_facts())
    plan = engine.build_plan(
        task_id=task.task_id,
        root_id=slug,
        inputs=facts,
        reader=reader,
    )
    root_slug = resolve_workflow_node_id(slug)
    root_specs = collect_root_interactions(reader, root_slug)
    path_specs = collect_path_interactions(reader, plan.execution_order)

    merged: list[NodeInteractionSpec] = []
    seen: set[str] = set()
    for spec in (*root_specs, *path_specs):
        if spec.variable in seen:
            continue
        seen.add(spec.variable)
        merged.append(spec)
    return merged


def interaction_for_parameter(
    reader: StandardsReader,
    task: Task,
    parameter_id: str,
) -> NodeInteractionSpec | None:
    return find_interaction(interaction_specs_for_task(reader, task), parameter_id)


def build_parameter_input_prompt(
    reader: StandardsReader,
    task: Task,
    parameter_id: str,
    *,
    planning: dict[str, Any] | None = None,
) -> str | None:
    """Return a user-facing prompt for a workflow parameter input."""
    facts = dict(task.fact_store.active_facts())

    spec = interaction_for_parameter(reader, task, parameter_id)
    if spec is not None:
        interaction_prompt = question_for_interaction(spec, facts).strip()
        if interaction_prompt:
            return interaction_prompt

    graph_question = graph_question_for_field(reader, parameter_id)
    if graph_question and graph_question.strip():
        return graph_question.strip()

    default_prompt = default_workflow_parameter_prompt(parameter_id)
    if default_prompt:
        return default_prompt

    equation_guidance = guidance_for_parameter_input(reader, task, parameter_id)
    if equation_guidance:
        return equation_guidance.strip()

    if planning:
        phase_questions = planning.get("phase_questions") or {}
        phase_missing = planning.get("phase_missing") or {}
        if isinstance(phase_questions, dict) and isinstance(phase_missing, dict):
            for phase, fields in phase_missing.items():
                if not isinstance(fields, list) or parameter_id not in fields:
                    continue
                questions = phase_questions.get(phase)
                if isinstance(questions, dict):
                    prompt = questions.get(parameter_id)
                    if isinstance(prompt, str) and prompt.strip():
                        return prompt.strip()

    return None
