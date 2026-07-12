"""Tests for standards table source payloads."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.table_context import table_source_payload
from engine.reference.asme_b31_3_table_ids import TABLE_302_3_3_1, TABLE_302_3_3_2, TABLE_304_1_1, TABLE_A_2, TABLE_A_3, TABLE_A_1A, TABLE_A_1B
from engine.reference.standards_reader import StandardsReader
from engine.reference.standards_tables import flatten_lookup_table_rows


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_table_source_payload_for_appendix_a_1a(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "A-1A")

    assert payload["table_id"] == TABLE_A_2
    assert "Table A-2" in payload["title"]
    assert payload["description"]
    assert "302.3.3-b" in payload["description"]
    assert "node:302.3.3-a-b" in payload["description"]
    assert "table:asme_b31.3_302.3.3-1" in payload["description"]
    assert payload["columns"]
    assert payload["rows"]
    assert all(row.get("base_metal_group") == "Stainless Steel" for row in payload["rows"])
    assert any(row.get("quality_factor_E_c") == 0.8 for row in payload["rows"])


def test_table_source_payload_for_table_302_3_3_1(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "302.3.3-1")

    assert payload["table_id"] == TABLE_302_3_3_1
    assert "Increased Casting Quality Factors" in payload["title"]
    assert payload["description"]
    assert (
        "node:asme-b313-table-302-3-3-1-note-1" in payload["description"]
        or "node:asme-b313-note-302-3-3C-1" in payload["description"]
    )
    assert payload["rows"] == []

    column_keys = {column["key"] for column in payload["columns"]}
    assert "supplementary_examination" in column_keys


def test_table_source_payload_for_table_302_3_3_2(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "302.3.3-2")

    assert payload["table_id"] == TABLE_302_3_3_2
    assert "Acceptance Levels for Castings" in payload["title"]
    assert payload["description"]
    assert payload["rows"] == []

    column_keys = {column["key"] for column in payload["columns"]}
    assert "material_examined_thickness_T" in column_keys
    assert "applicable_standard" in column_keys
    assert "acceptance_level_or_class" in column_keys
    assert "acceptable_discontinuities" in column_keys


def test_table_source_payload_accepts_legacy_302_3_3c_alias(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "302.3.3C")

    assert payload["table_id"] == TABLE_302_3_3_1
    assert "Increased Casting Quality Factors" in payload["title"]


def test_table_source_payload_accepts_file_stem_alias(standards_reader: StandardsReader) -> None:
    payload = table_source_payload(standards_reader, "A-1B")

    assert payload["table_id"] == TABLE_A_3
    assert TABLE_A_1B == TABLE_A_3
    assert "Table A-3" in payload["title"]
    assert payload["rows"]


def test_table_source_payload_includes_all_row_columns_for_table_304_1_1(
    standards_reader: StandardsReader,
) -> None:
    payload = table_source_payload(standards_reader, "table_304_1_1")
    _, raw_data = standards_reader.load_table_by_id("table_304_1_1")
    raw_rows = flatten_lookup_table_rows(raw_data)

    assert payload["table_id"] == TABLE_304_1_1
    column_keys = {column["key"] for column in payload["columns"]}
    assert "material" in column_keys
    assert "temperature_c" in column_keys
    assert "design_temperature" in column_keys
    assert "coefficient_Y" in column_keys
    assert len(payload["rows"]) >= 30
    assert any(row.get("coefficient_Y") is not None for row in payload["rows"])
    assert len({row.get("material") for row in payload["rows"]}) >= 5
    assert not any("temperature_c" in row for row in raw_rows)

    ferritic_900 = next(
        row
        for row in payload["rows"]
        if row.get("material_id") == "ferritic_steels" and row.get("design_temperature") == 900
    )
    assert abs(float(ferritic_900["temperature_c"]) - 482.22222222222223) < 1e-6


def test_table_source_payload_includes_revision_year_from_source_node(
    standards_reader: StandardsReader,
) -> None:
    payload = table_source_payload(standards_reader, TABLE_304_1_1)

    assert payload["revision_year"] == 2024
    assert payload["table_number"] == "304.1.1-1"
    assert payload["paragraph_number"] is None
