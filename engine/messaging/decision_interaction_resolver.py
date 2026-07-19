"""Load node-owned decision interaction copy from authored metadata only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.assumption_checker import normalize_assumption_value
from engine.graph.node_interaction import InteractionOption, NodeInteractionSpec, parse_interactions
from engine.graph.resolution_branches import (
    RESOLUTION_BRANCH_SUFFIX,
    resolution_branch_fact_key,
    resolution_branches_from_metadata,
)
from engine.reference.parameter_keys import (
    canonical_parameter_key,
    load_parameter_node_metadata,
    param_node_id_for_input,
)
from engine.reference.paragraph_sidecar import merge_paragraph_sidecar_metadata
from engine.reference.standards_reader import StandardsReader
from models.task import Task

# Decision keys with explicit node-owned copy (no PARAM/assumption runtime fallback).
NODE_OWNED_DECISION_KEYS = frozenset(
    {
        "straight_pipe_section",
        "pressure_design_case",
        resolution_branch_fact_key("outside_diameter"),
    }
)


@dataclass(frozen=True)
class DecisionOptionView:
    value: str
    label: str
    help_text: str | None
    report_statement: str


@dataclass(frozen=True)
class DecisionInteractionView:
    decision_key: str
    interaction_id: str
    requesting_node_id: str
    question: str
    help_text: str | None
    options: tuple[DecisionOptionView, ...]


def is_node_owned_decision_key(decision_key: str) -> bool:
    return canonical_parameter_key(decision_key) in {
        canonical_parameter_key(item) for item in NODE_OWNED_DECISION_KEYS
    }


def _param_metadata_block(metadata: dict[str, Any]) -> dict[str, Any]:
    nested = metadata.get("metadata")
    if isinstance(nested, dict):
        return nested
    return metadata


def _options_from_rich(rich_options: tuple[InteractionOption, ...]) -> tuple[DecisionOptionView, ...]:
    views: list[DecisionOptionView] = []
    for option in rich_options:
        if not option.report_statement:
            continue
        views.append(
            DecisionOptionView(
                value=option.value,
                label=option.label,
                help_text=option.help_text,
                report_statement=option.report_statement,
            )
        )
    return tuple(views)


def _view_from_interaction_spec(spec: NodeInteractionSpec) -> DecisionInteractionView | None:
    if not spec.question or not spec.rich_options:
        return None
    options = _options_from_rich(spec.rich_options)
    if not options:
        return None
    return DecisionInteractionView(
        decision_key=spec.variable,
        interaction_id=spec.interaction_id or spec.variable,
        requesting_node_id=spec.node_id,
        question=spec.question.strip(),
        help_text=spec.help_text,
        options=options,
    )


def _authored_interactions_for_node(
    reader: StandardsReader,
    node_id: str,
) -> list[NodeInteractionSpec]:
    record = reader.load(node_id)
    metadata = merge_paragraph_sidecar_metadata(
        record.metadata,
        record_path=record.path,
        node_id=record.node_id,
    )
    return parse_interactions(metadata, record.node_id)


def _execution_order_for_task(reader: StandardsReader, task: Task) -> list[str]:
    from engine.graph.graph_engine import GraphEngine, normalize_root_id

    root = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()
    if not root:
        return []
    engine = GraphEngine()
    facts = dict(task.fact_store.active_facts())
    plan = engine.build_plan(
        task_id=task.task_id,
        root_id=normalize_root_id(root),
        inputs=facts,
        reader=reader,
    )
    return list(plan.execution_order)


def _paragraph_interaction_view(
    reader: StandardsReader,
    task: Task,
    decision_key: str,
) -> DecisionInteractionView | None:
    canonical = canonical_parameter_key(decision_key)
    for node_id in _execution_order_for_task(reader, task):
        try:
            record = reader.load(node_id)
        except FileNotFoundError:
            continue
        if str(record.metadata.get("type", "")) != "paragraph":
            continue
        for spec in _authored_interactions_for_node(reader, node_id):
            if canonical_parameter_key(spec.variable) != canonical:
                continue
            view = _view_from_interaction_spec(spec)
            if view is not None:
                return view
    return None


def _resolution_branch_view(decision_key: str) -> DecisionInteractionView | None:
    if not str(decision_key).endswith(RESOLUTION_BRANCH_SUFFIX):
        return None
    anchor_key = decision_key[: -len(RESOLUTION_BRANCH_SUFFIX)]
    param_node_id = param_node_id_for_input(anchor_key)
    metadata = load_parameter_node_metadata(param_node_id)
    if metadata is None:
        return None
    block = _param_metadata_block(metadata)
    question = str(block.get("resolution_branch_question") or "").strip()
    if not question:
        return None
    help_raw = block.get("resolution_branch_help_text")
    help_text = str(help_raw).strip() if isinstance(help_raw, str) and help_raw.strip() else None
    options: list[DecisionOptionView] = []
    for branch in resolution_branches_from_metadata(metadata):
        branch_id = str(branch.get("id") or "").strip()
        if not branch_id:
            continue
        label = str(branch.get("label") or branch_id.replace("_", " ").title()).strip()
        branch_help_raw = branch.get("help_text")
        branch_help = (
            str(branch_help_raw).strip()
            if isinstance(branch_help_raw, str) and branch_help_raw.strip()
            else None
        )
        report_raw = branch.get("report_statement")
        report_statement = (
            str(report_raw).strip()
            if isinstance(report_raw, str) and report_raw.strip()
            else None
        )
        if not report_statement:
            continue
        options.append(
            DecisionOptionView(
                value=branch_id,
                label=label,
                help_text=branch_help,
                report_statement=report_statement,
            )
        )
    if not options:
        return None
    return DecisionInteractionView(
        decision_key=decision_key,
        interaction_id=anchor_key,
        requesting_node_id=param_node_id,
        question=question,
        help_text=help_text,
        options=tuple(options),
    )


def resolve_decision_interaction(
    reader: StandardsReader,
    task: Task,
    decision_key: str,
) -> DecisionInteractionView | None:
    """Return node-owned decision copy for migrated decision keys only."""
    canonical = canonical_parameter_key(decision_key)
    if not is_node_owned_decision_key(canonical):
        return None
    if canonical.endswith(RESOLUTION_BRANCH_SUFFIX):
        return _resolution_branch_view(canonical)
    return _paragraph_interaction_view(reader, task, canonical)


def composer_options_from_view(view: DecisionInteractionView) -> list[dict[str, str]]:
    return [
        {
            "value": option.value,
            "label": option.label,
            **({"help_text": option.help_text} if option.help_text else {}),
        }
        for option in view.options
    ]


def selected_option_from_view(
    view: DecisionInteractionView,
    selected_value: Any,
) -> DecisionOptionView | None:
    selected = normalize_assumption_value(selected_value)
    for option in view.options:
        if normalize_assumption_value(option.value) == selected:
            return option
    return None
