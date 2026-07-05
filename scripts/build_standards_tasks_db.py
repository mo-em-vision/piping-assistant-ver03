#!/usr/bin/env python3
"""Compile workflow YAML nodes from repo-root ``workflows/`` into workflows.db."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.knowledge_paths import workflows_root
from engine.reference.pack_metadata import load_pack_metadata
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_paths import (
    list_standard_packs,
    resolve_global_tasks_db,
    workflow_source_rel_path,
)
from engine.reference.standards_tasks_db import StandardsTasksDatabase


def _authority_slug_map(standards_root: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for slug, pack_root in list_standard_packs(standards_root):
        authority = str(load_pack_metadata(pack_root).get("authority") or "").strip()
        if authority:
            mapping[authority] = slug
    return mapping


def _primary_standard_slug(metadata: dict[str, Any], authority_slugs: dict[str, str]) -> str:
    for authority in metadata.get("expected_authorities") or []:
        slug = authority_slugs.get(str(authority).strip())
        if slug:
            return slug
    return ""


def _discover_workflows(standards_root: Path) -> list[dict[str, Any]]:
    workflows_dir = workflows_root()
    if not workflows_dir.is_dir():
        return []

    authority_slugs = _authority_slug_map(standards_root)
    discovered: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in sorted(workflows_dir.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        if str(metadata.get("type") or "") != "workflow":
            continue
        node_id = str(metadata.get("id") or path.stem).strip()
        if not node_id or node_id in seen_ids:
            continue
        seen_ids.add(node_id)
        source_rel_path = workflow_source_rel_path(path)
        task_slug = str(metadata.get("slug") or metadata.get("key") or path.stem).strip()
        standard_slug = _primary_standard_slug(metadata, authority_slugs)
        discovered.append(
            {
                "node_id": node_id,
                "metadata": metadata,
                "body": body,
                "source_rel_path": source_rel_path,
                "standard_slug": standard_slug,
                "task_slug": task_slug,
                "source_path": path,
            }
        )
    return discovered


def build_all(*, standards_root: Path | None = None) -> Path | None:
    root = (standards_root or (_ROOT / "knowledge" / "standards")).resolve()
    discovered = _discover_workflows(root)
    if not discovered:
        return None

    db_path = resolve_global_tasks_db(root)
    database = StandardsTasksDatabase(db_path)
    database.clear_all()

    for item in discovered:
        standard_slug = str(item["standard_slug"])
        task_slug = str(item["task_slug"])
        rel = str(item["source_rel_path"])
        filename = Path(item["source_path"]).name
        aliases = [
            task_slug,
            rel,
            f"workflows/{filename}",
            f"nodes/workflows/{filename}",
            item["source_rel_path"],
        ]
        if standard_slug:
            aliases.extend(
                [
                    f"{standard_slug}/{task_slug}",
                    f"workflows/{standard_slug}/{filename}",
                    f"asme_b31.3/nodes/workflows/{filename}",
                ]
            )
        database.upsert_node(
            node_id=str(item["node_id"]),
            kind="workflow",
            metadata=item["metadata"],
            body=str(item["body"]),
            source_rel_path=rel,
            aliases=aliases,
        )

    count = len(database.list_node_ids())
    print(f"Built {db_path} ({count} workflows)")
    return db_path


if __name__ == "__main__":
    path = build_all()
    if path is None:
        print("No workflow tasks found to compile")
    else:
        print("Global workflows database built")
