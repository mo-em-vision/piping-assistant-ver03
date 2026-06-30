#!/usr/bin/env python3
"""Flatten ASME B31.3 nodes/ tree to nodes/{node_id}/ without editing node content."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.embedded_nodes import iter_embedded_node_sources
from engine.reference.standards_markdown import split_frontmatter

PACK = _ROOT / "standards" / "asme" / "asme_b31.3"
NODES = PACK / "nodes"
_NODE_FILES = ("node.yaml", "node.yml", "node.md")


@dataclass
class _NodeHome:
    path: Path
    node_id: str
    prefers_yaml: bool


def _node_id_from_dir(node_dir: Path) -> tuple[str, bool] | None:
    prefers_yaml = False
    metadata: dict = {}
    for name in ("node.yaml", "node.yml", "node.md"):
        path = node_dir / name
        if not path.is_file():
            continue
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        if name.endswith((".yaml", ".yml")):
            prefers_yaml = True
            metadata = meta
            break
        if not metadata:
            metadata = meta
    node_id = str(metadata.get("id") or node_dir.name).strip()
    if not node_id:
        return None
    return node_id, prefers_yaml


def _discover_homes(nodes_dir: Path) -> list[_NodeHome]:
    seen_dirs: set[Path] = set()
    homes: list[_NodeHome] = []
    for pattern in _NODE_FILES:
        for path in sorted(nodes_dir.rglob(pattern)):
            node_dir = path.parent.resolve()
            if node_dir in seen_dirs:
                continue
            seen_dirs.add(node_dir)
            parsed = _node_id_from_dir(node_dir)
            if parsed is None:
                continue
            node_id, prefers_yaml = parsed
            homes.append(_NodeHome(path=node_dir, node_id=node_id, prefers_yaml=prefers_yaml))
    return homes


def _embedded_child_ids(nodes_dir: Path, homes: list[_NodeHome]) -> dict[str, Path]:
    """Map embedded child id -> parent home path that owns the embedding."""
    embedded: dict[str, Path] = {}
    for home in homes:
        rel = home.path.relative_to(nodes_dir.parent).as_posix()
        for name in _NODE_FILES:
            path = home.path / name
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            metadata, _ = split_frontmatter(text)
            for item in iter_embedded_node_sources(
                parent_id=home.node_id,
                parent_source_rel_path=rel,
                metadata=metadata,
            ):
                embedded[item.node_id] = home.path
    return embedded


def _is_flat_home(home: _NodeHome, nodes_dir: Path) -> bool:
    rel = home.path.relative_to(nodes_dir)
    return len(rel.parts) == 1 and rel.parts[0] == home.node_id


def _merge_move(src: Path, dest: Path, *, dry_run: bool) -> None:
    if src.resolve() == dest.resolve():
        return
    if not dest.exists():
        if dry_run:
            print(f"  MOVE {src.relative_to(PACK)} -> {dest.relative_to(PACK)}")
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return

    for item in sorted(src.iterdir()):
        target = dest / item.name
        if item.is_dir():
            _merge_move(item, target, dry_run=dry_run)
        else:
            if dry_run:
                print(f"  MERGE {item.relative_to(PACK)} -> {target.relative_to(PACK)}")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    target.unlink()
                shutil.move(str(item), str(target))
    if dry_run:
        print(f"  RMDIR {src.relative_to(PACK)}")
    else:
        shutil.rmtree(src, ignore_errors=True)


def _remove_empty_dirs(root: Path, *, dry_run: bool) -> None:
    if not root.is_dir():
        return
    for child in sorted(root.iterdir(), reverse=True):
        if child.is_dir():
            _remove_empty_dirs(child, dry_run=dry_run)
    if root == NODES:
        return
    try:
        if not any(root.iterdir()):
            if dry_run:
                print(f"  RMDIR {root.relative_to(PACK)}")
            else:
                root.rmdir()
    except OSError:
        pass


def _nested_contains_dupes(homes: list[_NodeHome]) -> set[Path]:
    """Folders for ids listed in a parent node.yaml ``contains`` under that parent."""
    delete_paths: set[Path] = set()
    home_by_id = {h.node_id: h for h in homes}
    for home in homes:
        yaml_path = home.path / "node.yaml"
        if not yaml_path.is_file():
            yaml_path = home.path / "node.yml"
        if not yaml_path.is_file():
            continue
        metadata, _ = split_frontmatter(yaml_path.read_text(encoding="utf-8"))
        for child_id in metadata.get("contains") or []:
            if not isinstance(child_id, str):
                continue
            child = home_by_id.get(child_id.strip())
            if child is None or child.path.resolve() == home.path.resolve():
                continue
            try:
                child.path.relative_to(home.path)
            except ValueError:
                continue
            delete_paths.add(child.path.resolve())
    return delete_paths


def flatten(*, dry_run: bool = False) -> None:
    if not NODES.is_dir():
        raise SystemExit(f"Missing nodes directory: {NODES}")

    homes = _discover_homes(NODES)
    embedded_parents = _embedded_child_ids(NODES, homes)
    contains_dupes = _nested_contains_dupes(homes)

    deleted = 0
    moved = 0
    skipped = 0

    # Remove standalone folders for ids embedded inside an ancestor directory.
    for home in sorted(homes, key=lambda h: len(h.path.parts), reverse=True):
        parent_path = embedded_parents.get(home.node_id)
        is_embedded_dup = False
        if parent_path is not None and home.path.resolve() != parent_path.resolve():
            try:
                home.path.relative_to(parent_path)
                is_embedded_dup = True
            except ValueError:
                pass
        if home.path.resolve() in contains_dupes:
            is_embedded_dup = True
        if not is_embedded_dup:
            continue
        if dry_run:
            print(f"  DELETE embedded dup {home.path.relative_to(PACK)} ({home.node_id})")
        else:
            shutil.rmtree(home.path, ignore_errors=True)
        deleted += 1

    homes = _discover_homes(NODES)

    for home in sorted(homes, key=lambda h: len(h.path.parts), reverse=True):
        if _is_flat_home(home, NODES):
            skipped += 1
            continue
        dest = NODES / home.node_id
        if dry_run:
            print(f"  FLATTEN {home.path.relative_to(PACK)} -> nodes/{home.node_id}/")
        else:
            _merge_move(home.path, dest, dry_run=False)
        moved += 1

    _remove_empty_dirs(NODES, dry_run=dry_run)

    print(f"\nSummary: moved={moved}, deleted_embedded_dups={deleted}, already_flat={skipped}")
    if dry_run:
        print("(dry run — no changes written)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print actions without moving files")
    args = parser.parse_args()
    flatten(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
