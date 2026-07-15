"""Canonical graph-node table id aliases shared across lookup executors."""

from __future__ import annotations

from engine.reference.asme_b31_3_table_ids import (
    TABLE_302_3_5_1,
    TABLE_304_1_1_1,
    TABLE_A_1,
    TABLE_A_2,
    TABLE_A_3,
)

GRAPH_NODE_TABLE_IDS: dict[str, str] = {
    "asme-b313-table-A-1": TABLE_A_1,
    "asme-b313-table-A-2": TABLE_A_2,
    "asme-b313-table-A-3": TABLE_A_3,
    "asme-b313-table-304-1-1-1": TABLE_304_1_1_1,
    "asme-b313-table-302-3-5-1": TABLE_302_3_5_1,
}


def resolve_graph_node_table_id(table_ref: str) -> str:
    """Map a graph node table id or alias to a canonical pack table id."""
    wanted = str(table_ref or "").strip()
    if not wanted:
        return wanted
    return GRAPH_NODE_TABLE_IDS.get(wanted, wanted)
