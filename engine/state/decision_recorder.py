"""Record runtime decisions on ExecutionContext."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.graph.resolution_branches import RESOLUTION_BRANCH_SUFFIX
from engine.messaging.decision_interaction_resolver import (
    is_node_owned_decision_key,
    resolve_decision_interaction,
    selected_option_from_view,
)
from engine.reference.parameter_keys import canonical_parameter_key, load_parameter_node_metadata
from engine.reference.parameter_metadata import is_path_decision_parameter
from engine.reference.param_resolver import resolve_parameter_id
from engine.reference.standards_reader import StandardsReader
from models.execution_context import Decision, ExecutionContext, new_decision_id
from models.task import Task


def _is_selection_parameter(parameter: str) -> bool:
    canonical = canonical_parameter_key(parameter)
    if is_node_owned_decision_key(canonical):
        return True
    node_id = f"PARAM-{canonical.replace('_', '-')}"
    metadata = load_parameter_node_metadata(node_id)
    return is_path_decision_parameter(metadata)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _activated_node_ids_for_task(task: Task, decision_key: str) -> list[str]:
    canonical = canonical_parameter_key(decision_key)
    if canonical.endswith(RESOLUTION_BRANCH_SUFFIX):
        return []
    path = task.outputs.get("path_decision")
    if not isinstance(path, dict):
        return []
    field = str(path.get("field") or path.get("parameter") or "").strip()
    if field and canonical_parameter_key(field) == canonical:
        selected_node = str(path.get("selected_node") or "").strip()
        if selected_node:
            return [selected_node]
    return []


def _populate_structured_fields(
    decision: Decision,
    *,
    decision_key: str,
    interaction_id: str | None,
    requesting_node_id: str | None,
    selected_label: str | None,
    activated_node_ids: list[str] | None,
    source_type: str | None,
    submission_id: str | None,
) -> None:
    decision.decision_key = canonical_parameter_key(decision_key)
    decision.interaction_id = interaction_id
    decision.requesting_node_id = requesting_node_id
    decision.selected_label = selected_label
    decision.activated_node_ids = list(activated_node_ids or [])
    decision.source_type = source_type
    decision.submission_id = submission_id


def record_decision(
    ctx: ExecutionContext,
    *,
    parameter: str,
    selected_value: Any,
    source: str = "user_input",
    reason: str | None = None,
    decision_key: str | None = None,
    interaction_id: str | None = None,
    requesting_node_id: str | None = None,
    selected_label: str | None = None,
    activated_node_ids: list[str] | None = None,
    source_type: str | None = None,
    submission_id: str | None = None,
) -> Decision:
    param_id = resolve_parameter_id(parameter)
    canonical_key = canonical_parameter_key(decision_key or parameter)
    for existing in ctx.decisions:
        if existing.parameter == param_id or existing.decision_key == canonical_key:
            existing.selected_value = selected_value
            existing.source = source
            existing.reason = reason
            existing.timestamp = _utc_now_iso()
            _populate_structured_fields(
                existing,
                decision_key=canonical_key,
                interaction_id=interaction_id,
                requesting_node_id=requesting_node_id,
                selected_label=selected_label,
                activated_node_ids=activated_node_ids,
                source_type=source_type,
                submission_id=submission_id,
            )
            return existing
    decision = Decision(
        id=new_decision_id(),
        parameter=param_id,
        selected_value=selected_value,
        source=source,
        reason=reason,
        timestamp=_utc_now_iso(),
    )
    _populate_structured_fields(
        decision,
        decision_key=canonical_key,
        interaction_id=interaction_id,
        requesting_node_id=requesting_node_id,
        selected_label=selected_label,
        activated_node_ids=activated_node_ids,
        source_type=source_type,
        submission_id=submission_id,
    )
    ctx.decisions.append(decision)
    return decision


def record_decision_for_task(
    task: Task,
    *,
    parameter: str,
    selected_value: Any,
    source: str = "user_input",
    reason: str | None = None,
    decision_key: str | None = None,
    interaction_id: str | None = None,
    requesting_node_id: str | None = None,
    selected_label: str | None = None,
    activated_node_ids: list[str] | None = None,
    source_type: str | None = None,
    submission_id: str | None = None,
) -> Decision:
    return record_decision(
        task.execution_context,
        parameter=parameter,
        selected_value=selected_value,
        source=source,
        reason=reason,
        decision_key=decision_key,
        interaction_id=interaction_id,
        requesting_node_id=requesting_node_id,
        selected_label=selected_label,
        activated_node_ids=activated_node_ids,
        source_type=source_type,
        submission_id=submission_id,
    )


def record_decision_from_fact(
    task: Task,
    key: str,
    value: Any,
    *,
    reader: StandardsReader | None = None,
    submission_id: str | None = None,
    source_type: str | None = None,
) -> Decision | None:
    canonical = canonical_parameter_key(key)
    if not _is_selection_parameter(canonical):
        return None

    interaction_id = None
    requesting_node_id = None
    selected_label = None
    activated_node_ids = _activated_node_ids_for_task(task, canonical)
    resolved_source_type = source_type or "user_input"

    if reader is not None and is_node_owned_decision_key(canonical):
        view = resolve_decision_interaction(reader, task, canonical)
        if view is not None:
            interaction_id = view.interaction_id
            requesting_node_id = view.requesting_node_id
            option = selected_option_from_view(view, value)
            if option is not None:
                selected_label = option.label
        if canonical.endswith(RESOLUTION_BRANCH_SUFFIX):
            resolved_source_type = source_type or "resolution_branch"

    return record_decision_for_task(
        task,
        parameter=canonical,
        selected_value=value,
        source="user_input",
        decision_key=canonical,
        interaction_id=interaction_id,
        requesting_node_id=requesting_node_id,
        selected_label=selected_label,
        activated_node_ids=activated_node_ids,
        source_type=resolved_source_type,
        submission_id=submission_id,
    )


def migrate_path_decision_to_context(task: Task) -> None:
    path = task.outputs.get("path_decision")
    if not isinstance(path, dict):
        return
    field = path.get("field") or path.get("parameter")
    value = path.get("value") or path.get("selected_node") or field
    if field:
        record_decision_for_task(
            task,
            parameter=str(field),
            selected_value=value,
            source="planner",
            reason="Migrated from path_decision",
        )
