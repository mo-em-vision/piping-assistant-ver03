"""Tests for standards table source payloads."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.table_context import table_source_payload
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "standards", standard="asme_b31.3")


def test_table_source_payload_for_appendix_a_1a(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "A-1A")

    assert payload["table_id"] == "A-1A"
    assert "Table A-1A" in payload["title"]
    assert payload["columns"]
    assert payload["rows"]
    assert any(row.get("quality_factor_E") == 1.0 for row in payload["rows"])


def test_table_source_payload_accepts_file_stem_alias(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "A-1B")

    assert payload["table_id"]
    assert payload["rows"]
