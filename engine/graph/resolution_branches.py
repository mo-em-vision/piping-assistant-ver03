"""Resolution branch helpers for multi-path PARAM nodes."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.graph_store import GraphStore
from engine.reference.parameter_keys import canonical_parameter_key
from models.fact import Fact

RESOLUTION_BRANCH_SUFFIX = "__resolution_branch"


def resolution_branch_fact_key(parameter_key: str) -> str:
    """Runtime fact key storing the user's branch choice for an anchor parameter."""
    canonical = canonical_parameter_key(str(parameter_key or "").strip())
    return f"{canonical}{RESOLUTION_BRANCH_SUFFIX}"


def resolution_branches_from_metadata(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Return authored resolution branch specs from a PARAM node."""
    branches = metadata.get("resolution_branches")
    if isinstance(branches, list):
        return [item for item in branches if isinstance(item, dict)]
    nested = metadata.get("metadata")
    if isinstance(nested, dict):
        nested_branches = nested.get("resolution_branches")
        if isinstance(nested_branches, list):
            return [item for item in nested_branches if isinstance(item, dict)]
    return []


def has_resolution_branches(metadata: dict[str, Any]) -> bool:
    return bool(resolution_branches_from_metadata(metadata))


def active_resolution_branch_id(
    parameter_key: str,
    inputs: dict[str, Fact | Any],
) -> str | None:
    return field_value(resolution_branch_fact_key(parameter_key), inputs)


def find_resolution_branch(metadata: dict[str, Any], branch_id: str) -> dict[str, Any] | None:
    target = str(branch_id or "").strip()
    if not target:
        return None
    for branch in resolution_branches_from_metadata(metadata):
        if str(branch.get("id") or "").strip() == target:
            return branch
    return None


def _resolve_param_key(store: GraphStore, param_ref: str) -> str:
    text = str(param_ref or "").strip()
    if not text:
        return ""
    if text.startswith("PARAM-"):
        node = store.get_node(text)
        if node is not None:
            return canonical_parameter_key(str(node.metadata.get("key") or ""))
        from engine.reference.workflow_sidecar import _PARAM_TO_FIELD

        mapped = _PARAM_TO_FIELD.get(text)
        if mapped:
            return canonical_parameter_key(mapped)
    return canonical_parameter_key(text)


def via_parameter_keys(store: GraphStore, branch: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for raw in branch.get("via_parameters") or []:
        resolved = _resolve_param_key(store, str(raw))
        if resolved and resolved not in keys:
            keys.append(resolved)
    return keys


def branch_table_lookup_resolution(
    store: GraphStore,
    param_node_id: str,
    metadata: dict[str, Any],
    branch: dict[str, Any],
    *,
    active_nodes: set[str] | None = None,
    inputs: dict[str, Fact] | None = None,
) -> dict[str, Any] | None:
    """Build table_lookup resolution for an active resolution branch."""
    from engine.graph.lookup_parameter_resolution import lookup_resolution_for_parameter

    keys = via_parameter_keys(store, branch)
    lookup_id = str(branch.get("lookup") or "").strip()
    if lookup_id:
        lookup_node = store.get_node(lookup_id)
        if lookup_node is not None:
            from engine.graph.lookup_parameter_resolution import _lookup_keys_from_metadata

            for key_name in _lookup_keys_from_metadata(store, lookup_node.metadata):
                if key_name and key_name not in keys:
                    keys.append(key_name)

    inferred = lookup_resolution_for_parameter(
        store,
        param_node_id,
        active_nodes=active_nodes,
        inputs=inputs,
    )
    resolution: dict[str, Any] = {
        "method": "table_lookup",
        "branch_id": str(branch.get("id") or "").strip(),
        "keys": keys or (inferred.get("keys") if isinstance(inferred, dict) else []) or [],
    }
    if isinstance(inferred, dict):
        for field_name in ("table_id", "table_ids", "lookup_conditionals"):
            if inferred.get(field_name) is not None:
                resolution[field_name] = inferred[field_name]
    return resolution


def clear_conflicting_branch_facts(task: Any, *, anchor_key: str, branch_id: str) -> None:
    """Deactivate facts that belong to the non-selected resolution branch."""
    from engine.state.task_facts import deactivate_fact

    branch = str(branch_id or "").strip()
    if branch == "nps_lookup":
        deactivate_fact(task, "outside_diameter")
    elif branch == "direct_od":
        deactivate_fact(task, "nominal_pipe_size")
        deactivate_fact(task, "pipe_schedule")
