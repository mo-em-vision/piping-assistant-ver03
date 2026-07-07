"""Tests for table citation metadata helpers."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_reader import StandardsReader
from engine.reference.table_metadata import (
    format_table_citation,
    table_citation_labels,
    table_reference,
)


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_table_reference_reads_authored_table_number() -> None:
    reader = _reader()
    record = reader.load("asme-b313-table-304-1-1-1")
    assert table_reference(record.metadata) == "304.1.1-1"


def test_table_citation_labels_resolve_from_lookup_node() -> None:
    reader = _reader()
    table_number, paragraph_number = table_citation_labels(reader, "table_304_1_1")
    assert table_number == "304.1.1-1"
    assert paragraph_number in (None, "304.1.1-b")


def test_format_table_citation_includes_paragraph_when_present() -> None:
    label = format_table_citation(
        standard_label="ASME B31.3",
        table_number="A-1",
        paragraph_number="302.3.5-d",
    )
    assert label == "ASME B31.3 Table A-1 (para. 302.3.5-d)"
