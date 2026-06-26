"""Tests for standards table source payloads."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.table_context import table_source_payload
from engine.reference.asme_b31_3_table_ids import TABLE_304_1_1, TABLE_A_1A, TABLE_A_1B
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "standards", standard="asme_b31.3")


def test_table_source_payload_for_appendix_a_1a(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "A-1A")

    assert payload["table_id"] == TABLE_A_1A
    assert "Table A-1A" in payload["title"]
    assert payload["columns"]
    assert payload["rows"]
    assert any(row.get("quality_factor_E") == 1.0 for row in payload["rows"])


def test_table_source_payload_accepts_file_stem_alias(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "A-1B")

    assert payload["table_id"] == TABLE_A_1B
    assert payload["rows"]


def test_table_source_payload_includes_all_row_columns_for_table_304_1_1(
    standards_reader: StandardsReader,
) -> None:
    payload = table_source_payload(standards_reader, "table_304_1_1")

    assert payload["table_id"] == TABLE_304_1_1
    column_keys = {column["key"] for column in payload["columns"]}
    assert "material" in column_keys
    assert "temperature_c" in column_keys
    assert "design_temperature" in column_keys
    assert "coefficient_Y" in column_keys
    assert len(payload["rows"]) >= 30
    assert any(row.get("coefficient_Y") is not None for row in payload["rows"])
    assert len({row.get("material") for row in payload["rows"]}) >= 5
