"""Tests for standards retrieval used by task chat."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.standards_retrieval import retrieve_standards_context
from engine.reference.asme_b31_3_table_ids import TABLE_304_1_1
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def standards_root() -> Path:
    return Path(__file__).resolve().parents[2] / "standards"


@pytest.fixture
def reader(standards_root: Path) -> StandardsReader:
    return StandardsReader(standards_root)


def test_retrieve_y_coefficient_question_finds_table_304_1_1(reader: StandardsReader) -> None:
    result = retrieve_standards_context(
        "What are the typical values for the Y coefficient?",
        reader=reader,
    )

    table_ids = {source.table_id for source in result.sources if source.table_id}
    assert TABLE_304_1_1 in table_ids
    assert result.context_block
    assert "304.1.1" in result.context_block or TABLE_304_1_1 in result.context_block


def test_retrieve_includes_lookup_result_when_design_temperature_present(
    reader: StandardsReader,
) -> None:
    task_state_payload = {
        "inputs": {
            "design_temperature": {
                "value": 400.0,
                "unit": "F",
            }
        }
    }
    result = retrieve_standards_context(
        "What is Y at my design temperature?",
        reader=reader,
        task_state_payload=task_state_payload,
    )

    lookup_sources = [source for source in result.sources if source.kind == "lookup_result"]
    assert lookup_sources
    assert "Y =" in lookup_sources[0].label


def test_retrieve_returns_empty_for_blank_query(reader: StandardsReader) -> None:
    result = retrieve_standards_context("   ", reader=reader)
    assert result.sources == []
    assert result.context_block == ""
