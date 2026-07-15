"""Tests for v2 lookup_rules validation."""

from __future__ import annotations

from pathlib import Path

from engine.validation.lookup_rule_validator import (
    validate_lookup_bindings,
    validate_lookup_config,
    validate_lookup_rule_spec,
)

_STANDARDS_ROOT = Path(__file__).resolve().parents[2] / "knowledge" / "standards"


def test_a1_rule_spec_is_valid_v2() -> None:
    from engine.executor.lookup_rule_schema import load_table_lookup_rules

    rules = load_table_lookup_rules("asme-b313-table-A-1", standards_root=_STANDARDS_ROOT)
    issues = validate_lookup_rule_spec("by_material_temperature", rules["by_material_temperature"])
    assert issues == []


def test_missing_strategy_is_rejected() -> None:
    issues = validate_lookup_rule_spec(
        "bad_rule",
        {
            "inputs": {
                "material_grade": {"resolver": "material_catalog"},
            },
            "outputs": {"allowable_stress": {"column": "allowable_stress", "parameter": "PARAM-allowable-stress"}},
            "on_no_match": {"action": "error"},
            "on_multiple_matches": {"action": "error"},
        },
    )
    assert any("strategy" in issue for issue in issues)


def test_bindings_must_cover_strategy_inputs() -> None:
    raw_rule = {
        "strategy": "material_temperature",
        "inputs": {
            "material_grade": {"resolver": "material_catalog"},
            "design_temperature": {
                "resolver": "identity",
                "column": "design_temperature",
                "parameter": "PARAM-design-temperature",
                "match": {
                    "method": "linear_interpolation",
                    "outside_range": "error",
                    "duplicate_rows": "error",
                    "missing_value": "error",
                },
            },
        },
        "outputs": {
            "allowable_stress": {"column": "allowable_stress", "parameter": "PARAM-allowable-stress"},
        },
        "on_no_match": {"action": "error"},
        "on_multiple_matches": {"action": "error"},
    }
    issues = validate_lookup_bindings(
        raw_rule,
        {"material_grade": "PARAM-material-grade"},
    )
    assert any("missing keys" in issue for issue in issues)


def test_lookup_config_rejects_lookup_keys() -> None:
    issues = validate_lookup_config(
        {
            "lookup": {
                "table": "asme-b313-table-A-1",
                "rule": "by_material_temperature",
                "keys": ["PARAM-material-grade"],
                "bindings": {
                    "material_grade": "PARAM-material-grade",
                    "design_temperature": "PARAM-design-temperature",
                },
            }
        },
        standards_root=_STANDARDS_ROOT,
    )
    assert any("lookup.keys is deprecated" in issue for issue in issues)


def test_lookup_config_requires_rule() -> None:
    issues = validate_lookup_config(
        {
            "lookup": {
                "table": "asme-b313-table-A-1",
                "bindings": {"material_grade": "PARAM-material-grade"},
            }
        }
    )
    assert any("lookup.rule is required" in issue for issue in issues)
