"""Tests for compiling standards nodes into SQLite."""

from __future__ import annotations

import shutil
from pathlib import Path

from engine.reference.pack_nodes_db import resolve_pack_nodes_db
from engine.reference.standards_nodes import StandardsNodesDatabase
from scripts.build_standards_nodes_db import build_pack


def test_build_pack_dedupes_flat_path_over_nested_duplicate(tmp_path: Path, project_root: Path) -> None:
    pack = tmp_path / "asme_b31.3"
    shutil.copytree(project_root / "standards" / "asme" / "asme_b31.3" / "nodes", pack / "nodes")
    flat = pack / "nodes" / "B313-304.1.1"
    nested = pack / "nodes" / "304" / "304.1" / "304.1.1"
    assert flat.is_dir()
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "node.md").write_text(
        "---\nid: B313-304.1.1\ntype: calculation\n---\nNested duplicate\n",
        encoding="utf-8",
    )

    db_path = build_pack(pack)
    assert db_path is not None
    database = StandardsNodesDatabase(db_path)
    node = database.get_node("B313-304.1.1")
    assert node is not None
    assert node["source_rel_path"].endswith("B313-304.1.1")
    assert not nested.exists()


def test_build_b313_pack_node_count(project_root: Path) -> None:
    pack = project_root / "standards" / "asme" / "asme_b31.3"
    db_path = build_pack(pack)
    assert db_path is not None
    count = len(StandardsNodesDatabase(db_path).list_node_ids())
    assert count >= 16
    assert "B313-PIPE-WALL-THICKNESS-DESIGN" not in StandardsNodesDatabase(db_path).list_node_ids()
