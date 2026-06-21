"""Seed and manage parameter descriptors from definition-node nomenclature."""

from __future__ import annotations

from typing import Any

from engine.reference.standards_reader import StandardsReader
from models.input import (
    EngineeringInput,
    ParameterDescriptor,
    ResolutionMethod,
    ResolutionRef,
    pending_parameter_input,
)


_DEFINITION_NODE = "B313-304.1.1"
_THICKNESS_NODES = frozenset({"B313-304.1.2", "B313-304.1.3"})


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
) -> set[str]:
    return {node_id for node_id in execution_order if node_id in _THICKNESS_NODES}


def seed_parameter_registry(
    reader: StandardsReader,
    *,
    execution_order: tuple[str, ...] | list[str],
    existing_inputs: dict[str, EngineeringInput | Any] | None = None,
) -> dict[str, ParameterDescriptor]:
    """Register parameters from nomenclature when definition node is on active path."""
    if _DEFINITION_NODE not in execution_order:
        return {}

    active_thickness = _active_thickness_nodes(reader, execution_order)
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
    existing_inputs: dict[str, EngineeringInput | Any],
) -> dict[str, EngineeringInput]:
    """Create pending EngineeringInput placeholders for unregistered parameters."""
    proposed: dict[str, EngineeringInput] = {}
    for input_id, descriptor in registry.items():
        if input_id in existing_inputs:
            continue
        proposed[input_id] = pending_parameter_input(descriptor)
    return proposed


def merge_descriptor_into_input(
    engineering_input: EngineeringInput,
    descriptor: ParameterDescriptor,
) -> EngineeringInput:
    """Enrich an input with registry metadata when absent."""
    if engineering_input.symbol is None:
        engineering_input.symbol = descriptor.symbol
    if engineering_input.description is None:
        engineering_input.description = descriptor.description
    if engineering_input.introduced_at_node is None:
        engineering_input.introduced_at_node = descriptor.introduced_at_node
    if engineering_input.resolution_method is None:
        engineering_input.resolution_method = descriptor.resolution_method
    if engineering_input.resolution_ref is None:
        engineering_input.resolution_ref = descriptor.resolution_ref
    return engineering_input
