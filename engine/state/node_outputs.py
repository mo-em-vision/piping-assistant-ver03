"""Build structured node outputs for WorkflowState."""

from __future__ import annotations

from typing import Any

from engine.graph.graph_store import GraphStore
from engine.reference.node_types import is_lookup_node
from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput, InputStatus
from models.node_output import NodeOutput
from models.task import Task, TaskStatus

_LOOKUP_OUTPUT_SUFFIXES = ("_lookup", "_lookup_result")

_WORKFLOW_ROOT_ALIASES: dict[str, str] = {
    "pipe_wall_thickness_design": "B313-WF-PIPE-WALL-THICKNESS",
    "mawp_design": "B313-WF-MAWP",
    "B313-PIPE-WALL-THICKNESS-DESIGN": "B313-WF-PIPE-WALL-THICKNESS",
}


def build_node_outputs(
    task: Task,
    *,
    reader: StandardsReader,
    history: tuple[dict[str, Any], ...],
) -> dict[str, tuple[NodeOutput, ...]]:
    """Collect structured outputs keyed by producing node id."""
    store = reader.graph_store
    if not store.available:
        return {}

    by_node: dict[str, list[NodeOutput]] = {}

    for entry in history:
        if entry.get("status") != "completed":
            continue
        node_id = str(entry.get("node_id", "")).strip()
        if not node_id:
            continue
        node = store.get_node(node_id)
        if node is None:
            continue
        node_type = store.node_type(node_id) or ""
        meta = store.metadata(node_id)
        if node_type not in {"equation", "lookup", "calculation"}:
            continue
        result = entry.get("result")
        raw_outputs = result.get("outputs") if isinstance(result, dict) else None
        if not isinstance(raw_outputs, dict) or not raw_outputs:
            continue

        if is_lookup_node(meta, node_type) or node_type == "lookup":
            outputs = _lookup_node_outputs(store, node_id, meta, raw_outputs, task)
        else:
            outputs = _equation_node_outputs(store, meta, raw_outputs, task)
        if outputs:
            by_node.setdefault(node_id, []).extend(outputs)

    _attach_task_lookup_outputs(task, store, by_node)
    _attach_selection_outputs(task, store, by_node)
    _attach_workflow_completion(task, store, by_node)

    return {
        node_id: tuple(items)
        for node_id, items in sorted(by_node.items())
        if items
    }


def _param_output(
    store: GraphStore,
    param_node_id: str,
    *,
    value: Any,
    task: Task,
) -> NodeOutput | None:
    if value is None:
        return None
    meta = store.metadata(param_node_id)
    input_id = str(meta.get("input_id", "")).strip() or param_node_id
    symbol = str(meta.get("symbol", "")).strip() or None
    label = str(meta.get("title") or meta.get("displayName") or input_id).strip()
    unit = _resolve_unit(task, input_id, meta)
    return NodeOutput(
        name=input_id,
        label=label,
        value=value,
        unit=unit,
        symbol=symbol,
        param_node_id=param_node_id,
    )


def _equation_node_outputs(
    store: GraphStore,
    meta: dict[str, Any],
    raw_outputs: dict[str, Any],
    task: Task,
) -> list[NodeOutput]:
    outputs: list[NodeOutput] = []
    calculates = meta.get("calculates") or []
    for item in calculates:
        param_id = str(item).strip()
        if not param_id:
            continue
        param_meta = store.metadata(param_id)
        input_id = str(param_meta.get("input_id", "")).strip()
        symbol = str(param_meta.get("symbol", "")).strip()
        value = None
        if input_id and input_id in raw_outputs:
            value = raw_outputs[input_id]
        elif symbol and symbol in raw_outputs:
            value = raw_outputs[symbol]
        else:
            for key, candidate in raw_outputs.items():
                if key in {input_id, symbol, f"required_{input_id}"}:
                    value = candidate
                    break
        item_output = _param_output(store, param_id, value=value, task=task)
        if item_output is not None:
            outputs.append(item_output)
    return outputs


def _lookup_node_outputs(
    store: GraphStore,
    node_id: str,
    meta: dict[str, Any],
    raw_outputs: dict[str, Any],
    task: Task,
) -> list[NodeOutput]:
    outputs: list[NodeOutput] = []
    declared = [str(item).strip() for item in (meta.get("outputs") or []) if str(item).strip()]
    if not declared:
        output_param = str(meta.get("output_param", "")).strip()
        if output_param:
            declared = [output_param]

    for param_id in declared:
        param_meta = store.metadata(param_id)
        input_id = str(param_meta.get("input_id", "")).strip()
        symbol = str(param_meta.get("symbol", "")).strip()
        value = raw_outputs.get(input_id) or raw_outputs.get(symbol) or raw_outputs.get("value")
        item_output = _param_output(store, param_id, value=value, task=task)
        if item_output is not None:
            outputs.append(item_output)

    for key, label in (
        ("outside_diameter_mm", "Outside diameter"),
        ("outside_diameter_in", "Outside diameter"),
        ("wall_thickness_mm", "Wall thickness"),
        ("wall_thickness_in", "Wall thickness"),
        ("actual_wall_thickness", "Wall thickness"),
    ):
        if key in raw_outputs:
            outputs.append(
                NodeOutput(
                    name=key,
                    label=label,
                    value=raw_outputs[key],
                    unit="mm" if key.endswith("_mm") else ("in" if key.endswith("_in") else "dimensionless"),
                    param_node_id=None,
                )
            )
    return _dedupe_outputs(outputs)


def _attach_task_lookup_outputs(
    task: Task,
    store: GraphStore,
    by_node: dict[str, list[NodeOutput]],
) -> None:
    for key, payload in task.outputs.items():
        if not any(key.endswith(suffix) for suffix in _LOOKUP_OUTPUT_SUFFIXES):
            continue
        if not isinstance(payload, dict):
            continue
        node_id = _lookup_node_for_output_key(store, key)
        if not node_id:
            continue
        meta = store.metadata(node_id)
        outputs = _lookup_payload_outputs(store, meta, payload, task)
        if outputs:
            by_node.setdefault(node_id, []).extend(outputs)


def _lookup_payload_outputs(
    store: GraphStore,
    meta: dict[str, Any],
    payload: dict[str, Any],
    task: Task,
) -> list[NodeOutput]:
    outputs: list[NodeOutput] = []
    output_param = str(meta.get("output_param", "")).strip()
    if output_param and payload.get("value") is not None:
        item = _param_output(store, output_param, value=payload.get("value"), task=task)
        if item is not None:
            outputs.append(item)

    for key, label in (
        ("outside_diameter_mm", "Outside diameter"),
        ("outside_diameter_in", "Outside diameter"),
        ("wall_thickness_mm", "Wall thickness"),
        ("wall_thickness_in", "Wall thickness"),
    ):
        if key in payload:
            outputs.append(
                NodeOutput(
                    name=key.replace("_mm", "").replace("_in", ""),
                    label=label,
                    value=payload[key],
                    unit="mm" if key.endswith("_mm") else "in",
                )
            )
    return _dedupe_outputs(outputs)


def _lookup_node_for_output_key(store: GraphStore, output_key: str) -> str | None:
    stem = output_key
    for suffix in _LOOKUP_OUTPUT_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    for node in store.list_nodes(node_type="equation"):
        meta = node.metadata
        if not is_lookup_node(meta, "equation"):
            continue
        output_param = str(meta.get("output_param", "")).strip()
        if not output_param:
            continue
        param_meta = store.metadata(output_param)
        input_id = str(param_meta.get("input_id", "")).strip()
        symbol = str(param_meta.get("symbol", "")).strip()
        if stem in {input_id, symbol, node.node_id}:
            return node.node_id
    return None


def _attach_selection_outputs(
    task: Task,
    store: GraphStore,
    by_node: dict[str, list[NodeOutput]],
) -> None:
    for node in store.list_nodes(node_type="parameter"):
        input_id = str(node.metadata.get("input_id", "")).strip()
        if not input_id:
            continue
        if not _references_designation(store, node.node_id):
            continue
        engineering_input = task.inputs.get(input_id)
        if not _is_confirmed_selection(engineering_input):
            continue
        item = _param_output(
            store,
            node.node_id,
            value=engineering_input.value,
            task=task,
        )
        if item is not None:
            by_node.setdefault(node.node_id, []).append(item)


def _references_designation(store: GraphStore, param_node_id: str) -> bool:
    for edge in store.outgoing(param_node_id, edge_types={"references"}):
        if store.node_type(edge.to_id) == "designation":
            return True
    return False


def _attach_workflow_completion(
    task: Task,
    store: GraphStore,
    by_node: dict[str, list[NodeOutput]],
) -> None:
    if task.status != TaskStatus.COMPLETED:
        return
    workflow_id = str(
        task.outputs.get("workflow")
        or task.outputs.get("selected_root")
        or task.outputs.get("graph_root")
        or ""
    ).strip()
    if not workflow_id:
        return
    root_id = _WORKFLOW_ROOT_ALIASES.get(workflow_id, workflow_id)
    if store.get_node(root_id) is None:
        return
    title = str(store.metadata(root_id).get("title") or "Workflow").strip()
    by_node.setdefault(root_id, []).append(
        NodeOutput(
            name="workflow_status",
            label="Completed Task",
            value="completed",
            unit="dimensionless",
        )
    )
    goal_param = str(store.metadata(root_id).get("goal_output", "")).strip()
    if goal_param:
        goal_meta = store.metadata(goal_param)
        goal_input_id = str(goal_meta.get("input_id", "")).strip()
        goal_value = None
        if goal_input_id:
            goal_value = task.outputs.get(goal_input_id)
            if goal_value is None and goal_input_id in task.inputs:
                goal_value = task.inputs[goal_input_id].value
        if goal_value is not None:
            item = _param_output(store, goal_param, value=goal_value, task=task)
            if item is not None:
                by_node.setdefault(root_id, []).append(item)


def _resolve_unit(task: Task, input_id: str, param_meta: dict[str, Any]) -> str:
    unit_key = f"{input_id}_unit"
    if unit_key in task.outputs:
        return str(task.outputs[unit_key])
    if input_id in task.inputs:
        return task.inputs[input_id].unit
    if input_id == "thickness" and "required_thickness_unit" in task.outputs:
        return str(task.outputs["required_thickness_unit"])
    return str(param_meta.get("unit") or "dimensionless")


def _is_confirmed_selection(engineering_input: EngineeringInput | None) -> bool:
    if engineering_input is None:
        return False
    if engineering_input.value is None:
        return False
    return engineering_input.status in {
        InputStatus.CONFIRMED,
        InputStatus.USER_OVERRIDE,
    }


def _dedupe_outputs(outputs: list[NodeOutput]) -> list[NodeOutput]:
    seen: set[tuple[str, str]] = set()
    unique: list[NodeOutput] = []
    for item in outputs:
        key = (item.name, item.label)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
