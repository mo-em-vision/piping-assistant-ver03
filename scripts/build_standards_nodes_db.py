#!/usr/bin/env python3
"""Compile standards node and root markdown sources into per-pack SQLite databases."""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.pack_nodes_db import resolve_pack_nodes_db
from engine.reference.embedded_nodes import iter_embedded_node_sources
from engine.reference.standards_markdown import merge_dual_node_frontmatter, split_frontmatter
from engine.reference.standards_nodes import StandardsNodesDatabase
from engine.reference.standards_paths import list_standard_packs
from engine.reference.node_sources import iter_node_source_paths, source_rel_path

_ASSET_DIRS = {
    "equations": "equation",
    "conditions": "condition",
    "notes": "note",
    "references": "reference",
}


@dataclass
class _DiscoveredNode:
    node_id: str
    kind: str
    metadata: dict[str, Any]
    body: str
    source_rel_path: str
    source_path: Path
    depth_score: int
    aliases: tuple[str, ...] = ()


def _path_depth_score(source_rel_path: str) -> int:
    parts = [part for part in source_rel_path.replace("\\", "/").split("/") if part]
    return -len(parts)


def _discover_nodes(pack_root: Path) -> list[_DiscoveredNode]:
    nodes_dir = pack_root / "nodes"
    discovered: list[_DiscoveredNode] = []

    if nodes_dir.is_dir():
        seen_paths: set[Path] = set()
        for path in iter_node_source_paths(nodes_dir):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            text = path.read_text(encoding="utf-8")
            metadata, body = split_frontmatter(text)
            node_id = str(metadata.get("id") or path.stem).strip()
            if not node_id:
                continue
            rel = source_rel_path(pack_root, path)
            discovered.append(
                _DiscoveredNode(
                    node_id=node_id,
                    kind="node",
                    metadata=metadata,
                    body=body,
                    source_rel_path=rel,
                    source_path=path,
                    depth_score=_path_depth_score(rel),
                )
            )

    by_id: dict[str, _DiscoveredNode] = {}
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
        if item.depth_score > existing.depth_score:
            by_id[item.node_id] = item

    merged_by_id: dict[str, _DiscoveredNode] = {}
    for item in by_id.values():
        metadata, body = merge_dual_node_frontmatter(
            item.source_path.parent,
            item.metadata,
            item.body,
            primary_path=item.source_path,
        )
        merged_by_id[item.node_id] = _DiscoveredNode(
            node_id=item.node_id,
            kind=item.kind,
            metadata=metadata,
            body=body,
            source_rel_path=item.source_rel_path,
            source_path=item.source_path,
            depth_score=item.depth_score,
            aliases=item.aliases,
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
            existing = by_id.get(embedded.node_id)
            if existing is not None:
                if existing.source_path.parent.name == embedded.node_id:
                    continue
                if existing.source_path.stem == embedded.node_id:
                    continue
            by_id[embedded.node_id] = _DiscoveredNode(
                node_id=embedded.node_id,
                kind="node",
                metadata=embedded.metadata,
                body=embedded.body,
                source_rel_path=embedded.source_rel_path,
                source_path=item.source_path,
                depth_score=item.depth_score + 1,
                aliases=embedded.aliases,
            )
    return list(by_id.values())


def _collect_embedded_assets(item: _DiscoveredNode) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for embedded in iter_embedded_node_sources(
        parent_id=item.node_id,
        parent_source_rel_path=item.source_rel_path,
        metadata=item.metadata,
    ):
        for alias in embedded.aliases:
            normalized = alias.replace("\\", "/").lstrip("/")
            if not normalized.startswith(("equations/", "conditions/", "notes/", "references/")):
                continue
            key = (item.node_id, normalized)
            if key in seen:
                continue
            seen.add(key)
            folder = normalized.split("/", 1)[0]
            asset_type = _ASSET_DIRS.get(folder, "text")
            metadata = dict(embedded.metadata)
            metadata.pop("source", None)
            body = embedded.body
            asset_id = str(metadata.get("id") or metadata.get("equation_id") or Path(normalized).stem)
            assets.append(
                {
                    "node_id": item.node_id,
                    "asset_type": asset_type,
                    "asset_id": asset_id,
                    "relative_path": normalized,
                    "metadata": metadata,
                    "body": body,
                }
            )
    return assets


def _collect_assets(node_dir: Path, node_id: str) -> list[dict[str, Any]]:
    del node_dir, node_id
    return []


def _parse_index_md(pack_root: Path) -> list[dict[str, Any]]:
    index_path = pack_root / "index.md"
    if not index_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    current_section: str | None = None
    sort_order = 0
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current_section = line.removeprefix("## ").strip()
            continue
        if not line.startswith("|") or line.startswith("|--") or "Node ID" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        node_id = cells[0] if cells[0] and not cells[0].startswith("`") else None
        if node_id and (node_id.startswith("B313-") or node_id.startswith("ASTM-")):
            description = cells[-1] if len(cells) > 1 else None
            rows.append(
                {
                    "section": current_section,
                    "node_id": node_id,
                    "description": description,
                    "sort_order": sort_order,
                }
            )
            sort_order += 1
    return rows


_LEGACY_DUPLICATE_PREFIXES = ("302/", "304/", "parameters/", "appendix_A/", "workflows/")


def _remove_flat_duplicates(pack_root: Path, kept: list[_DiscoveredNode]) -> None:
    nodes_dir = pack_root / "nodes"
    if not nodes_dir.is_dir():
        return
    kept_by_id = {item.node_id: item for item in kept}
    seen_dirs: set[Path] = set()
    for pattern in ("node.md", "node.yaml", "node.yml"):
        for path in sorted(nodes_dir.rglob(pattern)):
            parent = path.parent.resolve()
            if parent in seen_dirs:
                continue
            seen_dirs.add(parent)
            text = path.read_text(encoding="utf-8")
            metadata, _ = split_frontmatter(text)
            node_id = str(metadata.get("id") or parent.name).strip()
            if node_id not in kept_by_id:
                continue
            canonical = kept_by_id[node_id].source_path.parent.resolve()
            if parent == canonical:
                continue
            if not canonical.name.startswith("B313-"):
                continue
            try:
                relative = parent.relative_to(nodes_dir).as_posix()
            except ValueError:
                continue
            if not relative.startswith(_LEGACY_DUPLICATE_PREFIXES):
                continue
            shutil.rmtree(parent, ignore_errors=True)


def build_pack(pack_root: Path) -> Path | None:
    discovered = _discover_nodes(pack_root)
    if not discovered:
        return None

    _remove_flat_duplicates(pack_root, discovered)
    db_path = resolve_pack_nodes_db(pack_root)
    database = StandardsNodesDatabase(db_path)
    database.clear_all()

    for item in discovered:
        aliases = list(item.aliases)
        if item.source_path.parent.name == item.node_id:
            aliases = [f"nodes/{item.node_id}", item.source_rel_path, *aliases]
        database.upsert_node(
            node_id=item.node_id,
            kind=item.kind,
            metadata=item.metadata,
            body=item.body,
            source_rel_path=item.source_rel_path,
            aliases=aliases,
        )
        for asset in _collect_embedded_assets(item):
            database.upsert_asset(
                node_id=asset["node_id"],
                asset_type=asset["asset_type"],
                asset_id=asset["asset_id"],
                relative_path=asset["relative_path"],
                metadata=asset["metadata"],
                body=asset["body"],
            )

    for row in _parse_index_md(pack_root):
        database.upsert_pack_index_row(
            section=row.get("section"),
            node_id=row.get("node_id"),
            description=row.get("description"),
            sort_order=int(row.get("sort_order", 0)),
        )

    return db_path


def build_all(*, standards_root: Path | None = None) -> list[Path]:
    root = (standards_root or (_ROOT / "knowledge" / "standards")).resolve()
    built: list[Path] = []
    for slug, pack_root in list_standard_packs(root):
        db_path = build_pack(pack_root)
        if db_path is None:
            continue
        count = len(StandardsNodesDatabase(db_path).list_node_ids())
        print(f"Built {db_path} ({slug}, {count} nodes/roots)")
        built.append(db_path)
    return built


if __name__ == "__main__":
    paths = build_all()
    print(f"Built {len(paths)} pack node databases")
