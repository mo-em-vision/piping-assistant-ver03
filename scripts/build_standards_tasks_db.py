#!/usr/bin/env python3
"""Compile workflow YAML nodes from pack nodes/workflows/ into workflows.db."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_paths import list_standard_packs, resolve_global_tasks_db
from engine.reference.standards_tasks_db import StandardsTasksDatabase


def _discover_workflows(standards_root: Path) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    for standard_slug, pack_root in list_standard_packs(standards_root):
        workflows_dir = pack_root / "nodes" / "workflows"
        if not workflows_dir.is_dir():
            continue
        for path in sorted(workflows_dir.glob("*.yaml")):
            text = path.read_text(encoding="utf-8")
            metadata, body = split_frontmatter(text)
            if str(metadata.get("type") or "") != "workflow":
                continue
            node_id = str(metadata.get("id") or path.stem).strip()
            if not node_id:
                continue
            rel = path.relative_to(pack_root).as_posix()
            source_rel_path = f"{standard_slug}/{rel}"
            task_slug = str(metadata.get("slug") or path.stem).strip()
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
        aliases = [
            task_slug,
            f"{standard_slug}/{task_slug}",
            rel,
            f"nodes/workflows/{Path(item['source_path']).name}",
            item["source_rel_path"],
        ]
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
