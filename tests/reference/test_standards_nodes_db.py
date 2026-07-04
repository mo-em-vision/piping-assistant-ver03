"""Tests for per-pack standards nodes SQLite database."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.pack_nodes_db import resolve_pack_nodes_db
from engine.reference.standards_nodes import StandardsNodesDatabase


@pytest.fixture
def b313_nodes_db(project_root: Path) -> StandardsNodesDatabase:
    pack = project_root / "knowledge" / "standards" / "asme" / "asme_b31.3"
    db_path = resolve_pack_nodes_db(pack)
    if not db_path.is_file():
        pytest.skip("Run scripts/build_standards_nodes_db.py first")
    return StandardsNodesDatabase(db_path)


def test_resolve_pack_nodes_db_uses_compact_slug(project_root: Path) -> None:
    pack = project_root / "knowledge" / "standards" / "asme" / "asme_b31.3"
    assert resolve_pack_nodes_db(pack).name == "nodes.db"


def test_b313_nodes_db_contains_wall_thickness_node(b313_nodes_db: StandardsNodesDatabase) -> None:
    data = b313_nodes_db.get_node("304.1.1-a")
    assert data is not None
    assert data["kind"] == "node"
    assert data["metadata"]["type"] == "paragraph"
    assert "304.1.1" in str(data["metadata"].get("paragraph_number", ""))
    text = (data["metadata"].get("text") or {}).get("original", "")
    assert "t_m = t + c" in text
    assert "304.1.1-a.yaml" in data["source_rel_path"]


def test_b313_nodes_db_resolves_legacy_alias(b313_nodes_db: StandardsNodesDatabase) -> None:
    assert b313_nodes_db.get_node("304.1.1-a") is not None
    assert b313_nodes_db.get_node("304.1.1-b") is not None


def test_b313_nodes_db_has_equation_assets(b313_nodes_db: StandardsNodesDatabase) -> None:
    data = b313_nodes_db.get_node("304.1.1.eq.2")
    assert data is not None
    assert data["metadata"]["type"] == "equation"
    assert "t_m = t + c" in str(data["metadata"].get("display", ""))

    wall = b313_nodes_db.get_node("304.1.2.eq.3a")
    assert wall is not None
    assert wall["metadata"]["type"] == "equation"


def test_nodes_db_roundtrip_upsert(tmp_path: Path) -> None:
    db_path = tmp_path / "test_nodes.db"
    database = StandardsNodesDatabase(db_path)
    database.upsert_node(
        node_id="TEST-node",
        kind="node",
        metadata={"id": "TEST-node", "type": "definition"},
        body="Body text",
        source_rel_path="nodes/TEST-node",
        aliases=["nodes/TEST-node"],
    )
    database.upsert_asset(
        node_id="TEST-node",
        asset_type="equation",
        asset_id="eq1",
        relative_path="equations/eq1.md",
        metadata={"id": "eq1"},
        body="---\nid: eq1\n---\n",
    )
    loaded = database.get_node("TEST-node")
    assert loaded is not None
    assert loaded["body"] == "Body text"
    asset = database.get_asset_by_relative_path("TEST-node", "equations/eq1.md")
    assert asset is not None
    assert asset.asset_id == "eq1"
