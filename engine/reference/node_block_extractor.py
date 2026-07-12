"""Extract nested node-owned blocks from primary YAML into flattened metadata.

Authors maintain one primary YAML per node. Nested ``execution``, ``runtime``,
``definition``, and ``resolution`` blocks are promoted to the top-level metadata
shape consumed by graph compilation and execution — without changing consumers.
"""

from __future__ import annotations

from typing import Any

from engine.reference.equation_authoring_policy import (
    EQUATION_DEFINITION_KEYS,
    EQUATION_EXECUTION_KEYS,
)
from engine.reference.paragraph_authoring_policy import (
    EXECUTION_SIDECAR_KEYS,
    NOMENCLATURE_SIDECAR_KEY,
)
from engine.reference.workflow_authoring_policy import WORKFLOW_RUNTIME_KEYS

PARAGRAPH_EXECUTION_KEYS: frozenset[str] = frozenset(EXECUTION_SIDECAR_KEYS)
EQUATION_DEFINITION_KEY_SET: frozenset[str] = EQUATION_DEFINITION_KEYS
EQUATION_EXEC_KEY_SET: frozenset[str] = EQUATION_EXECUTION_KEYS
WORKFLOW_RUNTIME_KEY_SET: frozenset[str] = WORKFLOW_RUNTIME_KEYS


def _promote_block(
    merged: dict[str, Any],
    block_name: str,
    keys: frozenset[str],
) -> None:
    block = merged.pop(block_name, None)
    if not isinstance(block, dict):
        return
    for key in keys:
        if key in block and present_block_value(block, key):
            merged[key] = block[key]


def present_block_value(block: dict[str, Any], key: str) -> bool:
    if key not in block:
        return False
    value = block[key]
    if value is None:
        return False
    if isinstance(value, (list, dict, str)) and not value:
        return False
    return True


def extract_nested_blocks(metadata: dict[str, Any], node_type: str) -> dict[str, Any]:
    """Return a copy with nested authoring blocks promoted to top-level keys."""
    merged = dict(metadata)
    if node_type == "paragraph":
        _promote_block(merged, "execution", PARAGRAPH_EXECUTION_KEYS)
        nomenclature = merged.get(NOMENCLATURE_SIDECAR_KEY)
        if isinstance(nomenclature, dict) and "symbols" in nomenclature:
            merged[NOMENCLATURE_SIDECAR_KEY] = nomenclature["symbols"]
    elif node_type == "equation":
        _promote_block(merged, "definition", EQUATION_DEFINITION_KEY_SET)
        _promote_block(merged, "execution", EQUATION_EXEC_KEY_SET)
    elif node_type == "validation_rule":
        _promote_block(merged, "execution", EQUATION_EXEC_KEY_SET)
    elif node_type == "workflow":
        _promote_block(merged, "runtime", WORKFLOW_RUNTIME_KEY_SET)
    elif node_type == "parameter":
        _promote_block(merged, "resolution", frozenset({"method", "lookup", "table_id", "keys"}))
    elif node_type == "lookup":
        _promote_block(merged, "source", frozenset({"table_id", "storage", "path", "format"}))
    return merged


def extract_and_flatten_node_metadata(
    metadata: dict[str, Any],
    node_type: str,
) -> dict[str, Any]:
    """Normalize nested blocks for compile-time consumers."""
    return extract_nested_blocks(metadata, node_type)
