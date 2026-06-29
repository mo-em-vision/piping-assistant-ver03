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
from engine.reference.parameter_metadata import prepare_parameter_metadata
from engine.reference.node_types import normalize_node_metadata
from engine.reference.graph_db import GraphEdgeRecord, GraphNodeRecord
from engine.reference.standards_markdown import split_frontmatter


_NODE_PATTERNS = ("node.yaml", "node.yml", "node.md")


@dataclass
class _DiscoveredSourceNode:
    node_id: str
    node_type: str
    metadata: dict[str, Any]
    body: str
    source_rel_path: str


def compute_source_fingerprint(pack_root: Path) -> str:
    """Fingerprint micro-graph source files under ``nodes/`` for cache invalidation."""
    pack_root = pack_root.resolve()
    nodes_dir = pack_root / "nodes"
    if not nodes_dir.is_dir():
        return hashlib.sha256(b"empty").hexdigest()

    parts: list[str] = []
    seen: set[Path] = set()
    for pattern in _NODE_PATTERNS:
        for path in sorted(nodes_dir.rglob(pattern)):
            if path in seen:
                continue
            seen.add(path)
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
    for pattern in _NODE_PATTERNS:
        for path in sorted(nodes_dir.rglob(pattern)):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            text = path.read_text(encoding="utf-8")
            metadata, body = split_frontmatter(text)
            node_id = str(metadata.get("id") or path.parent.name).strip()
            node_type = str(metadata.get("type") or "node").strip()
            if not node_id or not is_micro_graph_node(metadata, node_type):
                continue
            try:
                source_rel_path = path.parent.relative_to(pack_root).as_posix()
            except ValueError:
                source_rel_path = path.parent.as_posix()
            discovered.append(
                _DiscoveredSourceNode(
                    node_id=node_id,
                    node_type=node_type,
                    metadata=metadata,
                    body=body,
                    source_rel_path=source_rel_path,
                )
            )

    by_id: dict[str, _DiscoveredSourceNode] = {}
    for item in discovered:
        by_id[item.node_id] = item
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
