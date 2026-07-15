"""Temperature and row matching with explicit lookup_rules policies."""

from __future__ import annotations

from typing import Any

from engine.executor.lookup_rule_schema import MatchPolicy
from engine.reference.coefficient_resolver import interpolate_by_temperature


def _temp_column(column: str | None) -> str:
    return column or "design_temperature"


def match_column_value(
    rows: list[dict[str, Any]],
    *,
    query_value: float,
    value_column: str,
    temp_column: str,
    match: MatchPolicy | None,
) -> tuple[float, dict[str, Any] | None, bool]:
    if not rows:
        raise ValueError("No rows available for column lookup")

    policy = match or MatchPolicy(
        method="exact",
        outside_range="error",
        duplicate_rows="error",
        missing_value="error",
    )

    for row in rows:
        if policy.missing_value == "error" and row.get(value_column) is None:
            raise ValueError(f"Missing value in column {value_column!r}")

    sorted_rows = sorted(rows, key=lambda r: float(r[temp_column]))
    temps = [float(r[temp_column]) for r in sorted_rows]
    min_temp = min(temps)
    max_temp = max(temps)

    exact_matches = [r for r in sorted_rows if float(r[temp_column]) == float(query_value)]
    if len(exact_matches) > 1:
        if policy.duplicate_rows == "error":
            raise ValueError(f"Duplicate rows at temperature {query_value}")
        exact_matches = exact_matches[:1]
    if exact_matches:
        row = exact_matches[0]
        return float(row[value_column]), row, False

    if policy.method == "exact":
        if policy.outside_range == "error":
            raise ValueError(
                f"No exact match for {temp_column}={query_value} "
                f"(table range {min_temp}..{max_temp})"
            )
        closest = min(sorted_rows, key=lambda r: abs(float(r[temp_column]) - query_value))
        return float(closest[value_column]), closest, False

    if policy.method == "linear_interpolation":
        if query_value < min_temp or query_value > max_temp:
            if policy.outside_range == "error":
                raise ValueError(
                    f"Temperature {query_value} outside table range {min_temp}..{max_temp}"
                )
        interpolate = True
        value, matched_row, interpolated = interpolate_by_temperature(
            sorted_rows,
            temperature_f=float(query_value),
            value_key=value_column,
            interpolate=interpolate,
        )
        if not interpolated and policy.outside_range == "error":
            if float(query_value) < min_temp or float(query_value) > max_temp:
                raise ValueError(
                    f"Temperature {query_value} outside table range {min_temp}..{max_temp}"
                )
        return float(value), matched_row, interpolated

    raise ValueError(f"Unsupported match method: {policy.method!r}")
