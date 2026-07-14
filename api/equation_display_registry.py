"""Graph-driven registry of equation blocks that must stay visible and update in place."""

from __future__ import annotations

from typing import Any

from api.display_block_metadata import (
    EQUATION_TRACE_KEYS_OUTPUT,
    _evaluated_equation_trace_entries,
    _persisted_equation_trace_entries,
    equation_trace_semantic_key,
)
from engine.graph.definition_equations import (
    definition_equation_specs_for_order,
    has_execution_trace,
)
from engine.reference.standards_reader import StandardsReader
from models.task import Task


def _workflow_id(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()


def _planning_inputs(task: Task) -> dict[str, Any]:
    """Merge confirmed facts with scalar task outputs for graph applicability checks."""
    inputs: dict[str, Any] = dict(task.fact_store.active_facts())
    for key, value in task.outputs.items():
        if str(key).startswith("_"):
            continue
        if isinstance(value, (bool, int, float, str)):
            inputs.setdefault(str(key), value)
    return inputs


def _resolve_execution_order(task: Task, reader: StandardsReader) -> tuple[str, ...]:
    workflow_id = _workflow_id(task)
    if not workflow_id:
        return ()
    try:
        from engine.graph.graph_engine import GraphEngine

        plan = GraphEngine().build_plan(
            task_id=task.task_id,
            root_id=workflow_id,
            inputs=_planning_inputs(task),
            reader=reader,
        )
        return tuple(plan.execution_order)
    except Exception:  # noqa: BLE001
        return ()


def _expanded_execution_order(task: Task, reader: StandardsReader) -> tuple[str, ...]:
    """Execution order augmented with nodes already present in the execution trace."""
    order = list(_resolve_execution_order(task, reader))
    seen = set(order)
    for entry in task.outputs.get("_execution_trace") or []:
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id") or "").strip()
        if node_id and node_id not in seen:
            order.append(node_id)
            seen.add(node_id)
    return tuple(order)


def _workflow_target_field(reader: StandardsReader, workflow_id: str) -> str | None:
    store = reader.graph_store
    if store is None:
        return None
    metadata = store.metadata(workflow_id) if store.get_node(workflow_id) is not None else {}
    target = str(metadata.get("goal_output") or "").strip()
    return target or None


def _definition_equation_ids_on_target_path(
    task: Task,
    reader: StandardsReader,
    execution_order: tuple[str, ...] | list[str],
) -> list[str]:
    workflow_id = _workflow_id(task)
    if not workflow_id:
        return []

    target_field = _workflow_target_field(reader, workflow_id)
    if not target_field:
        return []

    store = reader.graph_store
    if store is None:
        return []

    from engine.planner.graph_requirements import _equations_on_target_path

    equation_ids = _equations_on_target_path(
        store,
        target_field,
        _planning_inputs(task),
        execution_order=list(execution_order),
    )

    definition_ids: list[str] = []
    for equation_id in equation_ids:
        try:
            record = reader.load(equation_id)
        except FileNotFoundError:
            continue
        if str(record.metadata.get("execution_phase", "")).strip() != "definition":
            continue
        definition_ids.append(equation_id)
    return definition_ids


def source_node_id_for_equation(reader: StandardsReader, equation_node_id: str) -> str:
    """Resolve the paragraph/definition node that owns an equation for display provenance."""
    try:
        record = reader.load(equation_node_id)
    except FileNotFoundError:
        return equation_node_id

    metadata = record.metadata
    authority = metadata.get("authority") or {}
    authorized = authority.get("authorized_by") or []
    if authorized:
        candidate = str(authorized[0]).strip()
        if candidate:
            return candidate

    paragraph_number = str(metadata.get("paragraph_number") or "").strip()
    if paragraph_number:
        return paragraph_number

    return equation_node_id


def _definition_equation_entries(
    task: Task,
    reader: StandardsReader,
) -> list[tuple[str, str]]:
    if not has_execution_trace(task):
        return []

    execution_order = _expanded_execution_order(task, reader)
    if not execution_order:
        return []

    entries: list[tuple[str, str]] = []
    seen: set[str] = set()

    def append(equation_node_id: str) -> None:
        if not equation_node_id or equation_node_id in seen:
            return
        seen.add(equation_node_id)
        source_node_id = source_node_id_for_equation(reader, equation_node_id)
        entries.append((equation_node_id, source_node_id))

    for spec in definition_equation_specs_for_order(reader, execution_order):
        append(spec.node_id)

    for equation_node_id in _definition_equation_ids_on_target_path(
        task,
        reader,
        execution_order,
    ):
        append(equation_node_id)

    return entries


def discover_equation_display_entries(
    task: Task,
    reader: StandardsReader,
    planning: dict[str, Any],
) -> list[tuple[str, str]]:
    """Return ordered (equation_node_id, source_node_id) pairs to rebuild for display."""
    from api.equation_evaluation_display import (
        resolve_equation_node_for_display,
        resolve_focus_node_for_equation_display,
    )

    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(equation_node_id: str, source_node_id: str) -> None:
        equation_node_id = str(equation_node_id or "").strip()
        source_node_id = str(source_node_id or "").strip() or equation_node_id
        if not equation_node_id or equation_node_id in seen:
            return
        seen.add(equation_node_id)
        ordered.append((equation_node_id, source_node_id))
        workflow_id = _workflow_id(task)
        if workflow_id:
            register_equation_display_key(task, workflow_id, source_node_id, equation_node_id)

    for equation_node_id, source_node_id in _definition_equation_entries(task, reader):
        add(equation_node_id, source_node_id)

    for item in _evaluated_equation_trace_entries(task):
        add(item["equation_node_id"], item["source_node_id"])

    for item in _persisted_equation_trace_entries(task):
        add(item["equation_node_id"], item["source_node_id"])

    focus_node = resolve_focus_node_for_equation_display(task, planning, reader)
    if focus_node:
        equation_id = resolve_equation_node_for_display(reader, focus_node, task)
        if equation_id:
            add(equation_id, focus_node)

    return ordered


def register_equation_display_key(
    task: Task,
    workflow_id: str,
    source_node_id: str,
    equation_node_id: str,
) -> bool:
    """Append a semantic trace key when missing. Returns True if task.outputs changed."""
    workflow_id = str(workflow_id or "").strip()
    equation_node_id = str(equation_node_id or "").strip()
    source_node_id = str(source_node_id or "").strip() or equation_node_id
    if not workflow_id or not equation_node_id:
        return False

    key = equation_trace_semantic_key(
        workflow_id=workflow_id,
        source_node_id=source_node_id,
        equation_node_id=equation_node_id,
    )
    existing = list(task.outputs.get(EQUATION_TRACE_KEYS_OUTPUT) or [])
    if key in existing:
        return False
    task.outputs[EQUATION_TRACE_KEYS_OUTPUT] = sorted([*existing, key])
    return True


def sync_equation_display_keys_from_blocks(
    task: Task,
    blocks: list[dict[str, Any]],
) -> bool:
    """Register trace keys for every equation block in a display snapshot."""
    workflow_id = _workflow_id(task)
    if not workflow_id:
        return False

    changed = False
    for block in blocks:
        if str(block.get("type") or "") != "equation":
            continue
        equation_node_id = str(block.get("equation_node_id") or "").strip()
        if not equation_node_id:
            continue
        source_node_id = str(block.get("source_node_id") or "").strip() or equation_node_id
        if register_equation_display_key(task, workflow_id, source_node_id, equation_node_id):
            changed = True
    return changed
