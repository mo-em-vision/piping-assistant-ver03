#!/usr/bin/env python3
"""Inline B31.3 per-node asset subfolders into parent node.yaml source blocks."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.standards_markdown import compose_frontmatter, split_frontmatter

PACK = _ROOT / "standards" / "asme" / "asme_b31.3"
NODES = PACK / "nodes"

_ASSET_DIRS = ("equations", "conditions", "notes", "references")
_CONTAINER_KEYS = (
    "equations",
    "conditions",
    "notes",
    "references",
    "texts",
    "assumptions",
    "interactions",
)

_CROSS_REF_FIXES = {
    "../304.1.2/equations/mawp_pressure.md": "nodes/B313-304.1.2/equations/mawp_pressure.md",
    "../304.1.2/equations/thick_wall_y.md": "nodes/B313-304.1.2/equations/thick_wall_y.md",
    "../mawp_definition/equations/pressure_design_thickness.md": "nodes/B313-MAWP-SECTION/equations/pressure_design_thickness.md",
}

_ORPHAN_ASSET_DEFAULTS: dict[str, dict[str, Any]] = {
    "equations/wall_thickness.md": {
        "container": "equations",
        "item": {"id": "B313-eq-wall-thickness", "type": "equation"},
    },
    "equations/mawp_pressure.md": {
        "container": "equations",
        "item": {"id": "B313-eq-mawp", "type": "equation"},
    },
    "equations/thick_wall_y.md": {
        "container": "equations",
        "item": {"id": "thick_wall_y", "type": "equation"},
    },
    "conditions/thin_wall_check.md": {
        "container": "conditions",
        "item": {"type": "text", "kind": "condition"},
    },
}


def _normalize_ref(value: str) -> str:
    return value.replace("\\", "/").lstrip("/")


def _content_matches(existing_source: str, disk_text: str) -> bool:
    return re.sub(r"\s+", " ", existing_source.strip()) == re.sub(r"\s+", " ", disk_text.strip())


def _iter_container_items(metadata: dict[str, Any]):
    for key in _CONTAINER_KEYS:
        items = metadata.get(key)
        if isinstance(items, list):
            for index, item in enumerate(items):
                if isinstance(item, dict):
                    yield key, items, index, item
    for subsection in metadata.get("subsections", []) or []:
        if not isinstance(subsection, dict):
            continue
        for key in ("equations",):
            items = subsection.get(key)
            if isinstance(items, list):
                for index, item in enumerate(items):
                    if isinstance(item, dict):
                        yield key, items, index, item, subsection


def _find_item_for_asset(metadata: dict[str, Any], relative_path: str) -> tuple[str, list, int, dict] | None:
    filename = Path(relative_path).name
    stem = Path(relative_path).stem
    for entry in _iter_container_items(metadata):
        if len(entry) == 4:
            _key, items, index, item = entry
        else:
            _key, items, index, item, _subsection = entry
        file_ref = _normalize_ref(str(item.get("file") or ""))
        if file_ref == relative_path or file_ref.endswith(f"/{filename}"):
            return entry  # type: ignore[return-value]
        item_id = str(item.get("id") or item.get("equation_id") or "").strip()
        if item_id and (item_id == stem or item_id.replace("-", "_") == stem):
            return entry  # type: ignore[return-value]
    return None


def _inline_asset_item(item: dict[str, Any], disk_text: str) -> None:
    existing = str(item.get("source") or "")
    if existing:
        item.pop("file", None)
        if _content_matches(existing, disk_text):
            return
    item["source"] = disk_text.rstrip() + "\n"
    item.pop("file", None)


def _add_orphan_asset(metadata: dict[str, Any], relative_path: str, disk_text: str) -> None:
    defaults = _ORPHAN_ASSET_DEFAULTS.get(relative_path)
    if defaults is None:
        container = relative_path.split("/", 1)[0]
        defaults = {"container": container, "item": {}}
    container = defaults["container"]
    item = dict(defaults.get("item") or {})
    file_meta, _body = split_frontmatter(disk_text)
    if isinstance(file_meta, dict):
        item.setdefault("id", str(file_meta.get("id") or file_meta.get("equation_id") or Path(relative_path).stem))
        item.setdefault("type", file_meta.get("type") or ("equation" if container == "equations" else "text"))
    item["source"] = disk_text.rstrip() + "\n"
    metadata.setdefault(container, [])
    if isinstance(metadata[container], list):
        metadata[container].append(item)


def _fix_cross_refs(metadata: dict[str, Any]) -> int:
    changed = 0

    def walk(value: Any) -> Any:
        nonlocal changed
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, str):
            normalized = _normalize_ref(value)
            if normalized in _CROSS_REF_FIXES:
                changed += 1
                return _CROSS_REF_FIXES[normalized]
            if normalized.startswith("equations/") and normalized.endswith("/node.yaml"):
                changed += 1
                return None
        return value

    updated = walk(metadata)
    if isinstance(updated, dict):
        metadata.clear()
        metadata.update(updated)
    return changed


def _strip_none_file_values(metadata: dict[str, Any]) -> None:
    def walk(value: Any) -> Any:
        if isinstance(value, dict):
            cleaned = {key: walk(item) for key, item in value.items()}
            if cleaned.get("file") is None:
                cleaned.pop("file", None)
            return cleaned
        if isinstance(value, list):
            return [walk(item) for item in value]
        return value

    cleaned = walk(metadata)
    if isinstance(cleaned, dict):
        metadata.clear()
        metadata.update(cleaned)


def _convert_md_node_to_yaml(node_dir: Path) -> bool:
    md_path = node_dir / "node.md"
    yaml_path = node_dir / "node.yaml"
    if not md_path.is_file() or yaml_path.is_file():
        return False
    text = md_path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(text)
    yaml_path.write_text(compose_frontmatter(metadata, body), encoding="utf-8")
    md_path.unlink()
    return True


def _move_py_modules_to_root(node_dir: Path) -> list[str]:
    moved: list[str] = []
    eq_dir = node_dir / "equations"
    if not eq_dir.is_dir():
        return moved
    for path in sorted(eq_dir.glob("*.py")):
        target = node_dir / path.name
        if target.exists():
            continue
        shutil.move(str(path), str(target))
        moved.append(path.name)
    return moved


def _update_calculation_modules(metadata: dict[str, Any]) -> int:
    changed = 0

    def walk(item: Any) -> Any:
        nonlocal changed
        if isinstance(item, dict):
            updated = {key: walk(value) for key, value in item.items()}
            module = updated.get("calculation_module")
            if isinstance(module, str) and module.startswith("equations/"):
                updated["calculation_module"] = Path(module).name
                changed += 1
            return updated
        if isinstance(item, list):
            return [walk(value) for value in item]
        return item

    cleaned = walk(metadata)
    if isinstance(cleaned, dict):
        metadata.clear()
        metadata.update(cleaned)
    return changed


def _sync_subsection_equation_sources(metadata: dict[str, Any]) -> int:
    top_level = {
        str(item.get("id") or ""): item
        for item in metadata.get("equations", []) or []
        if isinstance(item, dict) and item.get("id")
    }
    changed = 0
    for subsection in metadata.get("subsections", []) or []:
        if not isinstance(subsection, dict):
            continue
        for item in subsection.get("equations", []) or []:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id") or "")
            parent = top_level.get(item_id)
            if parent is None:
                continue
            if parent.get("source") and not item.get("source"):
                item["source"] = parent["source"]
                changed += 1
            if item.get("source") or parent.get("source"):
                item.pop("file", None)
                changed += 1
    return changed


def _cleanup_asset_dirs(node_dir: Path, *, dry_run: bool) -> int:
    removed = 0
    for folder in _ASSET_DIRS:
        asset_dir = node_dir / folder
        if asset_dir.is_dir():
            removed += sum(1 for path in asset_dir.rglob("*") if path.is_file())
            if not dry_run:
                shutil.rmtree(asset_dir, ignore_errors=True)
    eq_dir = node_dir / "equations"
    if eq_dir.is_dir() and not any(eq_dir.iterdir()):
        if not dry_run:
            shutil.rmtree(eq_dir, ignore_errors=True)
    return removed


def _process_node_dir(node_dir: Path, *, dry_run: bool) -> dict[str, int]:
    stats = {
        "inlined": 0,
        "deduped": 0,
        "added": 0,
        "deleted": 0,
        "cross_refs": 0,
        "py_moved": 0,
        "converted": 0,
    }
    converted = _convert_md_node_to_yaml(node_dir)
    if converted:
        stats["converted"] = 1

    source_path = node_dir / "node.yaml"
    if not source_path.is_file():
        source_path = node_dir / "node.md"
    if not source_path.is_file():
        return stats

    text = source_path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(text)

    for folder in _ASSET_DIRS:
        asset_dir = node_dir / folder
        if not asset_dir.is_dir():
            continue
        for path in sorted(asset_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".py":
                continue
            relative_path = f"{folder}/{path.name}"
            disk_text = path.read_text(encoding="utf-8")
            match = _find_item_for_asset(metadata, relative_path)
            if match is not None:
                if len(match) == 4:
                    _key, _items, _index, item = match
                else:
                    _key, _items, _index, item, _subsection = match
                had_source = bool(item.get("source"))
                _inline_asset_item(item, disk_text)
                if had_source and "file" not in item:
                    stats["deduped"] += 1
                else:
                    stats["inlined"] += 1
            else:
                _add_orphan_asset(metadata, relative_path, disk_text)
                stats["added"] += 1
            if not dry_run:
                path.unlink()
                stats["deleted"] += 1

    stats["cross_refs"] += _fix_cross_refs(metadata)
    stats["py_moved"] = len(_move_py_modules_to_root(node_dir) if not dry_run else list((node_dir / "equations").glob("*.py")) if (node_dir / "equations").is_dir() else [])
    stats["deduped"] += _sync_subsection_equation_sources(metadata)
    _update_calculation_modules(metadata)
    _strip_none_file_values(metadata)

    if source_path.suffix.lower() == ".md":
        target = node_dir / "node.yaml"
        if not dry_run:
            target.write_text(compose_frontmatter(metadata, body), encoding="utf-8")
            source_path.unlink()
        stats["converted"] = 1
    elif not dry_run:
        source_path.write_text(compose_frontmatter(metadata, body), encoding="utf-8")

    if not dry_run:
        stats["deleted"] += _cleanup_asset_dirs(node_dir, dry_run=False)

    return stats


def _cleanup_legacy_trees(*, dry_run: bool) -> list[str]:
    removed: list[str] = []
    for legacy in ("302", "304", "parameters"):
        legacy_dir = NODES / legacy
        if legacy_dir.is_dir():
            removed.append(str(legacy_dir.relative_to(PACK)))
            if not dry_run:
                shutil.rmtree(legacy_dir, ignore_errors=True)
    return removed


def run(*, dry_run: bool) -> int:
    totals = {"nodes": 0, "inlined": 0, "deduped": 0, "added": 0, "deleted": 0, "cross_refs": 0, "py_moved": 0, "converted": 0}
    for node_dir in sorted(NODES.iterdir()):
        if not node_dir.is_dir():
            continue
        has_assets = any((node_dir / folder).is_dir() for folder in _ASSET_DIRS)
        has_md_only = (node_dir / "node.md").is_file() and not (node_dir / "node.yaml").is_file()
        has_py = (node_dir / "equations").is_dir() and any((node_dir / "equations").glob("*.py"))
        has_stale_file_refs = False
        source_path = node_dir / "node.yaml"
        if not source_path.is_file():
            source_path = node_dir / "node.md"
        if source_path.is_file():
            metadata, _ = split_frontmatter(source_path.read_text(encoding="utf-8"))
            has_stale_file_refs = any(
                isinstance(item, dict) and item.get("file")
                for entry in _iter_container_items(metadata)
                for item in [entry[3]]
            )
        if not has_assets and not has_md_only and not has_py and not has_stale_file_refs:
            continue
        print(f"inline {node_dir.name}")
        stats = _process_node_dir(node_dir, dry_run=dry_run)
        totals["nodes"] += 1
        for key in totals:
            if key != "nodes":
                totals[key] += stats.get(key, 0)

    legacy_removed = _cleanup_legacy_trees(dry_run=dry_run)
    if legacy_removed:
        print(f"legacy trees: {', '.join(legacy_removed)}")

    # Fix cross-node refs in nodes without asset subfolders
    for node_name in ("B313-304.1.1", "B313-MAWP-SECTION", "B313-MAWP-CALCULATION"):
        node_dir = NODES / node_name
        source_path = node_dir / "node.yaml"
        if not source_path.is_file():
            source_path = node_dir / "node.md"
        if not source_path.is_file():
            continue
        metadata, body = split_frontmatter(source_path.read_text(encoding="utf-8"))
        cross_refs = _fix_cross_refs(metadata)
        _strip_none_file_values(metadata)
        if cross_refs:
            totals["cross_refs"] += cross_refs
            print(f"cross-ref fix {node_name}: {cross_refs}")
            if not dry_run:
                if source_path.suffix.lower() == ".md":
                    yaml_path = node_dir / "node.yaml"
                    yaml_path.write_text(compose_frontmatter(metadata, body), encoding="utf-8")
                    source_path.unlink()
                else:
                    source_path.write_text(compose_frontmatter(metadata, body), encoding="utf-8")

    action = "would update" if dry_run else "updated"
    print(
        f"\nSummary: {action} {totals['nodes']} node(s); "
        f"inlined={totals['inlined']} deduped={totals['deduped']} added={totals['added']} "
        f"deleted={totals['deleted']} cross_refs={totals['cross_refs']} py_moved={totals['py_moved']} "
        f"converted={totals['converted']}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
