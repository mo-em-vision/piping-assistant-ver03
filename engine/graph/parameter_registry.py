"""Seed and manage parameter descriptors from definition-node nomenclature."""

from __future__ import annotations

from typing import Any

from engine.graph.path_decision import active_path_branch_nodes
from engine.reference.standards_reader import StandardsReader
from engine.state.task_facts import pending_parameter_fact_from_descriptor
from models.fact import Fact
from models.input import (
    ParameterDescriptor,
    ResolutionMethod,
    ResolutionRef,
)


_DEFINITION_NODE = "B313-304.1.1"


def _active_branch_nodes(
    reader: StandardsReader,
    execution_order: tuple[str, ...] | list[str],
    existing_inputs: dict[str, Fact | Any] | None = None,
) -> set[str]:
    from engine.graph.graph_engine import GraphEngine

    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    if micro is None:
        return set()
    return set(
        active_path_branch_nodes(
            micro.store,
            execution_order,
            existing_inputs or {},
        )
    )


def _parse_resolution_method(raw: str | None) -> ResolutionMethod | None:
    if not raw:
        return None
    mapping = {
        "user_input": ResolutionMethod.USER_INPUT,
        "table_lookup": ResolutionMethod.TABLE_LOOKUP,
        "equation": ResolutionMethod.EQUATION,
        "node_output": ResolutionMethod.NODE_OUTPUT,
        "default_confirmed": ResolutionMethod.DEFAULT_CONFIRMED,
    }
    return mapping.get(raw)


def _resolution_ref_from_item(item: dict[str, Any]) -> ResolutionRef | None:
    resolution = item.get("resolution")
    if isinstance(resolution, dict):
        return ResolutionRef(
            table=str(resolution["table"]) if resolution.get("table") else None,
            node_id=str(resolution["node_id"]) if resolution.get("node_id") else None,
            equation_id=str(resolution.get("equation_id", "")) or None,
            subsection=str(resolution["subsection"]) if resolution.get("subsection") else None,
        )
    if isinstance(resolution, list) and resolution:
        first = resolution[0]
        if isinstance(first, dict):
            return ResolutionRef(
                table=str(first["table"]) if first.get("table") else None,
                node_id=str(first["node_id"]) if first.get("node_id") else None,
                equation_id=str(first.get("equation_id", "")) or None,
                subsection=str(first["subsection"]) if first.get("subsection") else None,
            )
    refs = item.get("references") or []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        if ref.get("table") or ref.get("file"):
            return ResolutionRef(
                table=str(ref.get("table") or ref.get("file", "")),
                node_id=str(ref["node_id"]) if ref.get("node_id") else None,
            )
    return None


def _active_thickness_nodes(
    reader: StandardsReader,
    execution_order: tuple[str, ...] | list[str],
    existing_inputs: dict[str, Fact | Any] | None = None,
) -> set[str]:
    return _active_branch_nodes(reader, execution_order, existing_inputs)


def seed_parameter_registry(
    reader: StandardsReader,
    *,
    execution_order: tuple[str, ...] | list[str],
    existing_inputs: dict[str, Fact | Any] | None = None,
) -> dict[str, ParameterDescriptor]:
    """Register parameters from legacy definition-node nomenclature.

    Deprecated: micro-graph workflows use ``MicroGraphEngine.seed_parameter_registry``.
    Only called when ``VER03_LEGACY_GRAPH_TRAVERSAL`` is enabled or graph cache is absent.
    """
    import warnings

    warnings.warn(
        "seed_parameter_registry from definition nomenclature is deprecated; "
        "use micro-graph parameter nodes.",
        DeprecationWarning,
        stacklevel=2,
    )
    if _DEFINITION_NODE not in execution_order:
        return {}

    active_thickness = _active_thickness_nodes(reader, execution_order, existing_inputs)
    if not active_thickness:
        return {}

    record = reader.load(_DEFINITION_NODE)
    registry: dict[str, ParameterDescriptor] = {}

    for item in record.metadata.get("nomenclature", []) or []:
        if not isinstance(item, dict):
            continue
        if not item.get("introduced_here"):
            continue

        symbol = str(item.get("symbol", "")).strip()
        input_id = str(item.get("input_id", "")).strip() or symbol
        if not symbol:
            continue

        resolution = item.get("resolution")
        method_raw: str | None = None
        required_when: tuple[str, ...] = ()
        if isinstance(resolution, dict):
            method_raw = str(resolution.get("method", "")) or None
            required_when = tuple(
                str(node) for node in (resolution.get("required_when_nodes") or [])
            )
        elif isinstance(resolution, list):
            for entry in resolution:
                if isinstance(entry, dict) and entry.get("method"):
                    method_raw = str(entry["method"])
                    break

        if required_when and not active_thickness.intersection(required_when):
            continue

        registry[input_id] = ParameterDescriptor(
            input_id=input_id,
            symbol=symbol,
            description=str(item.get("description", "")).strip(),
            introduced_at_node=_DEFINITION_NODE,
            unit=str(item.get("unit", "dimensionless")),
            resolution_method=_parse_resolution_method(method_raw),
            resolution_ref=_resolution_ref_from_item(item),
            required_when_nodes=tuple(active_thickness),
        )

    for node_id in active_thickness:
        calc_record = reader.load(node_id)
        for spec in calc_record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            input_id = str(spec.get("id", ""))
            if not input_id or input_id in registry:
                continue
            symbol = str(spec.get("name", input_id))
            registry[input_id] = ParameterDescriptor(
                input_id=input_id,
                symbol=symbol,
                description=str(spec.get("description", "")),
                introduced_at_node=_DEFINITION_NODE,
                unit=str(spec.get("unit", "dimensionless")),
                required_when_nodes=(node_id,),
            )

    return registry


def apply_registry_to_inputs(
    registry: dict[str, ParameterDescriptor],
    existing_inputs: dict[str, Fact | Any],
    *,
    task_id: str,
) -> dict[str, Fact]:
    """Create pending fact placeholders for unregistered parameters."""
    proposed: dict[str, Fact] = {}
    for input_id, descriptor in registry.items():
        if input_id in existing_inputs:
            continue
        proposed[input_id] = pending_parameter_fact_from_descriptor(descriptor, task_id=task_id)
    return proposed


def merge_descriptor_into_fact(
    fact: Fact,
    descriptor: ParameterDescriptor,
) -> Fact:
    """Enrich a fact with registry metadata when absent."""
    if fact.symbol is None:
        fact.symbol = descriptor.symbol
    if fact.description is None:
        fact.description = descriptor.description
    if fact.introduced_at_node is None:
        fact.introduced_at_node = descriptor.introduced_at_node
    return fact
