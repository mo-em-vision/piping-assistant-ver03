"""Tests for flat standards node path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "standards", standard="asme_b31.3")


def test_find_node_path_resolves_flat_302_3_3c_note(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("B313-note-302-3-3C-1")
    assert path is not None
    assert any(path.as_posix().endswith(suffix) for suffix in ("B313-note-302-3-3C-1/node.md", "B313-note-302-3-3C-1/node.yaml"))


def test_find_node_path_resolves_flat_304_paragraph_node(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("B313-304.1.2")
    assert path is not None
    assert path.as_posix().endswith("B313-304.1.2/node.yaml")


def test_find_node_path_resolves_appendix_table_node(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("B313-table-A-1A")
    assert path is not None
    assert path.name in {"node.md", "node.yaml"}


def test_find_node_path_resolves_table_304_1_1(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("B313-table-304-1-1")
    assert path is not None
    assert path.name in {"node.md", "node.yaml"}


def test_find_node_path_resolves_table_a1_allowable_stress(standards_reader: StandardsReader) -> None:
    path = standards_reader.find_node_path("B313-table-A-1")
    assert path is not None
    assert path.name in {"node.md", "node.yaml"}
