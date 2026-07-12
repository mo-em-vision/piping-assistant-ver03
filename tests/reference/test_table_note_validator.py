"""Tests for table-note node validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_markdown import split_frontmatter
from engine.validation.table_note_node_validator import validate_table_note_node


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_table_note(name: str) -> dict:
    path = (
        _project_root()
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "tables"
        / name
    )
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    return meta


def test_table_note_nodes_pass_validator() -> None:
    for name in (
        "asme-b313-table-302-3-3-1-note-1.yaml",
        "asme-b313-table-302-3-3-1-note-2a.yaml",
        "asme-b313-table-302-3-3-1-note-2b.yaml",
        "asme-b313-table-302-3-3-1-note-3a.yaml",
        "asme-b313-table-302-3-3-1-note-3b.yaml",
    ):
        issues = validate_table_note_node(_load_table_note(name))
        assert issues == [], f"{name}: {issues}"


def test_table_note_validator_requires_text_and_table_link() -> None:
    issues = validate_table_note_node(
        {
            "id": "asme-b313-table-302-3-3-1-note-1",
            "type": "table_note",
            "note_code": "1",
            "title": "Example",
            "metadata": {"last_revision": "2026-07-12", "edited_by": "admin"},
            "edges": [],
        }
    )
    assert "missing text" in issues
    assert "table_note requires note_for_table edge to parent table" in issues


def test_table_note_rejects_related_to_parent_table() -> None:
    issues = validate_table_note_node(
        {
            "id": "asme-b313-table-302-3-3-1-note-1",
            "type": "table_note",
            "note_code": "1",
            "title": "Example",
            "text": "Example note.",
            "metadata": {"last_revision": "2026-07-12", "edited_by": "admin"},
            "edges": [
                {"type": "related_to", "target": "asme-b313-table-302-3-3-1"},
            ],
        }
    )
    assert "use note_for_table for parent table" in " ".join(issues)


def test_table_note_allows_additional_related_to_edges() -> None:
    issues = validate_table_note_node(
        {
            "id": "asme-b313-table-302-3-3-1-note-1",
            "type": "table_note",
            "note_code": "1",
            "title": "Example",
            "text": "See also para. 302.3.3-c.",
            "metadata": {"last_revision": "2026-07-12", "edited_by": "admin"},
            "edges": [
                {"type": "note_for_table", "target": "asme-b313-table-302-3-3-1"},
                {"type": "related_to", "target": "302.3.3-c"},
            ],
        }
    )
    assert issues == []


def test_lookup_validator_requires_has_table_note_edges_for_table_notes() -> None:
    from engine.validation.lookup_node_validator import validate_lookup_node

    issues = validate_lookup_node(
        {
            "id": "asme-b313-table-example",
            "type": "lookup",
            "title": "Example",
            "table_number": "999-9",
            "lookup": {"table": "asme-b313-table-example"},
            "returns": [{"parameter": "PARAM-basic-casting-quality-factor"}],
            "notes": [{"id": "note_1", "node_id": "asme-b313-table-example-note-1"}],
            "edges": [
                {"type": "returns_parameter", "target": "PARAM-basic-casting-quality-factor"},
            ],
            "metadata": {"last_revision": "2026-07-12", "edited_by": "admin"},
        }
    )
    assert "missing has_table_note edge to table note: asme-b313-table-example-note-1" in issues


def test_lookup_validator_rejects_related_to_for_table_notes() -> None:
    from engine.validation.lookup_node_validator import validate_lookup_node

    issues = validate_lookup_node(
        {
            "id": "asme-b313-table-example",
            "type": "lookup",
            "title": "Example",
            "table_number": "999-9",
            "lookup": {"table": "asme-b313-table-example"},
            "returns": [{"parameter": "PARAM-basic-casting-quality-factor"}],
            "notes": [{"id": "note_1", "node_id": "asme-b313-table-example-note-1"}],
            "edges": [
                {"type": "returns_parameter", "target": "PARAM-basic-casting-quality-factor"},
                {"type": "related_to", "target": "asme-b313-table-example-note-1"},
            ],
            "metadata": {"last_revision": "2026-07-12", "edited_by": "admin"},
        }
    )
    assert "use has_table_note for table note asme-b313-table-example-note-1" in " ".join(issues)
