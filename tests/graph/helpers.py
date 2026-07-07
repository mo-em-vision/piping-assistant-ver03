"""Synthetic graph pack builders for Graph Engine error-path tests."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_builder import GraphBuilder
from engine.graph.graph_store import GraphStore


def _write_node(path: Path, node_id: str, node_type: str, edges: list[dict]) -> None:
    edge_lines = "\n".join(
        f"  - type: {edge['type']}\n    target: {edge['target']}"
        + (
            f"\n    when:\n      field: {edge['when']['field']}\n      in: {edge['when']['in']}"
            if edge.get("when")
            else ""
        )
        for edge in edges
    )
    path.write_text(
        f"""---
id: {node_id}
type: {node_type}
title: {node_id}
edges:
{edge_lines}
metadata:
  last_revision: 2026-07-07
  edited_by: test
---
{node_id} test node.
""",
        encoding="utf-8",
    )


def build_cycle_pack(tmp_path: Path) -> GraphStore:
    """Three text nodes with a dependency cycle A -> B -> C -> A."""
    pack_root = tmp_path / "cycle_pack"
    nodes_dir = pack_root / "nodes" / "text"
    nodes_dir.mkdir(parents=True)
    (pack_root / "pack.yaml").write_text(
        """---
id: test_cycle_pack
title: Cycle test pack
authority: AUTH-TEST
---
""",
        encoding="utf-8",
    )
    _write_node(nodes_dir / "node-a.yaml", "node-a", "text", [{"type": "depends_on", "target": "node-b"}])
    _write_node(nodes_dir / "node-b.yaml", "node-b", "text", [{"type": "depends_on", "target": "node-c"}])
    _write_node(nodes_dir / "node-c.yaml", "node-c", "text", [{"type": "depends_on", "target": "node-a"}])
    GraphBuilder(pack_root).build()
    store = GraphStore(pack_root)
    store.load(prefer_cache=False)
    return store


def build_missing_dependency_pack(tmp_path: Path) -> GraphStore:
    """Single text node depending on a non-existent target."""
    pack_root = tmp_path / "missing_dep_pack"
    nodes_dir = pack_root / "nodes" / "text"
    nodes_dir.mkdir(parents=True)
    (pack_root / "pack.yaml").write_text(
        """---
id: test_missing_dep_pack
title: Missing dependency test pack
authority: AUTH-TEST
---
""",
        encoding="utf-8",
    )
    _write_node(
        nodes_dir / "node-root.yaml",
        "node-root",
        "text",
        [{"type": "depends_on", "target": "node-missing"}],
    )
    GraphBuilder(pack_root).build()
    store = GraphStore(pack_root)
    store.load(prefer_cache=False)
    return store
