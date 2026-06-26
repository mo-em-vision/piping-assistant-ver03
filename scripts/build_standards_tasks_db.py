#!/usr/bin/env python3
"""Compile global workflow task markdown sources into standards/tasks/tasks.db."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_paths import resolve_global_tasks_db, resolve_standards_tasks_dir
from engine.reference.standards_tasks_db import StandardsTasksDatabase


def _discover_tasks(tasks_root: Path) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    if not tasks_root.is_dir():
        return discovered

    for path in sorted(tasks_root.glob("*/*/root.md")):
        standard_slug = path.parent.parent.name
        task_slug = path.parent.name
        text = path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        node_id = str(metadata.get("id") or task_slug).strip()
        if not node_id:
            continue
        source_rel_path = f"{standard_slug}/{task_slug}"
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
    root = (standards_root or (_ROOT / "standards")).resolve()
    tasks_root = resolve_standards_tasks_dir(root)
    discovered = _discover_tasks(tasks_root)
    if not discovered:
        return None

    db_path = resolve_global_tasks_db(root)
    database = StandardsTasksDatabase(db_path)
    database.clear_all()

    for item in discovered:
        standard_slug = str(item["standard_slug"])
        task_slug = str(item["task_slug"])
        aliases = [
            task_slug,
            f"{standard_slug}/{task_slug}",
            f"tasks/{standard_slug}/{task_slug}",
            f"tasks/{standard_slug}/{task_slug}/root.md",
            item["source_rel_path"],
        ]
        database.upsert_node(
            node_id=str(item["node_id"]),
            kind="root",
            metadata=item["metadata"],
            body=str(item["body"]),
            source_rel_path=str(item["source_rel_path"]),
            aliases=aliases,
        )

    count = len(database.list_node_ids())
    print(f"Built {db_path} ({count} workflow roots)")
    return db_path


if __name__ == "__main__":
    path = build_all()
    if path is None:
        print("No workflow tasks found to compile")
    else:
        print("Global tasks database built")
