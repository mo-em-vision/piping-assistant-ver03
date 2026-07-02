"""Validate runtime Fact nodes against the Fact Node template."""

from __future__ import annotations

from typing import Any

from models.fact import (
    Fact,
    FactClass,
    NumericValue,
    ValidationStatus,
)

_FORBIDDEN_FIELDS = frozenset(
    {
        "concept_definition",
        "dimension_definition",
        "unit_conversion_rule",
        "parameter_aliases",
        "equation_formula",
        "standard_text",
        "workflow_definition",
    }
)

_DERIVED_CLASSES = frozenset(
    {
        FactClass.CALCULATED,
        FactClass.DERIVED,
        FactClass.LOOKED_UP,
    }
)


def validate_fact(fact: Fact) -> list[str]:
    """Return validation issue messages for a fact (empty if valid)."""
    issues: list[str] = []
    if fact.type != "fact":
        issues.append("type must be 'fact'")
    if not fact.id:
        issues.append("missing id")
    if not fact.parameter:
        issues.append("missing parameter")
    elif not str(fact.parameter).startswith("PARAM-"):
        issues.append(f"parameter must reference PARAM-* node, got {fact.parameter!r}")
    if not fact.key:
        issues.append("missing key")
    if not fact.fact_class:
        issues.append("missing fact_class")
    if fact.source is None or not fact.source.source_id:
        issues.append("missing source.source_id")
    if fact.provenance is None:
        issues.append("missing provenance")

    if isinstance(fact.value, NumericValue):
        if fact.canonical_value is None and fact.validation.status in {
            ValidationStatus.CONFIRMED,
            ValidationStatus.VALIDATED,
        }:
            issues.append("numeric fact should have canonical_value when confirmed")
    elif fact.value is None and fact.validation.status not in {
        ValidationStatus.PENDING,
        ValidationStatus.SUPERSEDED,
    }:
        if fact.fact_class != FactClass.SYSTEM_GENERATED:
            issues.append("missing value")

    if fact.fact_class in _DERIVED_CLASSES and not fact.source.input_facts:
        if fact.fact_class == FactClass.LOOKED_UP and not fact.source.lookup_node:
            issues.append("looked_up fact should record lookup_node or input_facts")

    for field in _FORBIDDEN_FIELDS:
        if field in (fact.metadata or {}):
            issues.append(f"forbidden metadata field: {field}")

    return issues


def validate_fact_dict(data: dict[str, Any]) -> list[str]:
    from models.fact import fact_from_dict

    return validate_fact(fact_from_dict(data))
