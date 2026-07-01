"""Canonical micro-graph node types and legacy normalization."""

from __future__ import annotations

from typing import Any

CANONICAL_NODE_TYPES = frozenset(
    {
        "workflow",
        "paragraph",
        "equation",
        "parameter",
        "quantity",
        "designation",
        "text",
        "unit",
        "dimension",
    }
)
RUNTIME_NODE_FIELDS = frozenset({"value", "user_input", "runtime_unit", "runtime_units"})

# Legacy on-disk types → (canonical type, kind metadata value)
_LEGACY_TYPE_KIND: dict[str, tuple[str, str]] = {
    "assumption": ("parameter", "assumption"),
    "interaction": ("parameter", "interaction"),
    "lookup": ("equation", "lookup"),
    "table": ("text", "table"),
    "standard_section": ("paragraph", "section"),
    "definition": ("paragraph", "definition"),
    "calculation": ("paragraph", "calculation"),
    "requirement": ("paragraph", "requirement"),
}

# Accept canonical types and legacy aliases when discovering sources.
MICRO_GRAPH_TYPES = CANONICAL_NODE_TYPES | frozenset(_LEGACY_TYPE_KIND.keys())


def normalize_node_metadata(
    metadata: dict[str, Any],
    node_type: str,
) -> tuple[str, dict[str, Any]]:
    """Return canonical type and metadata (sets ``kind`` for legacy types)."""
    meta = dict(metadata)
    explicit_kind = meta.get("kind")
    if node_type in CANONICAL_NODE_TYPES:
        if node_type in {"quantity", "designation"}:
            for field in RUNTIME_NODE_FIELDS:
                meta.pop(field, None)
        if node_type == "paragraph" and explicit_kind is None:
            meta.setdefault("kind", "section")
        if explicit_kind is not None:
            meta["kind"] = str(explicit_kind)
        return node_type, meta

    if node_type == "text" and explicit_kind == "section":
        meta.setdefault("kind", "section")
        meta["type"] = "paragraph"
        return "paragraph", meta

    mapping = _LEGACY_TYPE_KIND.get(node_type)
    if mapping is None:
        return node_type, meta

    canonical, kind = mapping
    meta.setdefault("kind", kind)
    if kind in {"assumption", "interaction"}:
        if meta.get("field") and not meta.get("input_id"):
            meta["input_id"] = meta["field"]
        if kind == "assumption":
            meta.setdefault("required", True)
    meta["type"] = canonical
    return canonical, meta


def node_kind(metadata: dict[str, Any]) -> str | None:
    kind = metadata.get("kind")
    if kind is not None:
        return str(kind)
    legacy = str(metadata.get("type", ""))
    mapped = _LEGACY_TYPE_KIND.get(legacy)
    return mapped[1] if mapped else None


def canonical_type(metadata: dict[str, Any], node_type: str | None = None) -> str:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    normalized, _ = normalize_node_metadata(metadata, raw)
    return normalized


def is_micro_graph_node(metadata: dict[str, Any], node_type: str) -> bool:
    if node_type in MICRO_GRAPH_TYPES:
        return True
    normalized, _ = normalize_node_metadata(metadata, node_type)
    return normalized in CANONICAL_NODE_TYPES


def parameter_input_id(metadata: dict[str, Any]) -> str:
    return str(metadata.get("input_id") or metadata.get("field") or "").strip()


def is_ui_parameter(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    """Parameter that collects user decisions (assumption or interaction)."""
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    ctype, meta = normalize_node_metadata(metadata, raw)
    if ctype != "parameter":
        return False
    return node_kind(meta) in {"assumption", "interaction"}


def is_section_node(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    if raw == "standard_section":
        return True
    ctype, meta = normalize_node_metadata(metadata, raw)
    return ctype == "paragraph" and node_kind(meta) in {"section", "definition", "calculation"}


def is_lookup_node(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    if raw == "lookup":
        return True
    ctype, meta = normalize_node_metadata(metadata, raw)
    return ctype == "equation" and node_kind(meta) == "lookup"


def is_table_node(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    if raw == "table":
        return True
    ctype, meta = normalize_node_metadata(metadata, raw)
    return ctype == "text" and node_kind(meta) == "table"


def is_quantity_node(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    return canonical_type(metadata, raw) == "quantity"


def is_designation_node(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    return canonical_type(metadata, raw) == "designation"


def expansion_priority_order(node_type: str, metadata: dict[str, Any]) -> int:
    """Lower sorts earlier during lazy expansion."""
    ctype, meta = normalize_node_metadata(metadata, node_type)
    kind = node_kind(meta)
    if ctype == "workflow":
        return 0
    if ctype == "parameter" and kind == "assumption":
        return 1
    if ctype == "parameter" and kind == "interaction":
        return 2
    if ctype == "parameter":
        return 3
    if ctype == "quantity":
        return 4
    if ctype == "designation":
        return 5
    if ctype == "equation" and kind == "lookup":
        return 6
    if ctype == "equation":
        return 7
    if ctype == "paragraph":
        return 8
    if ctype == "text":
        return 8
    if ctype == "unit":
        return 9
    if ctype == "dimension":
        return 10
    return 50
