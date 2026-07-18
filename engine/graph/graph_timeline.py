"""Timeline ordering derived from micro-graph parameter nodes."""

from __future__ import annotations

from engine.graph.graph_store import GraphStore
from engine.graph.param_priority import parameter_collection_priority
from engine.reference.node_types import is_ui_parameter, parameter_input_id
from engine.reference.parameter_metadata import parameter_prompt_text
from engine.reference.standards_reader import StandardsReader
from models.execution import ExecutionPlan


def graph_input_step_order(
    reader: StandardsReader,
    plan: ExecutionPlan,
) -> tuple[str, ...]:
    store = GraphStore(reader.pack_root)
    if not store.available:
        return ()
    active_nodes = set(plan.nodes) if plan.nodes else set(plan.execution_order)
    priorities: list[tuple[int, str, str]] = []
    for node_id in plan.execution_order:
        node = store.get_node(node_id)
        if node is None or node.node_type != "parameter":
            continue
        if is_ui_parameter(node.metadata, node.node_type):
            continue
        input_id = str(
            node.metadata.get("input_id") or node.metadata.get("key") or ""
        ).strip()
        if not input_id:
            continue
        priority = parameter_collection_priority(store, node_id, active_nodes)
        title = str(node.metadata.get("title") or input_id)
        priorities.append((priority, input_id, title))
    priorities.sort(key=lambda item: (item[0], item[1]))
    return tuple(input_id for _, input_id, _ in priorities)


def graph_step_titles(
    reader: StandardsReader,
    plan: ExecutionPlan,
) -> dict[str, str]:
    store = GraphStore(reader.pack_root)
    titles: dict[str, str] = {}
    if not store.available:
        return titles
    for node_id in plan.execution_order:
        node = store.get_node(node_id)
        if node is None:
            continue
        if node.node_type == "parameter":
            input_id = str(
                node.metadata.get("input_id") or node.metadata.get("key") or ""
            ).strip()
            if not input_id:
                continue
            titles[input_id] = str(
                node.metadata.get("title") or node.metadata.get("name") or input_id
            )
    return titles


def graph_question_for_field(
    reader: StandardsReader,
    field_name: str,
) -> str | None:
    store = GraphStore(reader.pack_root)
    if not store.available:
        return None
    for node in store.list_nodes():
        if node.node_type != "parameter":
            continue
        field = parameter_input_id(node.metadata)
        if field == field_name:
            prompt = parameter_prompt_text(node.metadata)
            if prompt:
                return prompt
    return None
