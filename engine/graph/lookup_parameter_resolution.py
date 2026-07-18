"""Infer parameter resolution from lookup nodes and catalog edges in the compiled graph."""

from __future__ import annotations

from typing import Any

from engine.graph.conditions import when_clause_matches
from engine.graph.resolution_branches import (
    active_resolution_branch_id,
    branch_table_lookup_resolution,
    find_resolution_branch,
    has_resolution_branches,
    resolution_branches_from_metadata,
    via_parameter_keys,
)
from engine.graph.graph_store import GraphStore
from engine.reference.parameter_keys import MATERIAL_GRADE_KEY, canonical_parameter_key
from models.fact import Fact

_CATALOG_INPUT_KEYS = frozenset({MATERIAL_GRADE_KEY, "material"})


def _resolve_lookup_key(store: GraphStore, key: str) -> str:
    """Map PARAM-* ids or legacy aliases to canonical fact keys."""
    text = str(key or "").strip()
    if not text:
        return ""
    if text.startswith("PARAM-"):
        node = store.get_node(text)
        if node is not None:
            param_key = str(node.metadata.get("key") or "").strip()
            if param_key:
                return canonical_parameter_key(param_key)
        from engine.reference.workflow_sidecar import _PARAM_TO_FIELD

        mapped = _PARAM_TO_FIELD.get(text)
        if mapped:
            return canonical_parameter_key(mapped)
    return canonical_parameter_key(text)


def _lookup_keys_from_metadata(store: GraphStore, metadata: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    lookup_cfg = metadata.get("lookup")
    if isinstance(lookup_cfg, dict):
        bindings = lookup_cfg.get("bindings")
        if isinstance(bindings, dict) and bindings:
            for param_ref in bindings.values():
                resolved = _resolve_lookup_key(store, str(param_ref))
                if resolved and resolved not in keys:
                    keys.append(resolved)
            if keys:
                return keys
    for item in metadata.get("inputs") or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("task_input_id") or item.get("id") or "").strip()
        resolved = _resolve_lookup_key(store, key)
        if resolved and resolved not in keys:
            keys.append(resolved)
    return keys


def _table_id_from_metadata(metadata: dict[str, Any]) -> str:
    lookup_cfg = metadata.get("lookup")
    if isinstance(lookup_cfg, dict):
        table_id = str(lookup_cfg.get("table") or lookup_cfg.get("table_id") or "").strip()
        if table_id:
            return table_id
    for item in metadata.get("lookups") or []:
        if not isinstance(item, dict):
            continue
        table_id = str(item.get("table_id") or item.get("table") or "").strip()
        if table_id:
            return table_id
    source = metadata.get("source")
    if isinstance(source, dict):
        return str(source.get("table_id") or "").strip()
    return ""


def _explicit_resolution_from_metadata(
    explicit: Any,
    inputs: dict[str, Fact] | None,
) -> dict[str, Any] | None:
    """Return the first authored resolution spec whose ``when`` clause matches task inputs."""
    task_inputs = inputs or {}
    if isinstance(explicit, list):
        for spec in explicit:
            if not isinstance(spec, dict):
                continue
            when = spec.get("when")
            if isinstance(when, dict) and not when_clause_matches(when, task_inputs):
                continue
            method = str(spec.get("method", "")).strip()
            if method:
                return spec
        return None
    if isinstance(explicit, dict) and explicit.get("method"):
        when = explicit.get("when")
        if isinstance(when, dict) and not when_clause_matches(when, task_inputs):
            return None
        return explicit
    return None


def lookup_resolution_for_parameter(
    store: GraphStore,
    param_node_id: str,
    *,
    active_nodes: set[str] | None = None,
    inputs: dict[str, Fact] | None = None,
    branch_lookup_id: str | None = None,
) -> dict[str, Any] | None:
    """Return table_lookup resolution inferred from active lookup nodes that output this parameter."""
    merged_keys: list[str] = []
    table_ids: list[str] = []
    lookup_node_ids: list[str] = []
    found_lookup = False
    task_inputs = inputs or {}

    from engine.graph.lazy_expander import _node_active_on_path

    branch_lookup = str(branch_lookup_id or "").strip()
    if branch_lookup:
        lookup_node = store.get_node(branch_lookup)
        if lookup_node is not None and lookup_node.node_type == "lookup":
            if active_nodes is None or branch_lookup in active_nodes:
                if _node_active_on_path(store, branch_lookup, task_inputs):
                    keys = _lookup_keys_from_metadata(store, lookup_node.metadata)
                    if keys:
                        found_lookup = True
                        lookup_node_ids.append(branch_lookup)
                        for key_name in keys:
                            if key_name not in merged_keys:
                                merged_keys.append(key_name)
                        table_id = _table_id_from_metadata(lookup_node.metadata)
                        if table_id and table_id not in table_ids:
                            table_ids.append(table_id)

    for edge in store.incoming(param_node_id, edge_types={"returns_parameter"}):
        lookup_node = store.get_node(edge.from_id)
        if lookup_node is None or lookup_node.node_type != "lookup":
            continue
        if branch_lookup and edge.from_id == branch_lookup:
            continue
        edge_when = edge.metadata.get("when") if edge.metadata else None
        if isinstance(edge_when, dict) and not when_clause_matches(edge_when, task_inputs):
            continue
        if active_nodes is not None and edge.from_id not in active_nodes:
            continue
        if not _node_active_on_path(store, edge.from_id, task_inputs):
            continue
        param_lookup_edge_active = False
        for outgoing in store.outgoing(param_node_id, edge_types={"used_by"}):
            if outgoing.to_id != edge.from_id:
                continue
            outgoing_when = outgoing.metadata.get("when") if outgoing.metadata else None
            if isinstance(outgoing_when, dict) and not when_clause_matches(outgoing_when, task_inputs):
                continue
            param_lookup_edge_active = True
            break
        if not param_lookup_edge_active:
            has_conditional_used_by = any(
                isinstance((outgoing.metadata or {}).get("when"), dict)
                for outgoing in store.outgoing(param_node_id, edge_types={"used_by"})
                if outgoing.to_id == edge.from_id
            )
            if has_conditional_used_by:
                continue
        keys = _lookup_keys_from_metadata(store, lookup_node.metadata)
        if not keys:
            continue
        found_lookup = True
        if edge.from_id not in lookup_node_ids:
            lookup_node_ids.append(edge.from_id)
        for key_name in keys:
            if key_name not in merged_keys:
                merged_keys.append(key_name)
        table_id = _table_id_from_metadata(lookup_node.metadata)
        if table_id and table_id not in table_ids:
            table_ids.append(table_id)

    if not found_lookup:
        return None

    resolution: dict[str, Any] = {"method": "table_lookup", "keys": merged_keys}
    if lookup_node_ids:
        resolution["lookup_node_id"] = lookup_node_ids[0]
        if len(lookup_node_ids) > 1:
            resolution["lookup_node_ids"] = lookup_node_ids
    if table_ids:
        resolution["table_id"] = table_ids[0]
        if len(table_ids) > 1:
            resolution["table_ids"] = table_ids

    param_node = store.get_node(param_node_id)
    if param_node is not None:
        conditionals = param_node.metadata.get("lookup_conditionals")
        if isinstance(conditionals, dict) and conditionals:
            resolution["lookup_conditionals"] = conditionals

    return resolution


def catalog_resolution_for_parameter(
    store: GraphStore,
    param_node_id: str,
) -> dict[str, Any] | None:
    """Return material_catalog resolution when a parameter is derived from MAT-catalog."""
    node = store.get_node(param_node_id)
    if node is None:
        return None

    explicit = node.metadata.get("resolution")
    if isinstance(explicit, dict) and str(explicit.get("method", "")) == "material_catalog":
        keys = [
            _resolve_lookup_key(store, str(key))
            for key in (explicit.get("keys") or [])
            if str(key).strip()
        ]
        if keys:
            return {"method": "material_catalog", "keys": keys}
        return None

    param_key = canonical_parameter_key(str(node.metadata.get("key") or ""))
    if param_key in _CATALOG_INPUT_KEYS:
        return None

    for item in node.metadata.get("edges") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("type", "")) != "used_by":
            continue
        target = str(item.get("target") or "").strip()
        if target == "MAT-catalog":
            return {"method": "material_catalog", "keys": [MATERIAL_GRADE_KEY]}

    for edge in store.outgoing(param_node_id, edge_types={"used_by"}):
        catalog_node = store.get_node(edge.to_id)
        if catalog_node is None or catalog_node.node_type != "material_catalog":
            continue
        return {"method": "material_catalog", "keys": [MATERIAL_GRADE_KEY]}

    return None


def parameter_resolution_for_parameter(
    store: GraphStore,
    param_node_id: str,
    *,
    active_nodes: set[str] | None = None,
    inputs: dict[str, Fact] | None = None,
) -> dict[str, Any] | None:
    """Resolve explicit, lookup-output, branch-choice, or catalog-derived parameter resolution."""
    node = store.get_node(param_node_id)
    if node is None:
        return None

    task_inputs = inputs or {}
    param_key = str(node.metadata.get("key") or "").strip()

    from engine.reference.parameter_metadata import is_path_decision_parameter

    if is_path_decision_parameter(node.metadata):
        from engine.graph.assumption_checker import field_value as _field_value

        if _field_value(param_key, task_inputs) is None:
            return {"method": "branch_choice", "anchor": param_key, "role": "path_decision"}

    if has_resolution_branches(node.metadata):
        branch_id = active_resolution_branch_id(param_key, task_inputs)
        if not branch_id:
            return {
                "method": "branch_choice",
                "anchor": param_key,
                "branches": resolution_branches_from_metadata(node.metadata),
            }
        branch = find_resolution_branch(node.metadata, branch_id)
        if branch is not None:
            method = str(branch.get("method", "")).strip()
            if method == "user_input":
                return {"method": "user_input", "branch_id": branch_id}
            if method == "table_lookup":
                return branch_table_lookup_resolution(
                    store,
                    param_node_id,
                    node.metadata,
                    branch,
                    active_nodes=active_nodes,
                    inputs=task_inputs,
                )

    explicit = _explicit_resolution_from_metadata(node.metadata.get("resolution"), inputs)
    if isinstance(explicit, dict) and explicit.get("method"):
        method = str(explicit.get("method", ""))
        if method == "material_catalog":
            return catalog_resolution_for_parameter(store, param_node_id)
        return explicit

    lookup_resolution = lookup_resolution_for_parameter(
        store,
        param_node_id,
        active_nodes=active_nodes,
        inputs=inputs,
    )
    if lookup_resolution is not None:
        return lookup_resolution

    return catalog_resolution_for_parameter(store, param_node_id)


def param_node_id_for_fact_key(store: GraphStore, fact_key: str) -> str | None:
    """Return PARAM-* id for a canonical runtime fact key when present in the graph."""
    canonical = canonical_parameter_key(str(fact_key or "").strip())
    if not canonical:
        return None
    for node in store.list_nodes(node_type="parameter"):
        node_key = canonical_parameter_key(str(node.metadata.get("key") or ""))
        if node_key == canonical:
            return node.node_id
    return None


def prerequisite_input_keys(
    store: GraphStore,
    fact_key: str,
) -> list[str]:
    """Expand a parameter key to the user-input keys required to resolve it."""
    canonical = canonical_parameter_key(str(fact_key or "").strip())
    if not canonical:
        return []

    param_node_id = param_node_id_for_fact_key(store, canonical)
    if param_node_id is None:
        return [canonical]

    resolution = parameter_resolution_for_parameter(
        store,
        param_node_id,
        active_nodes=None,
        inputs=None,
    )
    if not isinstance(resolution, dict):
        return [canonical]

    method = str(resolution.get("method", "user_input"))
    if method == "material_catalog":
        keys = [
            _resolve_lookup_key(store, str(key))
            for key in (resolution.get("keys") or [])
            if str(key).strip()
        ]
        return keys or [canonical]
    if method == "table_lookup":
        keys = [
            _resolve_lookup_key(store, str(key))
            for key in (resolution.get("keys") or [])
            if str(key).strip()
        ]
        return keys or [canonical]
    return [canonical]
