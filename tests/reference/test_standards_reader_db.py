"""Tests for DB-primary StandardsReader behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.pack_nodes_db import resolve_pack_nodes_db
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    db_path = resolve_pack_nodes_db(project_root / "standards" / "asme" / "asme_b31.3")
    if not db_path.is_file():
        pytest.skip("Run scripts/build_standards_nodes_db.py first")
    return StandardsReader(project_root / "standards", standard="asme_b31.3")


def test_reader_loads_node_from_db(standards_reader: StandardsReader) -> None:
    assert standards_reader.nodes_db_available
    record = standards_reader.load("B313-304.1.1")
    assert record.node_id == "B313-304.1.1"
    assert record.metadata.get("type") == "definition"
    assert record.body.strip()
    assert record.path.as_posix().endswith("304/304.1.1/node.md")


def test_reader_read_asset_text_from_db(standards_reader: StandardsReader) -> None:
    record = standards_reader.load("B313-304.1.2")
    text = standards_reader.read_asset_text(record, "equations/wall_thickness.md")
    assert text
    assert "PD" in text or "thickness" in text.lower()


def test_reader_validate_passes_for_wall_thickness(standards_reader: StandardsReader) -> None:
    result = standards_reader.validate("B313-304.1.1")
    assert result.passed, [issue.message for issue in result.issues]


def test_reader_nested_note_path(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("B313-note-302-3-3C-1")
    assert path is not None
    assert "302/302.3.3/tables/B313-note-302-3-3C-1" in path.as_posix()
