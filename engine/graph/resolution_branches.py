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


def _param_metadata_block(metadata: dict[str, Any]) -> dict[str, Any]:
    nested = metadata.get("metadata")
    if isinstance(nested, dict):
        return nested
    return metadata


def default_resolution_branch_id(metadata: dict[str, Any]) -> str | None:
    """Return validated default branch id from PARAM ``default_value`` metadata."""
    block = _param_metadata_block(metadata)
    default = block.get("default_value")
    if default is None:
        default = metadata.get("default_value")
    if default is None:
        return None
    default_str = str(default).strip()
    if not default_str:
        return None
    branch_ids = {
        str(branch.get("id") or "").strip()
        for branch in resolution_branches_from_metadata(metadata)
        if str(branch.get("id") or "").strip()
    }
    if default_str in branch_ids:
        return default_str
    return None


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
    from engine.graph.lookup_parameter_resolution import (
        _lookup_keys_from_metadata,
        _table_id_from_metadata,
        lookup_resolution_for_parameter,
    )

    keys = via_parameter_keys(store, branch)
    lookup_id = str(branch.get("lookup") or "").strip()
    table_id = ""
    if lookup_id:
        lookup_node = store.get_node(lookup_id)
        if lookup_node is not None:
            for key_name in _lookup_keys_from_metadata(store, lookup_node.metadata):
                if key_name and key_name not in keys:
                    keys.append(key_name)
            table_id = _table_id_from_metadata(lookup_node.metadata)

    inferred = lookup_resolution_for_parameter(
        store,
        param_node_id,
        active_nodes=active_nodes,
        inputs=inputs,
        branch_lookup_id=lookup_id or None,
    )
    resolution: dict[str, Any] = {
        "method": "table_lookup",
        "branch_id": str(branch.get("id") or "").strip(),
        "keys": keys or (inferred.get("keys") if isinstance(inferred, dict) else []) or [],
    }
    if lookup_id:
        resolution["lookup_node_id"] = lookup_id
    if table_id:
        resolution["table_id"] = table_id
    if isinstance(inferred, dict):
        for field_name in ("table_id", "table_ids", "lookup_conditionals", "lookup_node_id"):
            if inferred.get(field_name) is not None and resolution.get(field_name) is None:
                resolution[field_name] = inferred[field_name]
    return resolution


def clear_outside_diameter_lookup_output(task: Any) -> None:
    """Remove stale B36.10 lookup metadata when direct OD is selected."""
    outputs = getattr(task, "outputs", None)
    if isinstance(outputs, dict) and "outside_diameter_lookup" in outputs:
        del outputs["outside_diameter_lookup"]


def apply_resolution_branch_defaults(task: Any) -> bool:
    """Seed resolution-branch facts from PARAM ``default_value`` metadata."""
    from engine.reference.knowledge_paths import parameters_root
    from engine.reference.standards_markdown import split_frontmatter
    from engine.state.task_facts import active_facts, store_system_categorical_fact

    added = False
    nodes_dir = parameters_root() / "nodes"
    if not nodes_dir.is_dir():
        return False

    for path in sorted(nodes_dir.glob("PARAM-*.yaml")):
        metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        if str(metadata.get("type", "")) != "parameter":
            continue
        block = _param_metadata_block(metadata)
        if str(block.get("composer_input") or metadata.get("composer_input") or "").strip() != "resolution_branch":
            continue
        default_branch = default_resolution_branch_id(metadata)
        if not default_branch:
            continue
        param_key = str(metadata.get("key") or "").strip()
        if not param_key:
            continue
        branch_key = resolution_branch_fact_key(param_key)
        if active_resolution_branch_id(param_key, active_facts(task)) is not None:
            continue
        if task.fact_store.active_fact(branch_key) is not None:
            continue
        store_system_categorical_fact(task, key=branch_key, label=default_branch)
        added = True
    return added


def clear_conflicting_branch_facts(task: Any, *, anchor_key: str, branch_id: str) -> None:
    """Deactivate facts that belong to the non-selected resolution branch."""
    from engine.state.task_facts import deactivate_fact

    branch = str(branch_id or "").strip()
    if branch == "nps_lookup":
        deactivate_fact(task, anchor_key)
    elif branch == "direct_od":
        deactivate_fact(task, "nominal_pipe_size")
        deactivate_fact(task, "pipe_schedule")
        if canonical_parameter_key(anchor_key) == "outside_diameter":
            clear_outside_diameter_lookup_output(task)
