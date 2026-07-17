#!/usr/bin/env python3
"""Migrate knowledge node relationship fields to canonical ``edges`` schema."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.reference.graph_compile import compile_metadata_edges, parse_dependency_node_ref
from engine.reference.graph_compile_legacy import compile_legacy_metadata_edges
from engine.reference.graph_edge_schema import (
    DEPRECATED_TOP_LEVEL_RELATIONSHIP_KEYS,
    edge_target,
    relationship_metadata,
)
from engine.reference.node_sources import iter_node_source_paths
from engine.reference.standards_markdown import compose_frontmatter, split_frontmatter
from engine.reference.standards_paths import list_standard_packs

_LEGACY_TYPE_MAP = {
    "anchors_to": "references",
    "next_step": "next",
    "calculates": "implements",
    "outputs": "parameter",
    "converts_to": "derived_from",
    "uses_table": "table",
    "located_in": "parent",
    "defines": "related_to",
    "explains": "related_to",
    "validates": "related_to",
    "defined_by": "related_to",
    "accepts": "related_to",
    "uses": "uses",
}

_DEPENDENCY_TYPE_MAP = {
    "reference": "references",
    "calculation": "depends_on",
    "lookup": "table",
    "requires": "depends_on",
    "dependency": "depends_on",
}


def _edge_dict(edge_type: str, target: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"type": edge_type, "target": target}
    if meta:
        for key, value in meta.items():
            if key in {"ref", "file", "node_id", "to", "id", "dependency_type", "direction"}:
                continue
            item[key] = value
    return item


def _dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str | None]] = set()
    out: list[dict[str, Any]] = []
    for item in edges:
        edge_type = str(item.get("type", ""))
        target = edge_target(item)
        alias = str(item.get("alias", "")) or None
        key = (edge_type, target, alias)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _rename_nested_references(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if key == "references" and "nomenclature" in str(obj.get("symbol", "")) or False:
                out[key] = _rename_nested_references(value)
            elif key == "references" and isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict) and any(
                    k in first for k in ("paragraph", "equation", "table", "node_id", "reason")
                ):
                    out["citations"] = _rename_nested_references(value)
                elif key == "references" and "input_id" in obj or "id" in obj and "references" in obj:
                    # table inputs keep as parameter edges at top level; rename schema refs
                    out["citations"] = _rename_nested_references(value)
                else:
                    out[key] = _rename_nested_references(value)
            elif key == "references" and isinstance(value, list):
                out["citations"] = _rename_nested_references(value)
            else:
                out[key] = _rename_nested_references(value)
        return out
    if isinstance(obj, list):
        return [_rename_nested_references(item) for item in obj]
    return obj


def _migrate_nomenclature_and_docs(metadata: dict[str, Any]) -> None:
    nomenclature = metadata.get("nomenclature")
    if isinstance(nomenclature, list):
        for item in nomenclature:
            if isinstance(item, dict) and "references" in item:
                item["citations"] = item.pop("references")
    documentation = metadata.get("documentation")
    if isinstance(documentation, dict) and "references" in documentation:
        documentation["citations"] = documentation.pop("references")


def _migrate_table_inputs(metadata: dict[str, Any], edges: list[dict[str, Any]]) -> None:
    inputs = metadata.get("inputs")
    if not isinstance(inputs, list):
        return
    for item in inputs:
        if not isinstance(item, dict):
            continue
        refs = item.get("references")
        if not isinstance(refs, list):
            continue
        for ref in refs:
            target = str(ref).strip() if isinstance(ref, str) else str(ref.get("node_id", "")).strip()
            if target:
                edges.append(_edge_dict("parameter", target))
        item.pop("references", None)


def metadata_to_edges(node_id: str, metadata: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Convert legacy relationship metadata to canonical edges list."""
    edges: list[dict[str, Any]] = []
    flags: list[str] = []

    for item in metadata.get("hierarchy", []) or []:
        if isinstance(item, dict):
            parent = str(item.get("node_id", "")).strip()
            if parent:
                edges.append(_edge_dict("parent", parent))

    parent_node_id = str(metadata.get("parent_node_id") or "").strip()
    if parent_node_id:
        edges.append(_edge_dict("parent", parent_node_id))

    for item in metadata.get("depends_on", []) or []:
        if isinstance(item, dict):
            dep_ref = str(item.get("node_id", "")).strip()
            if not dep_ref:
                continue
            dep_id, subsection = parse_dependency_node_ref(dep_ref)
            dep_type = str(item.get("dependency_type") or "depends_on")
            edge_type = _DEPENDENCY_TYPE_MAP.get(dep_type, "depends_on")
            meta = relationship_metadata(item)
            if subsection and "subsection" not in meta:
                meta = {**meta, "subsection": subsection}
            edges.append(_edge_dict(edge_type, dep_id, meta or None))
        elif isinstance(item, str) and item.strip():
            dep_id, subsection = parse_dependency_node_ref(item.strip())
            meta = {"subsection": subsection} if subsection else None
            edges.append(_edge_dict("depends_on", dep_id, meta))

    for item in metadata.get("references", []) or []:
        if isinstance(item, str):
            edges.append(_edge_dict("references", item))
        elif isinstance(item, dict):
            target = str(item.get("node_id") or item.get("to") or item.get("id") or "").strip()
            if target:
                edges.append(_edge_dict("references", target, relationship_metadata(item) or None))

    for item in metadata.get("requires", []) or []:
        if isinstance(item, str):
            edges.append(_edge_dict("requires", item))
        elif isinstance(item, dict):
            target = edge_target(item)
            if target:
                edges.append(_edge_dict("requires", target, relationship_metadata(item) or None))

    for item in metadata.get("calculates", []) or []:
        target = str(item).strip() if isinstance(item, str) else edge_target(item)
        if target:
            edges.append(_edge_dict("implements", target))

    for item in metadata.get("outputs", []) or []:
        target = str(item).strip() if isinstance(item, str) else edge_target(item)
        if target:
            edges.append(_edge_dict("parameter", target))

    anchors_to = metadata.get("anchors_to")
    if isinstance(anchors_to, str) and anchors_to.strip():
        edges.append(_edge_dict("references", anchors_to.strip()))
        flags.append("anchors_to→references")

    for item in metadata.get("converts_to", []) or []:
        if isinstance(item, dict):
            target = edge_target(item)
            if target:
                edges.append(_edge_dict("derived_from", target, relationship_metadata(item) or None))

    for subsection in metadata.get("subsections", []) or []:
        if not isinstance(subsection, dict):
            continue
        subsection_id = str(subsection.get("id") or "").strip() or None
        for equation in subsection.get("equations", []) or []:
            if not isinstance(equation, dict):
                continue
            if str(equation.get("ref") or "").strip().lower() == "external":
                target = edge_target(equation)
                if target:
                    meta = relationship_metadata(equation)
                    if subsection_id:
                        meta = {**(meta or {}), "subsection": subsection_id}
                    edges.append(_edge_dict("equation", target, meta or None))
            else:
                flags.append(f"unmigrated subsection equation in {subsection_id}")

    for item in metadata.get("equations", []) or []:
        if isinstance(item, dict) and str(item.get("ref") or "").strip().lower() == "external":
            target = edge_target(item)
            if target:
                edges.append(_edge_dict("equation", target, relationship_metadata(item) or None))

    for legacy_key in (
        "contains",
        "defines",
        "explains",
        "uses_table",
        "validates",
        "located_in",
        "defined_by",
        "related_to",
        "uses",
        "accepts",
        "next_step",
    ):
        targets = metadata.get(legacy_key)
        if not targets:
            continue
        mapped = _LEGACY_TYPE_MAP.get(legacy_key, legacy_key)
        if isinstance(targets, str):
            edges.append(_edge_dict(mapped, targets))
        elif isinstance(targets, list):
            for target in targets:
                if isinstance(target, str):
                    edges.append(_edge_dict(mapped, target))
                elif isinstance(target, dict):
                    tid = edge_target(target)
                    if tid:
                        edges.append(_edge_dict(str(target.get("type") or mapped), tid, relationship_metadata(target) or None))

    for item in metadata.get("edges", []) or []:
        if not isinstance(item, dict):
            continue
        target = edge_target(item)
        if not target:
            continue
        dep_id, subsection = parse_dependency_node_ref(target)
        edge_type = str(item.get("type") or "related_to")
        if edge_type == "next_step":
            edge_type = "next"
        if edge_type == "anchors_to":
            edge_type = "references"
            flags.append("anchors_to→references")
        meta = relationship_metadata(item)
        if subsection:
            meta = {**(meta or {}), "subsection": subsection}
        direction = str(item.get("direction") or "outgoing")
        if direction == "incoming":
            flags.append(f"incoming edge flipped manually required: {node_id} {edge_type} {dep_id}")
        else:
            edges.append(_edge_dict(edge_type, dep_id, meta or None))

    _migrate_table_inputs(metadata, edges)
    return _dedupe_edges(edges), flags


def strip_deprecated_relationship_keys(metadata: dict[str, Any]) -> None:
    for key in DEPRECATED_TOP_LEVEL_RELATIONSHIP_KEYS:
        metadata.pop(key, None)
    metadata.pop("parent_node_id", None)
    for subsection in metadata.get("subsections", []) or []:
        if isinstance(subsection, dict):
            subsection.pop("equations", None)


def migrate_metadata(node_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    meta = copy.deepcopy(metadata)
    edges, _flags = metadata_to_edges(node_id, meta)
    strip_deprecated_relationship_keys(meta)
    _migrate_nomenclature_and_docs(meta)
    meta["edges"] = edges
    return meta


def migrate_file(path: Path) -> tuple[dict[str, Any], list[str]]:
    text = path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(text)
    node_id = str(metadata.get("id") or path.stem).strip()
    flags: list[str] = []
    edges, edge_flags = metadata_to_edges(node_id, metadata)
    flags.extend(edge_flags)
    strip_deprecated_relationship_keys(metadata)
    _migrate_nomenclature_and_docs(metadata)
    metadata["edges"] = edges
    return {"metadata": metadata, "body": body, "flags": flags}


def write_migrated_file(path: Path, metadata: dict[str, Any], body: str) -> None:
    path.write_text(compose_frontmatter(metadata, body), encoding="utf-8")


def _edge_set(
    compiled: list[tuple[str, str, str, dict[str, Any] | None]],
) -> set[tuple[str, str, str]]:
    return {(a, b, c) for a, b, c, _ in compiled}


def migrate_nodes_dir(nodes_dir: Path, *, write: bool, label: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "pack": label,
        "files": 0,
        "migrated": 0,
        "flags": [],
        "connectivity_diffs": [],
    }
    for path in iter_node_source_paths(nodes_dir):
        report["files"] += 1
        text = path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        node_id = str(metadata.get("id") or path.stem).strip()

        legacy_edges = compile_legacy_metadata_edges(node_id, metadata)
        new_meta = migrate_metadata(node_id, metadata)
        new_edges = compile_metadata_edges(node_id, new_meta)

        legacy_set = _edge_set(legacy_edges)
        new_set = _edge_set(new_edges)
        if legacy_set != new_set:
            report["connectivity_diffs"].append(
                {
                    "node_id": node_id,
                    "path": str(path.relative_to(ROOT)),
                    "removed": sorted(legacy_set - new_set),
                    "added": sorted(new_set - legacy_set),
                }
            )

        _, flags = metadata_to_edges(node_id, split_frontmatter(text)[0])
        if flags:
            report["flags"].append({"node_id": node_id, "flags": flags})

        if write:
            write_migrated_file(path, new_meta, body)
            report["migrated"] += 1

    return report


def migrate_pack(pack_root: Path, *, write: bool) -> dict[str, Any]:
    nodes_dir = pack_root / "nodes"
    return migrate_nodes_dir(nodes_dir, write=write, label=pack_root.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate node relationship fields to edges schema")
    parser.add_argument("--write", action="store_true", help="Write migrated files")
    parser.add_argument("--report", type=Path, default=ROOT / "docs" / "audit" / "graph_edges_migration_report.json")
    args = parser.parse_args()

    standards_root = ROOT / "knowledge" / "standards"
    reports: list[dict[str, Any]] = []

    for _slug, pack_root in list_standard_packs(standards_root):
        reports.append(migrate_pack(pack_root, write=args.write))

    global_root = ROOT / "knowledge" / "global"
    for domain in ("dimensions", "units", "materials"):
        nodes_dir = global_root / domain / "nodes"
        if nodes_dir.is_dir():
            reports.append(migrate_nodes_dir(nodes_dir, write=args.write, label=f"global/{domain}"))

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(f"Report written to {args.report}")
    if not args.write:
        print("Dry run — pass --write to apply migrations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
