"""Build PackGraph objects from on-disk Markdown/YAML micro-node sources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.graph.pack_graph import PackGraph
from engine.reference.graph_compile import (
    compile_metadata_edges,
    is_micro_graph_node,
    node_aliases,
)
from engine.reference.embedded_nodes import iter_embedded_node_sources
from engine.reference.parameter_metadata import prepare_parameter_metadata
from engine.reference.node_types import normalize_node_metadata
from engine.reference.graph_db import GraphEdgeRecord, GraphNodeRecord
from engine.reference.node_sources import iter_node_source_paths, source_rel_path
from engine.reference.nomenclature_parameters import iter_nomenclature_parameters
from engine.reference.standards_markdown import merge_dual_node_frontmatter, split_frontmatter


@dataclass
class _DiscoveredSourceNode:
    node_id: str
    node_type: str
    metadata: dict[str, Any]
    body: str
    source_rel_path: str
    source_path: Path


def compute_source_fingerprint(pack_root: Path) -> str:
    """Fingerprint micro-graph source files under ``nodes/`` for cache invalidation."""
    pack_root = pack_root.resolve()
    nodes_dir = pack_root / "nodes"
    if not nodes_dir.is_dir():
        return hashlib.sha256(b"empty").hexdigest()

    parts: list[str] = []
    for path in iter_node_source_paths(nodes_dir):
        stat = path.stat()
        rel = path.relative_to(pack_root).as_posix()
        parts.append(f"{rel}:{stat.st_mtime_ns}:{stat.st_size}")

    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def discover_micro_graph_sources(pack_root: Path) -> list[_DiscoveredSourceNode]:
    """Scan ``pack_root/nodes`` for micro-graph node sources."""
    pack_root = pack_root.resolve()
    nodes_dir = pack_root / "nodes"
    discovered: list[_DiscoveredSourceNode] = []
    if not nodes_dir.is_dir():
        return discovered

    seen_paths: set[Path] = set()
    for path in iter_node_source_paths(nodes_dir):
        if path in seen_paths:
            continue
        seen_paths.add(path)
        text = path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        node_id = str(metadata.get("id") or path.stem).strip()
        node_type = str(metadata.get("type") or "node").strip()
        if not node_id or not is_micro_graph_node(metadata, node_type):
            continue
        discovered.append(
            _DiscoveredSourceNode(
                node_id=node_id,
                node_type=node_type,
                metadata=metadata,
                body=body,
                source_rel_path=source_rel_path(pack_root, path),
                source_path=path,
            )
        )

    by_id: dict[str, _DiscoveredSourceNode] = {}
    for item in discovered:
        existing = by_id.get(item.node_id)
        if existing is None:
            by_id[item.node_id] = item
            continue
        existing_prefers_yaml = existing.source_path.suffix.lower() in {".yaml", ".yml"}
        incoming_prefers_yaml = item.source_path.suffix.lower() in {".yaml", ".yml"}
        if existing_prefers_yaml and not incoming_prefers_yaml:
            continue
        if incoming_prefers_yaml and not existing_prefers_yaml:
            by_id[item.node_id] = item
            continue
        by_id[item.node_id] = item

    merged_by_id: dict[str, _DiscoveredSourceNode] = {}
    for item in by_id.values():
        metadata, body = merge_dual_node_frontmatter(
            item.source_path.parent,
            item.metadata,
            item.body,
            primary_path=item.source_path,
        )
        merged_by_id[item.node_id] = _DiscoveredSourceNode(
            node_id=item.node_id,
            node_type=item.node_type,
            metadata=metadata,
            body=body,
            source_rel_path=item.source_rel_path,
            source_path=item.source_path,
        )
    by_id = merged_by_id

    for item in list(by_id.values()):
        text = item.source_path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        for embedded in iter_embedded_node_sources(
            parent_id=item.node_id,
            parent_source_rel_path=item.source_rel_path,
            metadata=metadata,
        ):
            if not is_micro_graph_node(embedded.metadata, embedded.node_type):
                continue
            existing = by_id.get(embedded.node_id)
            if existing is not None and existing.source_path != item.source_path:
                if existing.source_path.parent.name == embedded.node_id:
                    continue
            by_id[embedded.node_id] = _DiscoveredSourceNode(
                node_id=embedded.node_id,
                node_type=embedded.node_type,
                metadata=embedded.metadata,
                body=embedded.body,
                source_rel_path=embedded.source_rel_path,
                source_path=item.source_path,
            )
    # Virtual parameter nodes from nomenclature on paragraph/workflow sources.
    for item in list(by_id.values()):
        node_type, meta = normalize_node_metadata(dict(item.metadata), item.node_type)
        if node_type not in {"paragraph", "workflow"}:
            continue
        for param_id, param_meta in iter_nomenclature_parameters(item.node_id, meta):
            if param_id in by_id:
                continue
            by_id[param_id] = _DiscoveredSourceNode(
                node_id=param_id,
                node_type="parameter",
                metadata=param_meta,
                body="",
                source_rel_path=item.source_rel_path,
                source_path=item.source_path,
            )
    return list(by_id.values())


class GraphBuilder:
    """Compile micro-graph sources on disk into a :class:`PackGraph`."""

    def __init__(self, pack_root: Path) -> None:
        self.pack_root = pack_root.resolve()

    def build(self) -> PackGraph:
        fingerprint = compute_source_fingerprint(self.pack_root)
        sources = discover_micro_graph_sources(self.pack_root)
        nodes: dict[str, GraphNodeRecord] = {}
        aliases: dict[str, str] = {}
        compiled_edges: list[tuple[str, str, str, dict[str, Any] | None]] = []

        for source in sources:
            metadata = dict(source.metadata)
            metadata.setdefault("id", source.node_id)
            node_type, metadata = normalize_node_metadata(metadata, source.node_type)
            metadata.setdefault("type", node_type)
            if node_type == "parameter":
                metadata = prepare_parameter_metadata(metadata)
            nodes[source.node_id] = GraphNodeRecord(
                node_id=source.node_id,
                node_type=node_type,
                metadata=metadata,
                body=source.body,
                source_rel_path=source.source_rel_path,
            )
            for alias in node_aliases(source.node_id, metadata):
                aliases[alias] = source.node_id
            compiled_edges.extend(compile_metadata_edges(source.node_id, metadata))

        node_ids = set(nodes.keys())
        edges: list[GraphEdgeRecord] = []
        for from_id, to_id, edge_type, edge_meta in compiled_edges:
            if from_id not in node_ids or to_id not in node_ids:
                continue
            edges.append(
                GraphEdgeRecord(
                    from_id=from_id,
                    to_id=to_id,
                    edge_type=edge_type,
                    metadata=edge_meta or {},
                )
            )

        return PackGraph(
            pack_root=str(self.pack_root),
            source_fingerprint=fingerprint,
            nodes=nodes,
            edges=edges,
            aliases=aliases,
        )
