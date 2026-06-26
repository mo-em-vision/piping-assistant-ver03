"""Tests for standards table source payloads."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.table_context import table_source_payload
from engine.reference.asme_b31_3_table_ids import TABLE_302_3_3C, TABLE_304_1_1, TABLE_A_1A, TABLE_A_1B
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "standards", standard="asme_b31.3")


def test_table_source_payload_for_appendix_a_1a(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "A-1A")

    assert payload["table_id"] == TABLE_A_1A
    assert "Table A-1A" in payload["title"]
    assert payload["description"]
    assert "302.3.3(b)" in payload["description"]
    assert "node:B313-302.3.3/b" in payload["description"]
    assert "table:asme_b31.3_table_302_3_3C" in payload["description"]
    assert payload["columns"]
    assert payload["rows"]
    assert all(row.get("base_metal_group") == "Stainless Steel" for row in payload["rows"])
    assert any(row.get("quality_factor_E_c") == 0.8 for row in payload["rows"])


def test_table_source_payload_for_table_302_3_3c(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "302.3.3C")

    assert payload["table_id"] == TABLE_302_3_3C
    assert "Increased Casting Quality Factors" in payload["title"]
    assert payload["description"]
    assert "node:B313-note-302-3-3C-1" in payload["description"]
    assert len(payload["rows"]) == 6

    factors = sorted(row.get("quality_factor_E_c") for row in payload["rows"])
    assert factors == [0.85, 0.85, 0.9, 0.95, 1.0, 1.0]

    first_row = next(row for row in payload["rows"] if row.get("row_id") == "note_1_only")
    assert "node:B313-note-302-3-3C-1" in str(first_row.get("supplementary_examination", ""))

    column_keys = {column["key"] for column in payload["columns"]}
    assert "supplementary_examination" in column_keys
    assert "quality_factor_E_c" in column_keys
    assert "row_id" in column_keys


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
