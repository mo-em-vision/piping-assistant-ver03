"""Deterministic prompts for expansion assumptions and path decisions (no LLM)."""

from __future__ import annotations

from engine.messaging.prompt_format import format_numbered_choices, format_reply_hint
from engine.graph.node_interaction import (
    NodeInteractionSpec,
    collect_path_interactions,
    find_interaction,
    question_for_interaction,
)
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
    "Yes — straight pipe section (supported)",
    "No — fitting or bend (not yet supported)",
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
    specs = _interaction_specs_for_task(reader, task)
    spec = find_interaction(specs, field_id)

    if field_id == "straight_pipe_section":
        return _format_yes_no_assumption_prompt(field_id, spec, navigation_plan)
    if spec is not None and spec.mode.value == "decision" and spec.options:
        return _format_decision_prompt(field_id, spec, navigation_plan)
    if spec is not None and spec.confirmation_required and spec.default is not None:
        return _format_confirm_default_prompt(field_id, spec, task)
    if spec is not None:
        question = question_for_interaction(spec, task.fact_store.active_facts())
        return f"{question}\n\nReply to continue."
    return None


def _interaction_specs_for_task(reader: StandardsReader, task: Task) -> list[NodeInteractionSpec]:
    from engine.graph.graph_engine import GraphEngine, normalize_root_id

    root = task.outputs.get("selected_root") or "pipe_wall_thickness_design"
    slug = normalize_root_id(str(root))
    engine = GraphEngine()
    plan = engine.build_plan(
        task_id=task.task_id,
        root_id=slug,
        inputs=dict(task.fact_store.active_facts()),
        reader=reader,
    )
    node_ids = [
        node_id
        for node_id in plan.execution_order
        if str(reader.load(node_id).metadata.get("type", "")) != "root"
    ]
    return collect_path_interactions(reader, node_ids)


def _format_yes_no_assumption_prompt(
    field_id: str,
    spec: NodeInteractionSpec | None,
    navigation_plan: NavigationPlan,
) -> str:
    question = (
        spec.question.strip()
        if spec and spec.question
        else (
            navigation_plan.questions[0].strip()
            if navigation_plan.questions
            else (
                "Is the pipe wall thickness you would like to calculate for a "
                "straight section of pipe? Non-straight sections (fittings, bends) "
                "are not yet supported."
            )
        )
    )
    node_ref = spec.node_id if spec else "B313-304.1.1"
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
    label = spec.symbol or field_id
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
    navigation_plan: NavigationPlan,
) -> str:
    options = tuple(spec.options) if spec and spec.options else (
        "internal_pressure",
        "external_pressure",
    )
    labels = [_option_label(value) for value in options]
    question = (
        spec.question.strip()
        if spec and spec.question
        else (
            navigation_plan.questions[0].strip()
            if navigation_plan.questions
            else f"Select a value for {field_id}."
        )
    )

    lines = [
        f"Input required ({field_id}) — {question}",
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
        return "Internal pressure — design per §304.1.2 (node B313-304.1.2)"
    if value == "external_pressure":
        return "External pressure — design per §304.1.3 (node B313-304.1.3)"
    if value == "nps_lookup":
        return "Nominal pipe size (NPS) — look up outside diameter per ASME B36.10"
    if value == "direct_od":
        return "Outside diameter — enter D directly (mm or in)"
    if value == "seamless":
        return "Seamless pipe (default)"
    if value == "erw":
        return "Electric-resistance welded (ERW)"
    if value == "furnace_butt_welded":
        return "Furnace butt-welded"
    if value == "forging":
        return "Forging"
    return value.replace("_", " ").title()
