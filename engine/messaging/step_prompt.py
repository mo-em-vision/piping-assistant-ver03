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

_YES_NO_OPTIONS = (
    "Yes — straight pipe section",
    "No — fitting, bend, or other non-straight component",
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
    navigation_plan = _navigation_plan_from_planning(planning)
    if spec is None:
        specs = _interaction_specs_for_task(reader, task)
        spec = find_interaction(specs, parameter_id)

    if parameter_id == "straight_pipe_section":
        return _format_yes_no_assumption_prompt(parameter_id, spec, navigation_plan)
    if spec is not None and spec.mode == InteractionMode.DECISION and spec.options:
        return _format_decision_prompt(parameter_id, spec, navigation_plan)
    if spec is not None and spec.confirmation_required and spec.default is not None:
        return _format_confirm_default_prompt(parameter_id, spec, task)
    if spec is not None:
        question = question_for_interaction(spec, task.fact_store.active_facts())
        return f"{question}\n\nReply to continue."
    return None


def _interaction_specs_for_task(reader: StandardsReader, task: Task) -> list[NodeInteractionSpec]:
    from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id

    root = task.outputs.get("selected_root") or task.outputs.get("workflow") or "pipe_wall_thickness_design"
    slug = normalize_root_id(str(root))
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


def _format_yes_no_assumption_prompt(
    field_id: str,
    spec: NodeInteractionSpec | None,
    navigation_plan: NavigationPlan | None,
) -> str:
    question = (
        "This workflow currently supports straight pipe sections only. "
        "Is the wall thickness calculation for a straight pipe section?"
    )
    if spec and spec.question and spec.question.strip():
        question = spec.question.strip()
    elif navigation_plan and navigation_plan.questions:
        question = navigation_plan.questions[0].strip()

    node_ref = spec.node_id if spec else "304.1.1-a"
    lines = [
        f"Before expanding ASME B31.3 §304.1.1 ({node_ref}), confirm the following assumption:",
        "",
        question,
        "",
    ]
    lines.extend(format_numbered_choices(_YES_NO_OPTIONS))
    lines.append("")
    lines.append(format_reply_hint(len(_YES_NO_OPTIONS), examples=("yes", "no")))
    return "\n".join(lines)


def _format_confirm_default_prompt(
    field_id: str,
    spec: NodeInteractionSpec,
    task: Task,
) -> str:
    label = spec.symbol or parameter_display_label(field_id)
    default_val = spec.default
    stored = task.fact_store.active_fact(field_id)
    if stored is not None and stored.default is not None:
        default_val = stored.default
    elif stored is not None and fact_scalar_value(stored) is not None:
        default_val = fact_scalar_value(stored)

    question = (
        spec.question.strip()
        if spec.question
        else f"Confirm the value for {label}."
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
    field_id: str,
    spec: NodeInteractionSpec | None,
    navigation_plan: NavigationPlan | None,
) -> str:
    if field_id == "pressure_loading":
        question = (
            "Which pressure case applies to this pipe section? "
            "This determines the ASME B31.3 pressure design branch."
        )
    else:
        display_label = parameter_display_label(field_id)
        question = (
            spec.question.strip()
            if spec and spec.question
            else (
                navigation_plan.questions[0].strip()
                if navigation_plan and navigation_plan.questions
                else f"Select a value for {display_label}."
            )
        )

    options = tuple(spec.options) if spec and spec.options else (
        "internal_pressure",
        "external_pressure",
    )
    labels = [_option_label(value) for value in options]

    lines = [
        f"Input required — {question}",
        "",
    ]
    lines.extend(format_numbered_choices(labels))
    lines.append("")
    lines.append(
        format_reply_hint(
            len(labels),
            examples=(labels[0].split(" — ")[0].lower(),),
        )
    )
    return "\n".join(lines)


def _option_label(value: str) -> str:
    if value == "internal_pressure":
        return "Internal pressure — use §304.1.2"
    if value == "external_pressure":
        return "External pressure — use §304.1.3"
    if value == "nps_lookup":
        return "Nominal pipe size (NPS) — use table lookup for outside diameter"
    if value == "direct_od":
        return "Outside diameter — enter the diameter directly with units"
    if value == "direct_id":
        return "Inside diameter — enter d directly (mm or in)"
    if value == "seamless":
        return "Seamless pipe (default)"
    if value == "erw":
        return "Electric-resistance welded (ERW)"
    if value == "furnace_butt_welded":
        return "Furnace butt-welded"
    if value == "forging":
        return "Forging"
    return value.replace("_", " ").title()


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
