"""Generic table row resolution with multi-column interpolation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OutputColumnPolicy:
    method: str
    unit: str | None = None


@dataclass(frozen=True)
class RowResolutionPolicy:
    breakpoint_column: str
    unit: str | None = None
    method: str = "exact"
    outside_range: str = "error"
    duplicate_breakpoints: str = "error"
    missing_value: str = "error"
    min_bound: float | None = None
    max_bound: float | None = None
    interpolate_columns: tuple[str, ...] = ()
    output_columns: dict[str, OutputColumnPolicy] = field(default_factory=dict)


@dataclass(frozen=True)
class ColumnProvenance:
    source_column: str
    source_values: dict[str, float]
    lower_source_row: dict[str, Any] | None
    upper_source_row: dict[str, Any] | None
    interpolation_fraction: float | None
    unit: str | None
    resolution_method: str
    interpolated: bool


@dataclass(frozen=True)
class TableRowsResolutionResult:
    values: dict[str, float]
    column_provenance: dict[str, ColumnProvenance]
    interpolation_fraction: float | None
    lower_source_row: dict[str, Any] | None
    upper_source_row: dict[str, Any] | None
    matched_row: dict[str, Any] | None
    interpolated: bool
    breakpoint_column: str
    query_value: float


def linear_interpolate_value(v0: float, v1: float, fraction: float) -> float:
    """Scalar linear interpolation between two values."""
    return v0 + fraction * (v1 - v0)


def _breakpoint_value(row: dict[str, Any], column: str) -> float:
    raw = row.get(column)
    if raw is None:
        raise ValueError(f"Missing breakpoint value in column {column!r}")
    return float(raw)


def _apply_outside_range(
    query_value: float,
    *,
    min_bp: float,
    max_bp: float,
    policy: RowResolutionPolicy,
) -> tuple[float, str]:
    """Return adjusted query and resolution mode hint for outside-range handling."""
    effective_min = float(policy.min_bound) if policy.min_bound is not None else min_bp
    effective_max = float(policy.max_bound) if policy.max_bound is not None else max_bp

    if effective_min <= query_value <= effective_max:
        return query_value, "in_range"

    if policy.outside_range == "error":
        raise ValueError(
            f"Query {query_value} outside permitted range {effective_min}..{effective_max}"
        )
    if policy.outside_range == "clamp_to_boundary":
        return max(effective_min, min(query_value, effective_max)), "in_range"
    if policy.outside_range == "lower_bound":
        return query_value, "lower_bound"
    if policy.outside_range == "upper_bound":
        return query_value, "upper_bound"

    raise ValueError(f"Unsupported outside_range policy: {policy.outside_range!r}")


def _find_bracketing(
    sorted_rows: list[dict[str, Any]],
    *,
    breakpoint_column: str,
    query_value: float,
    policy: RowResolutionPolicy,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, float | None, bool]:
    """Find bracketing rows and interpolation fraction once."""
    exact_matches = [
        r for r in sorted_rows if _breakpoint_value(r, breakpoint_column) == float(query_value)
    ]
    if len(exact_matches) > 1:
        if policy.duplicate_breakpoints == "error":
            raise ValueError(f"Duplicate breakpoints at {breakpoint_column}={query_value}")
        exact_matches = exact_matches[:1]
    if exact_matches:
        row = exact_matches[0]
        return row, row, None, False

    below: dict[str, Any] | None = None
    above: dict[str, Any] | None = None
    for row in sorted_rows:
        bp = _breakpoint_value(row, breakpoint_column)
        if bp <= query_value:
            below = row
        if bp >= query_value and above is None:
            above = row

    if below is None and above is not None:
        return above, above, None, False
    if above is None and below is not None:
        return below, below, None, False
    if below is None or above is None:
        raise ValueError(f"No bracketing rows for {breakpoint_column}={query_value}")

    t0 = _breakpoint_value(below, breakpoint_column)
    t1 = _breakpoint_value(above, breakpoint_column)
    if t0 == t1:
        return below, below, None, False

    fraction = (float(query_value) - t0) / (t1 - t0)
    return below, above, fraction, True


def resolve_table_rows(
    rows: list[dict[str, Any]],
    *,
    breakpoint_column: str,
    output_columns: dict[str, OutputColumnPolicy],
    query_value: float,
    policy: RowResolutionPolicy,
    unit_context: dict[str, Any] | None = None,
) -> TableRowsResolutionResult:
    """Resolve multiple output columns in one bracketing pass."""
    if not rows:
        raise ValueError("No rows available for table resolution")

    _ = unit_context  # reserved for per-column unit conversion hooks

    if policy.missing_value == "error":
        for col_name, col_policy in output_columns.items():
            if col_policy.method != "linear_interpolation":
                continue
            for row in rows:
                if row.get(col_name) is None:
                    raise ValueError(f"Missing value in column {col_name!r}")

    sorted_rows = sorted(rows, key=lambda r: _breakpoint_value(r, breakpoint_column))
    breakpoints = [_breakpoint_value(r, breakpoint_column) for r in sorted_rows]
    if len(breakpoints) != len(set(breakpoints)) and policy.duplicate_breakpoints == "error":
        raise ValueError(f"Duplicate breakpoints in column {breakpoint_column!r}")

    min_bp = min(breakpoints)
    max_bp = max(breakpoints)
    adjusted_query, range_mode = _apply_outside_range(
        float(query_value),
        min_bp=min_bp,
        max_bp=max_bp,
        policy=policy,
    )

    lower_row: dict[str, Any] | None = None
    upper_row: dict[str, Any] | None = None
    fraction: float | None = None
    any_interpolated = False

    if range_mode == "lower_bound":
        lower_row = sorted_rows[0]
        upper_row = lower_row
    elif range_mode == "upper_bound":
        lower_row = sorted_rows[-1]
        upper_row = lower_row
    else:
        lower_row, upper_row, fraction, any_interpolated = _find_bracketing(
            sorted_rows,
            breakpoint_column=breakpoint_column,
            query_value=adjusted_query,
            policy=policy,
        )

    values: dict[str, float] = {}
    column_provenance: dict[str, ColumnProvenance] = {}

    for col_name, col_policy in output_columns.items():
        method = col_policy.method
        unit = col_policy.unit or (policy.unit if policy else None)
        interpolated = False
        source_values: dict[str, float] = {}
        resolved: float

        if lower_row is None or upper_row is None:
            raise ValueError(f"Could not resolve column {col_name!r}")

        if method == "exact" or fraction is None or lower_row is upper_row:
            source_row = lower_row
            raw = source_row.get(col_name)
            if raw is None and policy.missing_value == "error":
                raise ValueError(f"Missing value in column {col_name!r}")
            if raw is None:
                raise ValueError(f"Missing value in column {col_name!r}")
            resolved = float(raw)
            source_values = {"exact": resolved}
            resolution_method = "exact" if method == "exact" else method
        elif method == "linear_interpolation":
            v0_raw = lower_row.get(col_name)
            v1_raw = upper_row.get(col_name)
            if v0_raw is None or v1_raw is None:
                if policy.missing_value == "error":
                    raise ValueError(f"Missing value in column {col_name!r} for interpolation")
                raise ValueError(f"Missing value in column {col_name!r} for interpolation")
            v0 = float(v0_raw)
            v1 = float(v1_raw)
            resolved = linear_interpolate_value(v0, v1, fraction)
            source_values = {"lower": v0, "upper": v1}
            interpolated = True
            any_interpolated = True
            resolution_method = "linear_interpolation"
        else:
            raise ValueError(f"Unsupported column resolution method: {method!r}")

        values[col_name] = resolved
        column_provenance[col_name] = ColumnProvenance(
            source_column=col_name,
            source_values=source_values,
            lower_source_row=dict(lower_row),
            upper_source_row=dict(upper_row),
            interpolation_fraction=fraction if interpolated else None,
            unit=unit,
            resolution_method=resolution_method,
            interpolated=interpolated,
        )

    matched_row: dict[str, Any] | None = None
    if any_interpolated and fraction is not None and lower_row and upper_row:
        matched_row = {breakpoint_column: adjusted_query}
        for col_name, val in values.items():
            matched_row[col_name] = val
    elif lower_row is not None:
        matched_row = dict(lower_row)

    return TableRowsResolutionResult(
        values=values,
        column_provenance=column_provenance,
        interpolation_fraction=fraction if any_interpolated else None,
        lower_source_row=dict(lower_row) if lower_row else None,
        upper_source_row=dict(upper_row) if upper_row else None,
        matched_row=matched_row,
        interpolated=any_interpolated,
        breakpoint_column=breakpoint_column,
        query_value=adjusted_query,
    )


def resolution_result_to_meta(
    result: TableRowsResolutionResult,
    *,
    policy: RowResolutionPolicy,
) -> dict[str, Any]:
    """Build lookup meta dict from a table resolution result."""
    meta: dict[str, Any] = {
        "breakpoint_column": result.breakpoint_column,
        "query_value": result.query_value,
        "breakpoint_unit": policy.unit,
        "interpolation_fraction": result.interpolation_fraction,
        "interpolated": result.interpolated,
        "lower_source_row": result.lower_source_row,
        "upper_source_row": result.upper_source_row,
        "matched_row": result.matched_row,
        "column_provenance": {
            col: {
                "source_column": prov.source_column,
                "source_values": prov.source_values,
                "lower_source_row": prov.lower_source_row,
                "upper_source_row": prov.upper_source_row,
                "interpolation_fraction": prov.interpolation_fraction,
                "unit": prov.unit,
                "resolution_method": prov.resolution_method,
                "interpolated": prov.interpolated,
            }
            for col, prov in result.column_provenance.items()
        },
    }
    return meta
