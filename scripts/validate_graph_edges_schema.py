"""Validate knowledge nodes use canonical ``edges`` relationship schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.reference.graph_compile import validate_edge_item
from engine.reference.graph_edge_schema import DEPRECATED_TOP_LEVEL_RELATIONSHIP_KEYS
from engine.reference.node_sources import iter_node_source_paths
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_paths import list_standard_packs


def _validate_nodes_dir(nodes_dir: Path, graph_node_ids: set[str]) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    for path in iter_node_source_paths(nodes_dir):
        metadata, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        node_id = str(metadata.get("id") or path.stem)
        node_issues: list[str] = []
        if "edges" not in metadata:
            node_issues.append("missing edges key")
        for key in DEPRECATED_TOP_LEVEL_RELATIONSHIP_KEYS:
            if key in metadata:
                node_issues.append(f"deprecated field: {key}")
        for item in metadata.get("edges", []) or []:
            if not isinstance(item, dict):
                node_issues.append("edge entry is not a mapping")
                continue
            node_issues.extend(validate_edge_item(item))
            target = str(item.get("target") or item.get("to") or item.get("node_id") or "").strip()
            if target and target not in graph_node_ids:
                node_issues.append(f"broken target: {target}")
        if node_issues:
            issues[node_id] = node_issues
    return issues


def main() -> int:
    from engine.graph.graph_builder import GraphBuilder

    standards_root = ROOT / "knowledge" / "standards"
    all_issues: dict[str, dict[str, list[str]]] = {}
    for _slug, pack_root in list_standard_packs(standards_root):
        graph = GraphBuilder(pack_root).build()
        issues = _validate_nodes_dir(pack_root / "nodes", set(graph.nodes.keys()))
        if issues:
            all_issues[pack_root.name] = issues

    global_root = ROOT / "knowledge" / "global"
    for domain in ("dimensions", "units", "materials"):
        nodes_dir = global_root / domain / "nodes"
        if nodes_dir.is_dir():
            issues = _validate_nodes_dir(nodes_dir, set())
            if issues:
                all_issues[f"global/{domain}"] = issues

    report_path = ROOT / "docs" / "migration" / "graph_edges_migration_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Graph Edges Migration Validation\n"]
    if not all_issues:
        lines.append("All scanned nodes passed validation.\n")
    else:
        for pack, pack_issues in all_issues.items():
            lines.append(f"## {pack}\n")
            for node_id, node_issues in sorted(pack_issues.items()):
                lines.append(f"- **{node_id}**: " + "; ".join(node_issues))
            lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {report_path}")
    return 1 if all_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
