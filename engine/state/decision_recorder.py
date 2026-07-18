"""Record runtime decisions on ExecutionContext."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.reference.parameter_keys import canonical_parameter_key, load_parameter_node_metadata
from engine.reference.parameter_metadata import is_path_decision_parameter
from engine.reference.param_resolver import resolve_parameter_id
from models.execution_context import Decision, ExecutionContext, new_decision_id
from models.task import Task


_SELECTION_PARAMETERS = frozenset()  # compat: use _is_selection_parameter()


def _is_selection_parameter(parameter: str) -> bool:
    canonical = canonical_parameter_key(parameter)
    node_id = f"PARAM-{canonical.replace('_', '-')}"
    metadata = load_parameter_node_metadata(node_id)
    return is_path_decision_parameter(metadata)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_decision(
    ctx: ExecutionContext,
    *,
    parameter: str,
    selected_value: Any,
    source: str = "user_input",
    reason: str | None = None,
) -> Decision:
    param_id = resolve_parameter_id(parameter)
    for existing in ctx.decisions:
        if existing.parameter == param_id:
            existing.selected_value = selected_value
            existing.source = source
            existing.reason = reason
            existing.timestamp = _utc_now_iso()
            return existing
    decision = Decision(
        id=new_decision_id(),
        parameter=param_id,
        selected_value=selected_value,
        source=source,
        reason=reason,
        timestamp=_utc_now_iso(),
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
) -> Decision:
    return record_decision(
        task.execution_context,
        parameter=parameter,
        selected_value=selected_value,
        source=source,
        reason=reason,
    )


def record_decision_from_fact(task: Task, key: str, value: Any) -> Decision | None:
    if not _is_selection_parameter(key):
        return None
    return record_decision_for_task(
        task,
        parameter=key,
        selected_value=value,
        source="user_input",
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
