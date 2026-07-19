"""Tests for lookup node and table definition validators."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.validation.lookup_node_validator import validate_lookup_node
from engine.validation.lookup_rule_validator import validate_lookup_rule_spec
from engine.validation.table_definition_validator import validate_table_definition

_STANDARDS_ROOT = Path(__file__).resolve().parents[2] / "knowledge" / "standards"


def test_a1_rule_spec_is_valid_v2() -> None:
    from engine.executor.lookup_rule_schema import load_table_lookup_rules

    rules = load_table_lookup_rules("asme-b313-table-A-1", standards_root=_STANDARDS_ROOT)
    issues = validate_lookup_rule_spec("by_material_temperature", rules["by_material_temperature"])
    assert issues == []


def test_validator_rejects_match_block_on_input() -> None:
    issues = validate_lookup_rule_spec(
        "bad_rule",
        {
            "strategy": "material_temperature",
            "row_resolution": {
                "design_temperature": {
                    "breakpoint_column": "design_temperature",
                    "method": "linear_interpolation",
                    "interpolate_columns": ["allowable_stress"],
                }
            },
            "inputs": {
                "material_grade": {"resolver": "material_catalog"},
                "design_temperature": {
                    "resolver": "identity",
                    "column": "design_temperature",
                    "match": {"method": "linear_interpolation"},
                },
            },
            "outputs": {
                "allowable_stress": {"column": "allowable_stress", "parameter": "PARAM-allowable-stress"},
            },
            "on_no_match": {"action": "error"},
            "on_multiple_matches": {"action": "error"},
        },
    )
    assert any("match block" in issue for issue in issues)


def test_validator_rejects_mixed_column_forms() -> None:
    issues = validate_lookup_rule_spec(
        "bad_rule",
        {
            "strategy": "material_temperature",
            "row_resolution": {
                "design_temperature": {
                    "breakpoint_column": "design_temperature",
                    "method": "linear_interpolation",
                    "interpolate_columns": ["allowable_stress"],
                    "output_columns": {
                        "allowable_stress": {"method": "linear_interpolation"},
                    },
                }
            },
            "inputs": {
                "material_grade": {"resolver": "material_catalog"},
                "design_temperature": {"resolver": "identity", "column": "design_temperature"},
            },
            "outputs": {
                "allowable_stress": {"column": "allowable_stress", "parameter": "PARAM-allowable-stress"},
            },
            "on_no_match": {"action": "error"},
            "on_multiple_matches": {"action": "error"},
        },
    )
    assert any("not both" in issue for issue in issues)


def test_lookup_node_validator_rejects_lookup_rules_on_node() -> None:
    issues = validate_lookup_node(
        {
            "type": "lookup",
            "key": "test",
            "name": "Test",
            "description": "Test",
            "table_number": "A-1",
            "lookup": {
                "table": "asme-b313-table-A-1",
                "rule": "by_material_temperature",
                "bindings": {
                    "material_grade": "PARAM-material-grade",
                    "design_temperature": "PARAM-design-temperature",
                },
            },
            "lookup_rules": {"by_material_temperature": {"strategy": "material_temperature"}},
            "returns": [{"parameter": "PARAM-allowable-stress"}],
            "metadata": {"last_revision": "2026-01-01", "edited_by": "test"},
        }
    )
    assert any("lookup_rules" in issue for issue in issues)


def test_table_definition_validator_accepts_a1() -> None:
    from engine.executor.lookup_rule_schema import load_table_lookup_rules

    rules = load_table_lookup_rules("asme-b313-table-A-1", standards_root=_STANDARDS_ROOT)
    issues = validate_table_definition({"lookup_rules": rules})
    assert issues == []


def test_temperature_strategy_requires_row_resolution() -> None:
    issues = validate_lookup_rule_spec(
        "bad_rule",
        {
            "strategy": "material_temperature",
            "inputs": {
                "material_grade": {"resolver": "material_catalog"},
                "design_temperature": {"resolver": "identity", "column": "design_temperature"},
            },
            "outputs": {
                "allowable_stress": {"column": "allowable_stress", "parameter": "PARAM-allowable-stress"},
            },
            "on_no_match": {"action": "error"},
            "on_multiple_matches": {"action": "error"},
        },
    )
    assert any("row_resolution.design_temperature" in issue for issue in issues)
