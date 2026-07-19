"""Validate table definition YAML (lookup_rules and row_resolution)."""

from __future__ import annotations

from typing import Any

from engine.validation.lookup_rule_validator import validate_lookup_rule_spec


def validate_table_definition(data: dict[str, Any]) -> list[str]:
    """Validate a table definition document containing lookup_rules."""
    issues: list[str] = []
    rules = data.get("lookup_rules")
    if not isinstance(rules, dict) or not rules:
        issues.append("table definition requires lookup_rules block")
        return issues

    for rule_name, raw_rule in rules.items():
        if not isinstance(raw_rule, dict):
            issues.append(f"lookup_rules.{rule_name} must be a mapping")
            continue
        issues.extend(validate_lookup_rule_spec(str(rule_name), raw_rule))
    return issues
