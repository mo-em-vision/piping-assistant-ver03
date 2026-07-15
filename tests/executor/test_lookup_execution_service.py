"""Tests for shared lookup execution service and table registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.lookup_execution_service import execute_lookup_rule
from engine.executor.table_registry import GRAPH_NODE_TABLE_IDS, resolve_graph_node_table_id
from engine.reference.standards_paths import resolve_standard_pack


def test_table_registry_resolves_graph_node_ids() -> None:
    assert resolve_graph_node_table_id("asme-b313-table-A-1") == GRAPH_NODE_TABLE_IDS[
        "asme-b313-table-A-1"
    ]


def test_execute_lookup_rule_allowable_stress() -> None:
    root = Path(__file__).resolve().parents[2]
    pack_root = resolve_standard_pack(root / "knowledge" / "standards", "asme_b31.3")
    try:
        result = execute_lookup_rule(
            pack_root=pack_root,
            table_ref="asme-b313-table-A-1",
            rule="by_material_temperature",
            inputs={
                "material_grade": "SA-106B",
                "design_temperature": 100.0,
                "design_temperature_unit": "F",
            },
        )
    except FileNotFoundError:
        pytest.skip("standards tables db must be built")

    assert "allowable_stress" in result.outputs
    assert float(result.outputs["allowable_stress"]) > 0
