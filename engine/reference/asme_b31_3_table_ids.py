"""Canonical lookup table IDs for the ASME B31.3 standards pack."""

from __future__ import annotations

ASME_B31_3_PACK_SLUG = "asme_b31.3"
ASME_B31_3_TABLE_ID_PREFIX = f"{ASME_B31_3_PACK_SLUG}_"


def asme_b31_3_table_id(local_id: str) -> str:
    """Return the pack-scoped table id for a local table identifier."""
    return f"{ASME_B31_3_TABLE_ID_PREFIX}{local_id}"


def local_table_id(table_id: str) -> str:
    """Strip the ASME B31.3 pack prefix when present."""
    if table_id.startswith(ASME_B31_3_TABLE_ID_PREFIX):
        return table_id[len(ASME_B31_3_TABLE_ID_PREFIX) :]
    return table_id


TABLE_A_1 = asme_b31_3_table_id("A-1")
TABLE_A_1A = asme_b31_3_table_id("A-1A")
TABLE_A_1B = asme_b31_3_table_id("A-1B")
TABLE_304_1_1 = asme_b31_3_table_id("table_304_1_1")
TABLE_302_3_5 = asme_b31_3_table_id("302.3.5")
TABLE_302_3_3C = asme_b31_3_table_id("table_302_3_3C")
# Legacy alias; canonical id is TABLE_A_1.
TABLE_MATERIAL_ALLOWABLE_STRESS = TABLE_A_1
