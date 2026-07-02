#!/usr/bin/env python3
"""Migrate knowledge node edges from legacy transport types to taxonomy types."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

_SKIP_NAMES = frozenset(
    {
        "execution.yaml",
        "execution.yml",
        "runtime.yaml",
        "runtime.yml",
        "nomenclature.yaml",
        "nomenclature.yml",
    }
)

_KNOWLEDGE_ROOTS = (
    ROOT / "knowledge" / "global",
    ROOT / "knowledge" / "standards",
)


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            end_index = index
            break
    if end_index is None:
        return {}, text
    meta = yaml.safe_load("\n".join(lines[1:end_index])) or {}
    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return meta, body


def _compose(meta: dict[str, Any], body: str) -> str:
    yaml_text = yaml.safe_dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip()
    body_text = body.rstrip()
    if body_text:
        return f"---\n{yaml_text}\n---\n\n{body_text}\n"
    return f"---\n{yaml_text}\n---\n"


def _load_taxonomy_module():
    import importlib.util
    import sys

    path = ROOT / "engine" / "reference" / "relationship_taxonomy.py"
    name = "engine.reference.relationship_taxonomy"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _migrate_edges(meta: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    rt = _load_taxonomy_module()
    LEGACY_TRANSPORT_TYPES = rt.LEGACY_TRANSPORT_TYPES
    normalize_authoring_edge = rt.normalize_authoring_edge

    source_type = str(meta.get("type") or "")
    edges = meta.get("edges")
    if not isinstance(edges, list):
        return [], 0
    migrated: list[dict[str, Any]] = []
    changes = 0
    for item in edges:
        if not isinstance(item, dict):
            migrated.append(item)
            continue
        before_type = str(item.get("type") or "")
        normalized = normalize_authoring_edge(
            item,
            source_node_type=source_type,
            allow_legacy=True,
        )
        if normalized is None:
            migrated.append(item)
            continue
        new_item = dict(normalized)
        new_type = str(new_item.get("type") or "")
        if new_type != "references" and "role" in new_item:
            new_item.pop("role", None)
        if before_type in LEGACY_TRANSPORT_TYPES and new_type != before_type:
            changes += 1
        elif before_type == "references" and new_type != "references":
            changes += 1
        migrated.append(new_item)
    return migrated, changes


def _iter_yaml_paths() -> list[Path]:
    paths: list[Path] = []
    for root in _KNOWLEDGE_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.yaml")):
            if path.name in _SKIP_NAMES:
                continue
            if path.name in _SKIP_NAMES or path.suffix.lower() not in {".yaml", ".yml"}:
                continue
            paths.append(path)
        for path in sorted(root.rglob("*.yml")):
            if path.name in _SKIP_NAMES:
                continue
            paths.append(path)
    return sorted(set(paths))


def migrate_file(path: Path, *, dry_run: bool = False) -> int:
    text = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)
    if not meta or "edges" not in meta:
        return 0
    new_edges, changes = _migrate_edges(meta)
    if changes == 0:
        return 0
    meta["edges"] = new_edges
    if not dry_run:
        path.write_text(_compose(meta, body), encoding="utf-8")
    print(f"{'would migrate' if dry_run else 'migrated'} {path.relative_to(ROOT)} ({changes} edges)")
    return changes


def main(argv: list[str] | None = None) -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    dry_run = "--dry-run" in (argv or sys.argv[1:])
    total = 0
    files = 0
    for path in _iter_yaml_paths():
        changed = migrate_file(path, dry_run=dry_run)
        if changed:
            total += changed
            files += 1
    print(f"Done: {files} files, {total} edge type updates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
