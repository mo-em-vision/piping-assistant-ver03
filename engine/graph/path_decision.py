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
from models.fact import Fact

from engine.graph.workflow_adapters import PATH_DECISION_FIELDS as _PATH_DECISION_FIELDS


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


def resolve_path_decision(
    store: GraphStore | None,
    exec_nodes: list[str],
    inputs: dict[str, Fact | Any],
) -> dict[str, str] | None:
    """Return the active branch decision derived from inputs and expanded graph nodes."""
    if store is not None:
        for field_name in _PATH_DECISION_FIELDS:
            value = field_value(field_name, inputs)
            if not value:
                continue
            for node_id in exec_nodes:
                node = store.get_node(node_id)
                if node is None:
                    continue
                if applicability_expansion_status(node.metadata, inputs) != "satisfied":
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

    loading = field_value("pressure_loading", inputs)
    if loading:
        return {"field": "pressure_loading", "value": loading}

    return None
