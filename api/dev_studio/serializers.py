"""Node type schemas and API serializers for dev studio."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import EDGE_LIST_KEYS, MICRO_GRAPH_TYPES
from engine.reference.graph_db import GraphEdgeRecord, GraphNodeRecord
from engine.reference.node_types import CANONICAL_NODE_TYPES

_PARAMETER_KINDS = ("assumption", "interaction", "value")

_DOCS_FIELDS = [
    "documentation",
    "title",
    "summary",
    "description",
    "before_enter",
    "after_exit",
    "instructions",
    "warnings",
    "tips",
    "references",
    "report_summary",
]

NODE_TYPE_SCHEMAS: dict[str, dict[str, Any]] = {
    "workflow": {
        "sections": {
            "general": ["id", "type", "title", "slug", "status", "version", "engineering_intent", "purpose"],
            "docs": _DOCS_FIELDS,
            "navigation": ["navigation"],
            "graph": ["anchors_to", "goal_output", "contains", "requires", "edges"],
        },
        "required": ["id", "type", "title", "anchors_to", "goal_output"],
    },
    "text": {
        "sections": {
            "general": ["id", "type", "kind", "title", "role", "display_order", "paragraph", "section", "topic"],
            "docs": _DOCS_FIELDS,
            "ui": ["role", "display_order"],
            "graph": ["contains", "defines", "edges"],
            "reference": ["table_id", "standard", "lookup_keys"],
        },
        "required": ["id", "type"],
        "kinds": ["section", "table", "content"],
    },
    "equation": {
        "sections": {
            "general": ["id", "type", "kind", "title", "equation_id", "execution_phase"],
            "docs": _DOCS_FIELDS,
            "calculation": ["sympy", "display_latex", "table_id", "output_param", "interpolation"],
            "graph": ["requires", "calculates", "explains", "keys", "uses_table", "outputs", "edges"],
        },
        "required": ["id", "type"],
        "kinds": ["calculation", "lookup"],
    },
    "parameter": {
        "sections": {
            "general": ["id", "type", "kind", "title", "symbol", "input_id", "description", "display"],
            "docs": _DOCS_FIELDS,
            "engineering": ["canonical_unit", "unit", "allowed_units", "allowed_values", "required_for_expansion"],
            "ui": ["question", "mode", "options", "requires_confirmation", "expansion_block_message"],
            "calculation": ["resolution"],
            "metadata": ["defined_in", "concept_id", "references", "located_in", "blocks_expansion_on"],
            "graph": ["edges", "next_step"],
        },
        "required": ["id", "type", "input_id"],
        "kinds": list(_PARAMETER_KINDS),
    },
    "unit": {
        "sections": {
            "general": ["id", "type", "symbol", "dimension", "description", "aliases", "display"],
            "graph": ["converts_to", "edges"],
        },
        "required": ["id", "type", "symbol", "dimension"],
    },
}

GRAPH_EDGE_FIELDS = list(EDGE_LIST_KEYS) + ["edges", "anchors_to"]


def node_summary(record: GraphNodeRecord) -> dict[str, Any]:
    meta = record.metadata
    return {
        "id": record.node_id,
        "type": record.node_type,
        "kind": meta.get("kind"),
        "title": str(meta.get("title") or meta.get("name") or record.node_id),
        "description": str(meta.get("description") or ""),
        "source_rel_path": record.source_rel_path,
        "unit": str(meta.get("unit") or ""),
        "canonical_unit": str(meta.get("canonical_unit") or ""),
        "display": meta.get("display") if isinstance(meta.get("display"), dict) else {},
        "category": str(meta.get("topic") or meta.get("section") or ""),
        "tags": meta.get("tags") if isinstance(meta.get("tags"), list) else [],
    }


def list_node_type_schemas() -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []
    for node_type in sorted(CANONICAL_NODE_TYPES):
        schema = NODE_TYPE_SCHEMAS.get(node_type, {})
        schemas.append(
            {
                "type": node_type,
                "sections": schema.get("sections", {}),
                "required": schema.get("required", []),
                "kinds": schema.get("kinds", []),
            }
        )
    return schemas


def list_legacy_node_types() -> list[str]:
    return sorted(MICRO_GRAPH_TYPES - CANONICAL_NODE_TYPES)


def _edge_summary(edge: GraphEdgeRecord) -> dict[str, Any]:
    return {
        "from": edge.from_id,
        "to": edge.to_id,
        "type": edge.edge_type,
        "metadata": edge.metadata or {},
    }


def node_detail(
    record: GraphNodeRecord,
    *,
    pack: str,
    incoming: list[GraphEdgeRecord],
    outgoing: list[GraphEdgeRecord],
) -> dict[str, Any]:
    meta = record.metadata
    return {
        "pack": pack,
        "id": record.node_id,
        "type": record.node_type,
        "kind": meta.get("kind"),
        "metadata": meta,
        "body": record.body,
        "source_rel_path": record.source_rel_path,
        "incoming": [_edge_summary(edge) for edge in incoming],
        "outgoing": [_edge_summary(edge) for edge in outgoing],
        "graph_fields": GRAPH_EDGE_FIELDS,
    }


def list_node_types() -> dict[str, Any]:
    return {
        "types": list_node_type_schemas(),
        "legacy_types": list_legacy_node_types(),
        "edge_fields": GRAPH_EDGE_FIELDS,
    }


def relationships_payload(
    node_id: str,
    *,
    incoming: list[GraphEdgeRecord],
    outgoing: list[GraphEdgeRecord],
    connected: dict[str, list[str]],
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "incoming": [_edge_summary(edge) for edge in incoming],
        "outgoing": [_edge_summary(edge) for edge in outgoing],
        "connected": connected,
    }
