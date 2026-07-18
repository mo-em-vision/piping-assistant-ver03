"""Resolve workflow path decisions from expanded graph nodes and task inputs."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import (
    _field_from_param_ref,
    applicability_expansion_status,
    field_value,
    normalize_assumption_value,
)
from engine.graph.graph_store import GraphStore
from engine.reference.parameter_metadata import is_path_decision_parameter
from engine.reference.parameter_keys import load_parameter_node_metadata
from models.fact import Fact


def _applies_when_matches_field(
    metadata: dict[str, Any],
    *,
    field_name: str,
    field_value_text: str,
) -> bool:
    applicability = metadata.get("applicability") or {}
    if not isinstance(applicability, dict):
        return False
    for item in applicability.get("applies_when") or []:
        if not isinstance(item, dict):
            continue
        clause_field = _field_from_param_ref(str(item.get("parameter") or ""))
        if clause_field != field_name:
            continue
        if str(item.get("operator") or "equals") != "equals":
            continue
        if normalize_assumption_value(item.get("value")) == field_value_text:
            return True
    return False


def _path_decision_fields_from_applies_when(metadata: dict[str, Any]) -> list[str]:
    """Return path-decision field keys referenced by paragraph applicability clauses."""
    applicability = metadata.get("applicability") or {}
    if not isinstance(applicability, dict):
        return []
    fields: list[str] = []
    for item in applicability.get("applies_when") or []:
        if not isinstance(item, dict):
            continue
        param_ref = str(item.get("parameter") or "")
        field_name = _field_from_param_ref(param_ref)
        if not field_name or field_name in fields:
            continue
        param_meta = load_parameter_node_metadata(param_ref) if param_ref.startswith("PARAM-") else None
        if param_meta is not None and is_path_decision_parameter(param_meta):
            fields.append(field_name)
    return fields


def active_path_branch_nodes(
    store: GraphStore,
    execution_order: tuple[str, ...] | list[str],
    inputs: dict[str, Fact | Any],
) -> list[str]:
    """Paragraph nodes on the execution path whose applicability matches current inputs."""
    branches: list[str] = []
    for node_id in execution_order:
        node = store.get_node(node_id)
        if node is None or node.node_type != "paragraph":
            continue
        if applicability_expansion_status(node.metadata, inputs) != "satisfied":
            continue
        applicability = node.metadata.get("applicability") or {}
        applies_when = applicability.get("applies_when") if isinstance(applicability, dict) else None
        if applies_when:
            branches.append(node_id)
    return branches


def pending_path_branch_nodes(
    store: GraphStore,
    execution_order: tuple[str, ...] | list[str],
    inputs: dict[str, Fact | Any],
) -> list[dict[str, str]]:
    """Paragraph branch nodes waiting on an unresolved path-decision parameter."""
    pending: list[dict[str, str]] = []
    for node_id in execution_order:
        node = store.get_node(node_id)
        if node is None or node.node_type != "paragraph":
            continue
        if applicability_expansion_status(node.metadata, inputs) != "pending":
            continue
        decision_fields = _path_decision_fields_from_applies_when(node.metadata)
        if not decision_fields:
            continue
        pending.append(
            {
                "node_id": node_id,
                "field": decision_fields[0],
            }
        )
    return pending


def resolve_path_decision(
    store: GraphStore | None,
    exec_nodes: list[str],
    inputs: dict[str, Fact | Any],
) -> dict[str, str] | None:
    """Return the active branch decision derived from inputs and expanded graph nodes."""
    if store is None:
        return None
    for node_id in exec_nodes:
        node = store.get_node(node_id)
        if node is None or node.node_type != "paragraph":
            continue
        if applicability_expansion_status(node.metadata, inputs) != "satisfied":
            continue
        decision_fields = _path_decision_fields_from_applies_when(node.metadata)
        if not decision_fields:
            continue
        for field_name in decision_fields:
            value = field_value(field_name, inputs)
            if not value:
                continue
            if _applies_when_matches_field(
                node.metadata,
                field_name=field_name,
                field_value_text=value,
            ):
                return {
                    "field": field_name,
                    "value": value,
                    "selected_node": node_id,
                }
    return None
