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
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_nodes import StandardsNodesDatabase
from engine.reference.standards_paths import list_standard_packs

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


def _path_depth_score(source_rel_path: str) -> int:
    parts = [part for part in source_rel_path.replace("\\", "/").split("/") if part]
    score = len(parts)
    if any(part in {"302", "304", "appendix_A"} for part in parts):
        score += 10
    return score


def _discover_nodes(pack_root: Path) -> list[_DiscoveredNode]:
    nodes_dir = pack_root / "nodes"
    discovered: list[_DiscoveredNode] = []

    if nodes_dir.is_dir():
        for path in sorted(nodes_dir.rglob("node.md")):
            text = path.read_text(encoding="utf-8")
            metadata, body = split_frontmatter(text)
            node_id = str(metadata.get("id") or path.parent.name).strip()
            if not node_id:
                continue
            try:
                source_rel_path = path.parent.relative_to(pack_root).as_posix()
            except ValueError:
                continue
            discovered.append(
                _DiscoveredNode(
                    node_id=node_id,
                    kind="node",
                    metadata=metadata,
                    body=body,
                    source_rel_path=source_rel_path,
                    source_path=path,
                    depth_score=_path_depth_score(source_rel_path),
                )
            )

    by_id: dict[str, _DiscoveredNode] = {}
    for item in discovered:
        existing = by_id.get(item.node_id)
        if existing is None or item.depth_score > existing.depth_score:
            by_id[item.node_id] = item
    return list(by_id.values())


def _collect_assets(node_dir: Path, node_id: str) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for folder_name, asset_type in _ASSET_DIRS.items():
        asset_dir = node_dir / folder_name
        if not asset_dir.is_dir():
            continue
        for path in sorted(asset_dir.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix == ".py":
                continue
            if suffix not in {".md", ".yaml", ".yml", ".txt"}:
                continue
            relative_path = f"{folder_name}/{path.name}"
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            metadata, body = split_frontmatter(text)
            asset_id = str(metadata.get("id") or path.stem)
            assets.append(
                {
                    "node_id": node_id,
                    "asset_type": asset_type,
                    "asset_id": asset_id,
                    "relative_path": relative_path,
                    "metadata": metadata,
                    "body": body,
                }
            )
    return assets


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


def _remove_flat_duplicates(pack_root: Path, kept: list[_DiscoveredNode]) -> None:
    nodes_dir = pack_root / "nodes"
    if not nodes_dir.is_dir():
        return
    kept_dirs = {item.source_path.parent.resolve() for item in kept}
    kept_ids = {item.node_id for item in kept}
    for item in kept:
        flat_candidate = nodes_dir / item.node_id
        if flat_candidate.is_dir() and flat_candidate.resolve() not in kept_dirs:
            shutil.rmtree(flat_candidate, ignore_errors=True)
    for path in list(nodes_dir.iterdir()):
        if not path.is_dir() or path.resolve() in kept_dirs:
            continue
        node_md = path / "node.md"
        if not node_md.is_file():
            continue
        metadata, _ = split_frontmatter(node_md.read_text(encoding="utf-8"))
        node_id = str(metadata.get("id") or path.name).strip()
        if node_id in kept_ids:
            shutil.rmtree(path, ignore_errors=True)


def build_pack(pack_root: Path) -> Path | None:
    discovered = _discover_nodes(pack_root)
    if not discovered:
        return None

    _remove_flat_duplicates(pack_root, discovered)
    db_path = resolve_pack_nodes_db(pack_root)
    database = StandardsNodesDatabase(db_path)
    database.clear_all()

    for item in discovered:
        aliases = [
            f"nodes/{item.source_path.parent.name}",
            item.source_rel_path,
        ]
        database.upsert_node(
            node_id=item.node_id,
            kind=item.kind,
            metadata=item.metadata,
            body=item.body,
            source_rel_path=item.source_rel_path,
            aliases=aliases,
        )
        for asset in _collect_assets(item.source_path.parent, item.node_id):
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
    root = (standards_root or (_ROOT / "standards")).resolve()
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
