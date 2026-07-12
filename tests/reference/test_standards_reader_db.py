"""Tests for DB-primary StandardsReader behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.pack_nodes_db import resolve_pack_nodes_db
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    db_path = resolve_pack_nodes_db(project_root / "knowledge" / "standards" / "asme" / "asme_b31.3")
    if not db_path.is_file():
        pytest.skip("Run scripts/build_standards_nodes_db.py first")
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_reader_loads_node_from_db(standards_reader: StandardsReader) -> None:
    assert standards_reader.nodes_db_available
    record = standards_reader.load("304.1.1-a")
    assert record.node_id == "304.1.1-a"
    assert record.metadata.get("type") == "paragraph"
    assert "t_m = t + c" in (record.metadata.get("text") or {}).get("original", "")
    assert record.path.as_posix().endswith("paragraph/304.1.1-a.yaml")


def test_reader_read_asset_text_from_db(standards_reader: StandardsReader) -> None:
    record = standards_reader.load("304.1.2.eq.3a")
    text = record.body
    assert text
    assert "PD" in text or "thickness" in text.lower()


def test_reader_validate_passes_for_wall_thickness(standards_reader: StandardsReader) -> None:
    result = standards_reader.validate("304.1.1-a")
    assert result.passed, [issue.message for issue in result.issues]


def test_reader_nested_table_note_path(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("asme-b313-table-302-3-3-1-note-1")
    assert path is not None
    assert "asme-b313-table-302-3-3-1-note-1" in path.as_posix()


def test_reader_nested_table_path(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("asme-b313-table-302-3-3-1")
    assert path is not None
    assert "asme-b313-table-302-3-3-1" in path.as_posix()
