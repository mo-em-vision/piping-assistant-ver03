"""Tests for shared material name resolution across standards tables."""

from __future__ import annotations

from engine.reference.material_ids import ASTM_A106_GR_B
from engine.reference.material_resolver import resolve_material_table_key

_STRESS_MATERIALS = {
    ASTM_A106_GR_B: {
        "display_name": "ASTM A106 Grade B",
        "rows": [{"design_temperature": 200, "allowable_stress": 193_000_000}],
    },
}


def test_resolve_catalog_grade_name_to_stress_table_key() -> None:
    assert resolve_material_table_key(_STRESS_MATERIALS, "A106 Gr B") == ASTM_A106_GR_B
    assert resolve_material_table_key(_STRESS_MATERIALS, "SA-106B") == ASTM_A106_GR_B
    assert resolve_material_table_key(_STRESS_MATERIALS, ASTM_A106_GR_B) == ASTM_A106_GR_B


def test_resolve_unknown_material_returns_none() -> None:
    assert resolve_material_table_key(_STRESS_MATERIALS, "Unknown Alloy") is None
