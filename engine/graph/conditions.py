"""Shared graph condition helpers."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value, normalize_assumption_value
from models.fact import Fact


class GraphCycleError(ValueError):
    """Raised when a dependency cycle is detected."""


def when_clause_matches(
    when: dict[str, Any] | None,
    inputs: dict[str, Fact],
) -> bool:
    """Return True when a conditional edge should be active."""
    if not when:
        return True
    field_name = str(when.get("field", ""))
    if not field_name:
        return True
    value = field_value(field_name, inputs)
    if when.get("present"):
        return value is not None
    if when.get("absent"):
        return value is None
    allowed = when.get("in") or []
    if value is None:
        return False
    normalized_allowed = {normalize_assumption_value(v) for v in allowed}
    return value in normalized_allowed
