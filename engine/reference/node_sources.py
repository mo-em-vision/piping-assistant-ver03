"""Shared discovery of micro-graph node source files under a pack ``nodes/`` tree."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

_LEGACY_NODE_FILENAMES = ("node.yaml", "node.yml", "node.md")


_SIDECAR_FILENAMES = frozenset(
    {
        "execution.yaml",
        "execution.yml",
        "nomenclature.yaml",
        "nomenclature.yml",
        "runtime.yaml",
        "runtime.yml",
        "navigation.yaml",
        "navigation.yml",
    }
)


def _is_sidecar_source(path: Path) -> bool:
    return path.name.lower() in _SIDECAR_FILENAMES


def iter_node_source_paths(nodes_dir: Path) -> Iterator[Path]:
    """Yield node source files: legacy ``node.yaml`` and named ``{id}.yaml`` files."""
    if not nodes_dir.is_dir():
        return

    seen: set[Path] = set()
    for pattern in _LEGACY_NODE_FILENAMES:
        for path in sorted(nodes_dir.rglob(pattern)):
            if path in seen:
                continue
            seen.add(path)
            yield path

    for path in sorted(nodes_dir.rglob("*.yaml")):
        if path in seen:
            continue
        if path.name in _LEGACY_NODE_FILENAMES:
            continue
        if _is_sidecar_source(path):
            continue
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        seen.add(path)
        yield path

    for path in sorted(nodes_dir.rglob("*.yml")):
        if path in seen:
            continue
        if path.name in _LEGACY_NODE_FILENAMES:
            continue
        if _is_sidecar_source(path):
            continue
        seen.add(path)
        yield path

    for path in sorted(nodes_dir.rglob("*.md")):
        if path in seen:
            continue
        if path.name in _LEGACY_NODE_FILENAMES:
            continue
        if _is_sidecar_source(path):
            continue
        seen.add(path)
        yield path


def source_rel_path(pack_root: Path, source_path: Path) -> str:
    """Return pack-relative path to the source file (not parent folder)."""
    try:
        return source_path.relative_to(pack_root).as_posix()
    except ValueError:
        return source_path.as_posix()
