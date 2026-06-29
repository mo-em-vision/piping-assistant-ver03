"""Incremental graph DB sync for dev studio writes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.graph.graph_builder import compute_source_fingerprint
from engine.reference.graph_compile import compile_metadata_edges, node_aliases
from engine.reference.graph_db import GraphDatabase
from engine.reference.pack_graph_db import resolve_pack_graph_db


def sync_node_to_graph_db(
    pack_root: Path,
    *,
    node_id: str,
    node_type: str,
    metadata: dict[str, Any],
    body: str,
    source_rel_path: str,
) -> None:
    """Upsert one node and rebuild its outgoing/incoming compiled edges."""
    db_path = resolve_pack_graph_db(pack_root)
    database = GraphDatabase(db_path)
    database.initialize_schema()

    meta = dict(metadata)
    meta.setdefault("id", node_id)
    meta.setdefault("type", node_type)
    aliases = node_aliases(node_id, meta)

    database.delete_edges_for_node(node_id)
    database.upsert_node(
        node_id=node_id,
        node_type=node_type,
        metadata=meta,
        body=body,
        source_rel_path=source_rel_path,
        aliases=aliases or None,
    )

    compiled = compile_metadata_edges(node_id, meta)
    known_ids = set(database.list_node_ids())
    for from_id, to_id, edge_type, edge_meta in compiled:
        if from_id not in known_ids or to_id not in known_ids:
            continue
        database.upsert_edge(
            from_id=from_id,
            to_id=to_id,
            edge_type=edge_type,
            metadata=edge_meta,
        )

    database.set_meta("source_fingerprint", compute_source_fingerprint(pack_root))


def remove_node_from_graph_db(pack_root: Path, node_id: str) -> bool:
    db_path = resolve_pack_graph_db(pack_root)
    database = GraphDatabase(db_path)
    if not database.exists:
        return False
    database.delete_edges_for_node(node_id)
    return database.delete_node(node_id)
