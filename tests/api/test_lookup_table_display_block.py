"""Generic lookup table blocks from execution trace payloads."""

from __future__ import annotations

from api.output_blocks import _lookup_table_block


def test_lookup_table_block_from_b36_10_shaped_trace() -> None:
    lookup = {
        "table_id": "B3610-table-2-1",
        "title": "ASME B36.10M pipe schedules for NPS 2",
        "rows": [
            {"schedule": "10", "wall_thickness_mm": 3.404},
            {"schedule": "40", "wall_thickness_mm": 5.54},
        ],
        "highlight": {"column": "schedule", "value": "10"},
        "recommendation_summary": "For NPS 2, Schedule 10 is the lightest standard schedule.",
    }

    block = _lookup_table_block("B3610-table-2-1", lookup)
    assert block is not None
    assert block["id"] == "table-lookup-B3610-table-2-1"
    assert block["type"] == "table"
    assert block.get("highlight_row") == {"column": "schedule", "value": "10"}
    assert block.get("summary_text") == lookup["recommendation_summary"]
    assert len(block.get("rows") or []) == 2
