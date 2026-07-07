"""Build structured workflow parameters from task state and the graph."""

from __future__ import annotations

from typing import Any

from engine.graph.graph_store import GraphStore
from engine.graph.param_priority import parameter_collection_priority
from engine.reference.node_types import is_designation_node, is_quantity_node
from engine.reference.parameter_metadata import parameter_concept_id
from engine.reference.relationship_taxonomy import PARAMETER_CONCEPT_TRAVERSAL_TYPES
from engine.reference.standards_reader import StandardsReader
from engine.units.unit_registry import get_unit_registry
from models.fact import Fact, FactClass, fact_scalar_value, fact_unit
from models.task import Task
from models.workflow_state import WorkflowParameter

_CONTROL_OUTPUT_KEYS = {
    "workflow",
    "selected_root",
    "graph_root",
    "graph_version",
    "_execution_trace",
    "_validation_trace",
}

_DEFAULT_PRIORITY = 100

_OUTPUT_KEY_PARAM_CANDIDATES: dict[str, tuple[str, ...]] = {
    "required_thickness": ("thickness", "t"),
    "minimum_required_thickness": ("minimum_required_thickness", "t_m"),
    "allowable_stress": ("allowable_stress", "S"),
    "mawp": ("mawp", "MAWP"),
}


def build_workflow_parameters(
    task: Task,
    *,
    reader: StandardsReader,
    active_nodes: set[str] | frozenset[str] | None = None,
) -> dict[str, WorkflowParameter]:
    store = reader.graph_store
    if not store.available:
        return _parameters_without_graph(task)

    active = _resolve_active_nodes(task, active_nodes)
    param_index = _param_nodes_by_input_id(store, active)

    parameters: dict[str, WorkflowParameter] = {}
    for name, fact in task.fact_store.active_facts().items():
        param_node_id = param_index.get(name)
        parameters[name] = _parameter_from_fact(
            store,
            name=name,
            fact=fact,
            param_node_id=param_node_id,
            active_nodes=active,
        )

    for name, value in task.outputs.items():
        if name in _CONTROL_OUTPUT_KEYS or name.endswith("_lookup"):
            continue
        if name.endswith("_unit"):
            continue
        if name in parameters:
            continue
        param_node_id = param_index.get(name) or _find_param_node_for_output(store, name, value)
        parameters[name] = _parameter_from_output(
            store,
            name=name,
            value=value,
            task=task,
            param_node_id=param_node_id,
            active_nodes=active,
        )

    return parameters


def _parameters_without_graph(task: Task) -> dict[str, WorkflowParameter]:
    parameters: dict[str, WorkflowParameter] = {}
    for name, fact in task.fact_store.active_facts().items():
        parameters[name] = WorkflowParameter(
            name=name,
            value=fact_scalar_value(fact),
            dimension=None,
            unit=fact_unit(fact),
            priority=_DEFAULT_PRIORITY,
            source=_workflow_source_from_fact(fact),
            status=fact.validation.status.value,
            symbol=fact.symbol,
        )
    for name, value in task.outputs.items():
        if name in _CONTROL_OUTPUT_KEYS or name.endswith("_lookup") or name.endswith("_unit"):
            continue
        if name in parameters:
            continue
        parameters[name] = WorkflowParameter(
            name=name,
            value=value,
            dimension=None,
            unit=_output_unit(task, name),
            priority=_DEFAULT_PRIORITY,
            source="derived",
            status="confirmed",
        )
    return parameters


def _resolve_active_nodes(
    task: Task,
    active_nodes: set[str] | frozenset[str] | None,
) -> set[str]:
    if active_nodes is not None:
        return set(active_nodes)
    nodes = set(task.active_nodes)
    trace = task.outputs.get("_execution_trace")
    if isinstance(trace, list):
        for item in trace:
            if isinstance(item, dict):
                node_id = item.get("node_id")
                if node_id:
                    nodes.add(str(node_id))
            elif isinstance(item, str) and item.strip():
                nodes.add(item.strip())
    graph_version = task.outputs.get("graph_version")
    if isinstance(graph_version, dict):
        for node_id in graph_version.get("nodes", []) or []:
            if node_id:
                nodes.add(str(node_id))
    return nodes


def _param_nodes_by_input_id(store: GraphStore, active_nodes: set[str]) -> dict[str, str]:
    index: dict[str, str] = {}

    def register(node_id: str, metadata: dict[str, Any]) -> None:
        input_id = str(metadata.get("input_id") or metadata.get("key") or "").strip()
        if input_id and input_id not in index:
            index[input_id] = node_id

    for node_id in active_nodes:
        node = store.get_node(node_id)
        if node is None or node.node_type != "parameter":
            continue
        register(node_id, node.metadata)
    for node in store.list_nodes(node_type="parameter"):
        register(node.node_id, node.metadata)
    return index


def _find_param_node_for_output(
    store: GraphStore,
    output_key: str,
    value: Any,
) -> str | None:
    candidates = {output_key, *_OUTPUT_KEY_PARAM_CANDIDATES.get(output_key, ())}
    for node in store.list_nodes(node_type="parameter"):
        input_id = str(node.metadata.get("input_id", "")).strip()
        symbol = str(node.metadata.get("symbol", "")).strip()
        if input_id in candidates or symbol in candidates:
            return node.node_id
    return None


def _concept_metadata(
    store: GraphStore,
    param_node_id: str | None,
) -> tuple[str | None, str | None, bool]:
    if not param_node_id:
        return None, None, False
    for edge in store.outgoing(param_node_id, edge_types=PARAMETER_CONCEPT_TRAVERSAL_TYPES | {"has_dimension"}):
        ref_meta = store.metadata(edge.to_id)
        ref_type = store.node_type(edge.to_id) or ""
        if is_quantity_node(ref_meta, ref_type):
            dimension = str(ref_meta.get("dimension", "")).strip() or None
            return edge.to_id, dimension, False
        if is_designation_node(ref_meta, ref_type):
            return edge.to_id, None, True
    return None, None, False


def _unit_fields(
    meta: dict[str, Any],
    *,
    dimension: str | None,
    is_designation: bool,
    unit: str,
) -> tuple[str | None, tuple[str, ...], str | None]:
    registry = get_unit_registry()
    canonical = str(meta.get("canonical_unit") or "").strip() or None
    allowed = registry.allowed_units_for_parameter(
        param_meta=meta,
        quantity_dimension=dimension,
        is_designation=is_designation,
    )
    unit_id = registry.resolver.resolve_unit_id(unit)
    return canonical, allowed, unit_id


def _parameter_from_fact(
    store: GraphStore,
    *,
    name: str,
    fact: Fact,
    param_node_id: str | None,
    active_nodes: set[str],
) -> WorkflowParameter:
    concept_id, dimension, is_designation = _concept_metadata(store, param_node_id)
    meta = store.metadata(param_node_id) if param_node_id else {}
    symbol = fact.symbol or (str(meta.get("symbol", "")).strip() if meta else None)
    priority = (
        parameter_collection_priority(store, param_node_id, active_nodes)
        if param_node_id
        else _DEFAULT_PRIORITY
    )
    unit = fact_unit(fact)
    canonical_unit, allowed_units, unit_id = _unit_fields(
        meta,
        dimension=dimension,
        is_designation=is_designation,
        unit=unit,
    )
    return WorkflowParameter(
        name=name,
        value=fact_scalar_value(fact),
        dimension=dimension,
        unit=unit,
        priority=priority,
        source=_workflow_source_from_fact(fact),
        status=fact.validation.status.value,
        symbol=symbol or None,
        param_node_id=param_node_id,
        concept_id=concept_id or parameter_concept_id(meta),
        canonical_unit=canonical_unit,
        allowed_units=allowed_units,
        unit_id=unit_id,
    )


def _parameter_from_output(
    store: GraphStore,
    *,
    name: str,
    value: Any,
    task: Task,
    param_node_id: str | None,
    active_nodes: set[str],
) -> WorkflowParameter:
    concept_id, dimension, is_designation = _concept_metadata(store, param_node_id)
    meta = store.metadata(param_node_id) if param_node_id else {}
    symbol = str(meta.get("symbol", "")).strip() or None
    priority = (
        parameter_collection_priority(store, param_node_id, active_nodes)
        if param_node_id
        else _DEFAULT_PRIORITY
    )
    active = task.fact_store.active_fact(name)
    if active is not None:
        source = _workflow_source_from_fact(active)
    else:
        source = "derived"
    output_unit = _output_unit(task, name)
    canonical_unit, allowed_units, unit_id = _unit_fields(
        meta,
        dimension=dimension,
        is_designation=is_designation,
        unit=output_unit,
    )
    return WorkflowParameter(
        name=name,
        value=value,
        dimension=dimension,
        unit=output_unit,
        priority=priority,
        source=source,
        status="confirmed",
        symbol=symbol,
        param_node_id=param_node_id,
        concept_id=concept_id or parameter_concept_id(meta),
        canonical_unit=canonical_unit,
        allowed_units=allowed_units,
        unit_id=unit_id,
    )


def _workflow_source_from_fact(fact: Fact) -> str:
    if fact.fact_class == FactClass.CALCULATED:
        return "equation"
    if fact.fact_class == FactClass.LOOKED_UP:
        return "lookup"
    if fact.fact_class == FactClass.DEFAULT_CONFIRMED:
        return "default"
    if fact.fact_class == FactClass.USER_SUPPLIED:
        return "user_input"
    if fact.source.source_type.value == "table_lookup":
        return "lookup"
    if fact.source.source_type.value == "equation":
        return "equation"
    return "derived"


def _output_unit(task: Task, key: str) -> str:
    unit_key = f"{key}_unit"
    if unit_key in task.outputs:
        return str(task.outputs[unit_key])
    active = task.fact_store.active_fact(key)
    if active is not None:
        return fact_unit(active)
    return "dimensionless"
