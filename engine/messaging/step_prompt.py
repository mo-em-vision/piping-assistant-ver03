"""Deterministic prompts for expansion assumptions and path decisions (no LLM)."""

from __future__ import annotations

from typing import Any

from engine.graph.node_interaction import (
    InteractionMode,
    NodeInteractionSpec,
    collect_path_interactions,
    collect_root_interactions,
    find_interaction,
    question_for_interaction,
)
from engine.messaging.decision_interaction_resolver import (
    is_node_owned_decision_key,
    resolve_decision_interaction,
)
from engine.messaging.parameter_prompt_context import (
    composer_option_label,
    parameter_metadata_context,
    parameter_prompt_from_metadata,
)
from engine.messaging.prompt_format import format_numbered_choices, format_reply_hint
from engine.reference.parameter_keys import parameter_display_label
from engine.reference.standards_reader import StandardsReader
from models.fact import fact_scalar_value
from models.planning import NavigationPhase, NavigationPlan
from models.task import Task

_DETERMINISTIC_PHASES = frozenset(
    {
        NavigationPhase.EXPANSION_ASSUMPTIONS,
        NavigationPhase.PATH_DECISIONS,
        NavigationPhase.COEFFICIENT_RESOLUTION,
        NavigationPhase.EXECUTION_ASSUMPTIONS,
    }
)


def build_step_prompt(
    *,
    reader: StandardsReader,
    task: Task,
    navigation_plan: NavigationPlan | None,
    missing_input_ids: list[str] | None = None,
) -> str | None:
    """Return a deterministic step prompt for the current navigation phase."""
    if navigation_plan is None:
        return None
    if navigation_plan.current_phase not in _DETERMINISTIC_PHASES:
        return None

    phase_fields = navigation_plan.phase_missing.get(
        navigation_plan.current_phase.value,
        [],
    )
    if not phase_fields:
        phase_fields = list(missing_input_ids or [])
    if not phase_fields:
        return None

    field_id = phase_fields[0]
    return build_interaction_step_prompt(
        reader=reader,
        task=task,
        parameter_id=field_id,
        planning=_planning_dict_from_navigation(navigation_plan),
    )


def build_interaction_step_prompt(
    *,
    reader: StandardsReader,
    task: Task,
    parameter_id: str,
    planning: dict[str, Any] | None = None,
    spec: NodeInteractionSpec | None = None,
) -> str | None:
    """Return a numbered or structured prompt for a single interaction field."""
    if spec is None:
        specs = _interaction_specs_for_task(reader, task)
        spec = find_interaction(specs, parameter_id)

    if spec is not None and spec.mode == InteractionMode.DECISION and spec.options:
        return _format_decision_prompt(reader, parameter_id, spec, planning, task=task)
    if spec is not None and spec.confirmation_required and spec.default is not None:
        return _format_confirm_default_prompt(parameter_id, spec, task)
    if spec is not None:
        question = question_for_interaction(spec, task.fact_store.active_facts())
        return f"{question}\n\nReply to continue."
    return None


def _interaction_specs_for_task(reader: StandardsReader, task: Task) -> list[NodeInteractionSpec]:
    from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id

    root = str(task.outputs.get("selected_root") or task.outputs.get("workflow") or "").strip()
    if not root:
        return []

    slug = normalize_root_id(root)
    engine = GraphEngine()
    plan = engine.build_plan(
        task_id=task.task_id,
        root_id=slug,
        inputs=dict(task.fact_store.active_facts()),
        reader=reader,
    )
    root_slug = resolve_workflow_node_id(slug)
    root_specs = collect_root_interactions(reader, root_slug)
    path_specs = collect_path_interactions(
        reader,
        [
            node_id
            for node_id in plan.execution_order
            if str(reader.load(node_id).metadata.get("type", "")) != "root"
        ],
    )
    merged: list[NodeInteractionSpec] = []
    seen: set[str] = set()
    for item in (*root_specs, *path_specs):
        if item.variable in seen:
            continue
        seen.add(item.variable)
        merged.append(item)
    return merged


def _format_confirm_default_prompt(
    field_id: str,
    spec: NodeInteractionSpec,
    task: Task,
) -> str:
    metadata_ctx = parameter_metadata_context(None, field_id)
    label = spec.symbol or (metadata_ctx.name if metadata_ctx else parameter_display_label(field_id))
    default_val = spec.default
    stored = task.fact_store.active_fact(field_id)
    if stored is not None and stored.default is not None:
        default_val = stored.default
    elif stored is not None and fact_scalar_value(stored) is not None:
        default_val = fact_scalar_value(stored)

    question = (
        spec.question.strip()
        if spec.question
        else (parameter_prompt_from_metadata(metadata_ctx) or f"Confirm the value for {label}.")
    )
    options = (
        f"Confirm default ({label} = {default_val})",
        f"Enter a different value (e.g. {label}: {default_val})",
    )
    lines = [
        f"Confirmation required — {question}",
        "",
    ]
    lines.extend(format_numbered_choices(options))
    lines.append("")
    lines.append(
        format_reply_hint(
            len(options),
            examples=("confirm", f"{label}: {default_val}"),
        )
    )
    return "\n".join(lines)


def _format_decision_prompt(
    reader: StandardsReader,
    field_id: str,
    spec: NodeInteractionSpec | None,
    planning: dict[str, Any] | None,
    *,
    task: Task | None = None,
) -> str:
    metadata_ctx = parameter_metadata_context(reader, field_id)
    navigation_plan = _navigation_plan_from_planning(planning)
    question = None
    labels: tuple[str, ...] = ()

    if task is not None and is_node_owned_decision_key(field_id):
        view = resolve_decision_interaction(reader, task, field_id)
        if view is not None:
            question = view.question
            labels = tuple(option.label for option in view.options)

    if not question:
        question = parameter_prompt_from_metadata(metadata_ctx)
    if not question:
        question = (
            spec.question.strip()
            if spec and spec.question
            else (
                navigation_plan.questions[0].strip()
                if navigation_plan and navigation_plan.questions
                else f"Select a value for {parameter_display_label(field_id, reader=reader)}."
            )
        )

    if not labels:
        if spec and spec.rich_options:
            labels = tuple(option.label for option in spec.rich_options)
        else:
            options = tuple(spec.options) if spec and spec.options else ()
            labels = tuple(composer_option_label(metadata_ctx, value) for value in options)

    lines = [
        f"Input required — {question}",
        "",
    ]
    lines.extend(format_numbered_choices(labels))
    lines.append("")
    lines.append(
        format_reply_hint(
            len(labels),
            examples=(labels[0].split(" — ")[0].lower(),) if labels else ("1",),
        )
    )
    return "\n".join(lines)


def _navigation_plan_from_planning(planning: dict[str, Any] | None) -> NavigationPlan | None:
    if not planning:
        return None
    try:
        phase = NavigationPhase(str(planning.get("current_phase") or NavigationPhase.READY.value))
    except ValueError:
        phase = NavigationPhase.READY
    phase_missing = planning.get("phase_missing") or {}
    questions: list[str] = []
    phase_questions = planning.get("phase_questions") or {}
    if isinstance(phase_questions, dict):
        for phase_name, items in phase_questions.items():
            if isinstance(items, dict):
                questions.extend(str(v) for v in items.values() if v)
            elif isinstance(items, list):
                questions.extend(str(v) for v in items if v)
    return NavigationPlan(
        current_phase=phase,
        phase_missing={
            str(phase_name): list(fields)
            for phase_name, fields in phase_missing.items()
            if isinstance(fields, list)
        },
        questions=questions,
    )


def _planning_dict_from_navigation(navigation_plan: NavigationPlan) -> dict[str, Any]:
    return {
        "current_phase": navigation_plan.current_phase.value,
        "phase_missing": dict(navigation_plan.phase_missing),
        "phase_questions": {},
    }
