"""Build desktop/API parameter input prompts from interaction, equation, and lookup context."""

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
from engine.messaging.formula_parameter_prompt import focus_node_for_parameter, guidance_for_parameter_input
from engine.messaging.parameter_prompt_context import (
    parameter_metadata_context,
    parameter_prompt_from_metadata,
    short_prompt_from_metadata,
)
from engine.messaging.prompt_format import PromptAssemblyContext, render_parameter_prompt
from engine.messaging.step_prompt import build_interaction_step_prompt
from engine.reference.formula_display import load_equation_context
from engine.reference.parameter_keys import canonical_parameter_key, parameter_display_label
from engine.reference.standards_reader import StandardsReader
from models.task import Task


def _task_workflow_root(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()


def interaction_specs_for_task(reader: StandardsReader, task: Task) -> list[NodeInteractionSpec]:
    """Merge workflow-root and path interaction specs for the active task."""
    from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id

    root = _task_workflow_root(task)
    if not root:
        return []

    slug = normalize_root_id(root)
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
    canonical_id = canonical_parameter_key(parameter_id)
    facts = dict(task.fact_store.active_facts())

    if is_node_owned_decision_key(canonical_id):
        view = resolve_decision_interaction(reader, task, canonical_id)
        if view is not None and view.question:
            return view.question

    metadata_ctx = parameter_metadata_context(reader, canonical_id)
    spec = interaction_for_parameter(reader, task, canonical_id)

    if spec is not None and _needs_numbered_interaction_prompt(spec):
        numbered = build_interaction_step_prompt(
            reader=reader,
            task=task,
            parameter_id=canonical_id,
            planning=planning,
            spec=spec,
        )
        if numbered:
            return numbered

    if spec is not None:
        interaction_prompt = question_for_interaction(spec, facts).strip()
        if interaction_prompt:
            return interaction_prompt

    if is_node_owned_decision_key(canonical_id):
        return _final_messaging_fallback(canonical_id, planning=planning, metadata_ctx=metadata_ctx)

    metadata_prompt = parameter_prompt_from_metadata(metadata_ctx)
    if metadata_prompt:
        return _enrich_metadata_prompt(metadata_ctx, metadata_prompt, planning)

    equation_guidance = guidance_for_parameter_input(reader, task, canonical_id)
    if equation_guidance:
        return _enrich_equation_guidance(
            reader,
            task,
            canonical_id,
            equation_guidance.strip(),
            planning=planning,
            metadata_ctx=metadata_ctx,
        )

    legacy = _legacy_phase_question(canonical_id, planning)
    if legacy:
        return legacy

    return _final_messaging_fallback(canonical_id, planning=planning, metadata_ctx=metadata_ctx)


def build_short_parameter_input_prompt(
    reader: StandardsReader,
    task: Task,
    parameter_id: str,
    *,
    planning: dict[str, Any] | None = None,
) -> str | None:
    """Return a short composer prompt without numbered choices or long narration."""
    canonical_id = canonical_parameter_key(parameter_id)
    facts = dict(task.fact_store.active_facts())

    if is_node_owned_decision_key(canonical_id):
        view = resolve_decision_interaction(reader, task, canonical_id)
        if view is not None and view.question:
            return view.question

    metadata_ctx = parameter_metadata_context(reader, canonical_id)

    short = short_prompt_from_metadata(metadata_ctx)
    if short and not is_node_owned_decision_key(canonical_id):
        return short

    spec = interaction_for_parameter(reader, task, canonical_id)
    if spec is not None:
        if spec.question and spec.question.strip():
            return spec.question.strip()
        interaction_prompt = question_for_interaction(spec, facts).strip()
        if interaction_prompt:
            return interaction_prompt

    legacy = _legacy_phase_question(canonical_id, planning)
    if legacy:
        return _first_sentence(legacy)

    label = parameter_display_label(canonical_id, reader=reader)
    return f"Enter {label}."


def _first_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    for separator in (". ", ".\n"):
        index = stripped.find(separator)
        if index > 0:
            return stripped[: index + 1].strip()
    return stripped


def _needs_numbered_interaction_prompt(spec: NodeInteractionSpec) -> bool:
    if spec.mode == InteractionMode.DECISION and spec.options:
        return True
    if spec.confirmation_required and spec.default is not None:
        return True
    return False


def _legacy_phase_question(parameter_id: str, planning: dict[str, Any] | None) -> str | None:
    if not planning:
        return None
    phase_questions = planning.get("phase_questions") or {}
    phase_missing = planning.get("phase_missing") or {}
    if not isinstance(phase_questions, dict) or not isinstance(phase_missing, dict):
        return None
    for phase, fields in phase_missing.items():
        if not isinstance(fields, list) or parameter_id not in fields:
            continue
        questions = phase_questions.get(phase)
        if isinstance(questions, dict):
            prompt = questions.get(parameter_id)
            if isinstance(prompt, str) and prompt.strip():
                return prompt.strip()
    return None


def _examples_from_metadata(metadata_ctx) -> tuple[str, ...]:
    if metadata_ctx is None:
        return ()
    return metadata_ctx.input_examples


def _enrich_metadata_prompt(
    metadata_ctx,
    prompt: str,
    planning: dict[str, Any] | None,
) -> str:
    if metadata_ctx is None:
        return prompt
    ctx = PromptAssemblyContext(
        parameter_id=metadata_ctx.parameter_id,
        label=metadata_ctx.name or parameter_display_label(metadata_ctx.parameter_id),
        symbol=metadata_ctx.canonical_symbol,
        phase=str((planning or {}).get("current_phase") or "") or None,
        body=prompt,
        units=metadata_ctx.allowed_units,
        examples=_examples_from_metadata(metadata_ctx),
    )
    return render_parameter_prompt(ctx)


def _enrich_equation_guidance(
    reader: StandardsReader,
    task: Task,
    parameter_id: str,
    guidance: str,
    *,
    planning: dict[str, Any] | None,
    metadata_ctx,
) -> str:
    label = (
        metadata_ctx.name
        if metadata_ctx and metadata_ctx.name
        else parameter_display_label(parameter_id, reader=reader)
    )
    symbol = metadata_ctx.canonical_symbol if metadata_ctx else None
    ctx = PromptAssemblyContext(
        parameter_id=parameter_id,
        label=label,
        symbol=symbol,
        phase=str((planning or {}).get("current_phase") or "") or None,
        body=guidance,
        usage_site=_equation_usage_line(reader, task, parameter_id),
        units=metadata_ctx.allowed_units if metadata_ctx else (),
        examples=_examples_from_metadata(metadata_ctx),
    )
    return render_parameter_prompt(ctx)


def _equation_usage_line(reader: StandardsReader, task: Task, parameter_id: str) -> str | None:
    facts = dict(task.fact_store.active_facts())
    node_id = focus_node_for_parameter(reader, task, facts)
    if node_id is None:
        return None
    eq_ctx = load_equation_context(reader, node_id, task_facts=facts)
    display = eq_ctx.get("display")
    if isinstance(display, str) and display.strip():
        return f"Used in the governing equation: {display.strip()}"
    return None


def _final_messaging_fallback(
    parameter_id: str,
    *,
    planning: dict[str, Any] | None,
    metadata_ctx,
) -> str:
    label = (
        metadata_ctx.name
        if metadata_ctx and metadata_ctx.name
        else parameter_display_label(parameter_id)
    )
    ctx = PromptAssemblyContext(
        parameter_id=parameter_id,
        label=label,
        symbol=metadata_ctx.canonical_symbol if metadata_ctx else None,
        phase=str((planning or {}).get("current_phase") or "") or None,
        purpose=f"Provide {label.lower()} to continue the workflow",
        units=metadata_ctx.allowed_units if metadata_ctx else (),
        examples=_examples_from_metadata(metadata_ctx),
    )
    return render_parameter_prompt(ctx)


def resolve_parameter_prompt_text(
    parameter_id: str,
    *,
    field_question: str | None = None,
    reader: StandardsReader | None = None,
    fallback_prefix: str = "Provide",
) -> str:
    """Resolve prompt copy from interaction field text or PARAM metadata."""
    if field_question and field_question.strip():
        return field_question.strip()
    canonical_id = canonical_parameter_key(parameter_id)
    metadata_ctx = parameter_metadata_context(reader, canonical_id)
    metadata_prompt = parameter_prompt_from_metadata(metadata_ctx)
    if metadata_prompt:
        return metadata_prompt
    label = parameter_display_label(canonical_id, reader=reader)
    return f"{fallback_prefix} {label}."
