"""Read and write micro-graph node YAML sources."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from engine.reference.node_types import node_kind
from engine.reference.graph_compile import is_micro_graph_node
from engine.reference.standards_markdown import compose_frontmatter, split_frontmatter
from engine.reference.node_sources import iter_node_source_paths, source_rel_path
from engine.reference.standards_paths import list_standard_packs, resolve_standard_pack

_DEFAULT_TYPE_PATHS: dict[str, str] = {
    "workflow": "nodes/workflows",
    "paragraph": "nodes/paragraph",
    "parameter": "nodes/parameters",
    "text": "nodes/text",
    "equation": "nodes/equations",
    "lookup": "nodes/tables",
}

_KIND_PATHS: dict[str, str] = {
    "assumption": "assumptions",
    "interaction": "interactions",
    "table": "tables",
    "lookup": "lookups",
    "section": "sections",
}


@dataclass
class StoredNode:
    node_id: str
    node_type: str
    metadata: dict[str, Any]
    body: str
    source_rel_path: str
    source_file: Path


class NodeRepository:
    def __init__(self, standards_root: Path) -> None:
        self.standards_root = standards_root.resolve()

    def list_packs(self) -> list[dict[str, Any]]:
        packs: list[dict[str, Any]] = []
        for slug, pack_root in list_standard_packs(self.standards_root):
            nodes = self.discover_nodes(pack_root)
            packs.append(
                {
                    "slug": slug,
                    "path": str(pack_root),
                    "node_count": len(nodes),
                }
            )
        return packs

    def pack_root(self, pack: str) -> Path:
        return resolve_standard_pack(self.standards_root, pack)

    def discover_nodes(self, pack_root: Path) -> list[StoredNode]:
        nodes_dir = pack_root / "nodes"
        if not nodes_dir.is_dir():
            return []
        discovered: list[StoredNode] = []
        seen_ids: set[str] = set()
        seen_paths: set[Path] = set()
        for path in iter_node_source_paths(nodes_dir):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            stored = self._load_file(pack_root, path)
                if stored is None or stored.node_id in seen_ids:
                    continue
                seen_ids.add(stored.node_id)
                discovered.append(stored)
        return sorted(discovered, key=lambda item: item.node_id)

    def get_node(self, pack: str, node_id: str) -> StoredNode | None:
        for item in self.discover_nodes(self.pack_root(pack)):
            if item.node_id == node_id:
                return item
        return None

    def write_node(
        self,
        pack: str,
        *,
        metadata: dict[str, Any],
        body: str,
        source_rel_path: str | None = None,
    ) -> StoredNode:
        pack_root = self.pack_root(pack)
        node_id = str(metadata.get("id", "")).strip()
        node_type = str(metadata.get("type", "")).strip()
        if not node_id or not node_type:
            raise ValueError("metadata must include id and type")
        if not is_micro_graph_node(metadata, node_type):
            raise ValueError(f"Unsupported node type: {node_type}")

        rel_path = source_rel_path or self._default_rel_path(node_id, node_type, metadata)
        file_path = pack_root / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(compose_frontmatter(metadata, body), encoding="utf-8")
        return StoredNode(
            node_id=node_id,
            node_type=node_type,
            metadata=dict(metadata),
            body=body,
            source_rel_path=rel_path.replace("\\", "/"),
            source_file=file_path,
        )

    def delete_node(self, pack: str, node_id: str) -> bool:
        stored = self.get_node(pack, node_id)
        if stored is None:
            return False
        if stored.source_file.is_file():
            stored.source_file.unlink()
        parent = stored.source_file.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
        return True

    def duplicate_node(
        self,
        pack: str,
        node_id: str,
        *,
        new_id: str,
        source_rel_path: str | None = None,
    ) -> StoredNode:
        source = self.get_node(pack, node_id)
        if source is None:
            raise FileNotFoundError(f"Node not found: {node_id}")
        metadata = dict(source.metadata)
        metadata["id"] = new_id
        if metadata.get("title"):
            metadata["title"] = f"{metadata['title']} (copy)"
        rel = source_rel_path or self._default_rel_path(new_id, source.node_type, metadata)
        return self.write_node(pack, metadata=metadata, body=source.body, source_rel_path=rel)

    def rename_node_id(
        self,
        pack: str,
        old_id: str,
        new_id: str,
        *,
        force: bool = False,
        find_references: Callable[[str], list[str]] | None = None,
    ) -> StoredNode:
        stored = self.get_node(pack, old_id)
        if stored is None:
            raise FileNotFoundError(f"Node not found: {old_id}")
        if find_references and not force:
            refs = find_references(old_id)
            if refs:
                raise ValueError(f"Node is referenced by: {', '.join(refs)}")
        metadata = dict(stored.metadata)
        metadata["id"] = new_id
        rel_parts = stored.source_rel_path.split("/")
        rel_parts[-1] = new_id.split("-")[-1] if rel_parts else new_id
        new_rel = "/".join(rel_parts)
        new_stored = self.write_node(
            pack,
            metadata=metadata,
            body=stored.body,
            source_rel_path=new_rel,
        )
        self.delete_node(pack, old_id)
        return new_stored

    def _default_rel_path(self, node_id: str, node_type: str, metadata: dict[str, Any] | None = None) -> str:
        meta = metadata or {}
        kind = node_kind(meta)
        folder = _DEFAULT_TYPE_PATHS.get(node_type)
        if folder is None and kind:
            folder = _KIND_PATHS.get(kind)
        if folder is None:
            folder = f"nodes/{node_type}s" if node_type else "nodes"
        return f"{folder}/{node_id}.yaml"

    def _load_file(self, pack_root: Path, path: Path) -> StoredNode | None:
        text = path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        node_id = str(metadata.get("id") or path.stem).strip()
        node_type = str(metadata.get("type") or "node").strip()
        if not node_id or not is_micro_graph_node(metadata, node_type):
            return None
        rel = source_rel_path(pack_root, path)
        return StoredNode(
            node_id=node_id,
            node_type=node_type,
            metadata=metadata,
            body=body,
            source_rel_path=rel,
            source_file=path,
        )
