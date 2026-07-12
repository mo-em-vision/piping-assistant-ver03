"""Tests for flat standards node path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_find_node_path_resolves_table_note(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("asme-b313-table-302-3-3-1-note-1")
    assert path is not None
    assert path.name == "asme-b313-table-302-3-3-1-note-1.yaml"


def test_find_node_path_resolves_flat_302_3_3_1_table(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("asme-b313-table-302-3-3-1")
    assert path is not None
    assert path.name == "asme-b313-table-302-3-3-1.yaml"


def test_find_node_path_resolves_flat_304_paragraph_node(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("304.1.2-a")
    assert path is not None
    assert path.name == "304.1.2-a.yaml"


def test_find_node_path_resolves_appendix_table_node(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("asme-b313-table-A-2")
    assert path is not None
    assert path.name == "asme-b313-table-A-2.yaml"


def test_find_node_path_resolves_table_304_1_1_1(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("asme-b313-table-304-1-1-1")
    assert path is not None
    assert path.name == "asme-b313-table-304-1-1-1.yaml"


def test_find_node_path_resolves_table_a1_allowable_stress(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("asme-b313-table-A-1")
    assert path is not None
    assert path.name == "asme-b313-table-A-1.yaml"
