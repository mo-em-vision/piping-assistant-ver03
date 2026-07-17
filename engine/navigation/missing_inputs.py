"""Aggregate missing input ids from planning projections."""

from __future__ import annotations

from typing import Any


def collect_all_missing(planning: dict[str, Any]) -> set[str]:
    all_missing: set[str] = set()
    for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
        all_missing.update(str(item) for item in (planning.get(key) or []))
    phase_missing = planning.get("phase_missing") or {}
    if isinstance(phase_missing, dict):
        for fields in phase_missing.values():
            if isinstance(fields, list):
                all_missing.update(str(item) for item in fields)
    return all_missing
