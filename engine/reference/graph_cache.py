"""Persist :class:`PackGraph` to SQLite as an optional performance cache."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_builder import GraphBuilder, compute_source_fingerprint
from engine.graph.pack_graph import PackGraph
from engine.reference.graph_compile import node_aliases
from engine.reference.graph_db import GraphDatabase, GraphEdgeRecord, GraphNodeRecord
from engine.reference.pack_graph_db import resolve_pack_graph_db

_CACHE_FINGERPRINT_KEY = "source_fingerprint"


def load_cached_graph(pack_root: Path, *, expected_fingerprint: str | None = None) -> PackGraph | None:
    """Load a pack graph from SQLite when the cache matches on-disk sources."""
    pack_root = pack_root.resolve()
    database = GraphDatabase(resolve_pack_graph_db(pack_root))
    if not database.exists:
        return None

    fingerprint = expected_fingerprint or compute_source_fingerprint(pack_root)
    cached_fp = database.get_meta(_CACHE_FINGERPRINT_KEY)
    if cached_fp != fingerprint:
        return None

    graph = database.export_pack_graph(pack_root)
    if not graph.nodes:
        return None
    return graph


def write_graph_cache(pack_root: Path, graph: PackGraph) -> Path:
    """Write a compiled graph to the pack SQLite cache."""
    pack_root = pack_root.resolve()
    db_path = resolve_pack_graph_db(pack_root)
    database = GraphDatabase(db_path)
    database.import_pack_graph(graph)
    database.set_meta(_CACHE_FINGERPRINT_KEY, graph.source_fingerprint)
    return db_path


def build_or_load_graph(pack_root: Path, *, prefer_cache: bool = True) -> PackGraph:
    """Return the pack graph, building from sources when the cache is missing or stale."""
    pack_root = pack_root.resolve()
    fingerprint = compute_source_fingerprint(pack_root)
    if prefer_cache:
        cached = load_cached_graph(pack_root, expected_fingerprint=fingerprint)
        if cached is not None:
            return cached
    graph = GraphBuilder(pack_root).build()
    if prefer_cache and graph.nodes:
        write_graph_cache(pack_root, graph)
    return graph


def invalidate_graph_cache(pack_root: Path) -> None:
    """Drop cached graph content (sources remain authoritative)."""
    pack_root = pack_root.resolve()
    database = GraphDatabase(resolve_pack_graph_db(pack_root))
    if database.exists:
        database.clear_all()
