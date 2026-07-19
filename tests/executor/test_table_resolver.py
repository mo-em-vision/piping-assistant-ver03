"""Tests for generic table row resolution."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from engine.executor.table_resolver import (
    OutputColumnPolicy,
    RowResolutionPolicy,
    linear_interpolate_value,
    resolve_table_rows,
)


def _sample_rows() -> list[dict]:
    return [
        {"design_temperature": 100.0, "allowable_stress": 200.0, "material_group": "A"},
        {"design_temperature": 200.0, "allowable_stress": 300.0, "material_group": "B"},
        {"design_temperature": 300.0, "allowable_stress": 400.0, "material_group": "C"},
    ]


def test_linear_interpolate_value() -> None:
    assert linear_interpolate_value(200.0, 300.0, 0.5) == pytest.approx(250.0)


def test_resolve_single_interpolated_column() -> None:
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        interpolate_columns=("allowable_stress",),
    )
    result = resolve_table_rows(
        _sample_rows(),
        breakpoint_column="design_temperature",
        output_columns={"allowable_stress": OutputColumnPolicy(method="linear_interpolation")},
        query_value=150.0,
        policy=policy,
    )
    assert result.values["allowable_stress"] == pytest.approx(250.0)
    assert result.interpolated is True
    assert result.interpolation_fraction == pytest.approx(0.5)
    prov = result.column_provenance["allowable_stress"]
    assert prov.source_column == "allowable_stress"
    assert prov.source_values == {"lower": 200.0, "upper": 300.0}
    assert prov.resolution_method == "linear_interpolation"


def test_resolve_multiple_interpolated_columns() -> None:
    rows = [
        {"design_temperature": 100.0, "allowable_stress": 200.0, "allowable_stress_alt": 20.0},
        {"design_temperature": 200.0, "allowable_stress": 300.0, "allowable_stress_alt": 30.0},
    ]
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        interpolate_columns=("allowable_stress", "allowable_stress_alt"),
    )
    result = resolve_table_rows(
        rows,
        breakpoint_column="design_temperature",
        output_columns={
            "allowable_stress": OutputColumnPolicy(method="linear_interpolation"),
            "allowable_stress_alt": OutputColumnPolicy(method="linear_interpolation"),
        },
        query_value=150.0,
        policy=policy,
    )
    assert result.values["allowable_stress"] == pytest.approx(250.0)
    assert result.values["allowable_stress_alt"] == pytest.approx(25.0)
    assert result.lower_source_row is not None
    assert result.upper_source_row is not None
    frac_a = result.column_provenance["allowable_stress"].interpolation_fraction
    frac_b = result.column_provenance["allowable_stress_alt"].interpolation_fraction
    assert frac_a == frac_b == pytest.approx(0.5)


def test_resolve_mixed_interpolated_and_exact_columns() -> None:
    rows = [
        {"design_temperature": 100.0, "allowable_stress": 200.0, "quality_factor": 0.8},
        {"design_temperature": 200.0, "allowable_stress": 300.0, "quality_factor": 1.0},
    ]
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        output_columns={
            "allowable_stress": OutputColumnPolicy(method="linear_interpolation"),
            "quality_factor": OutputColumnPolicy(method="exact"),
        },
    )
    result = resolve_table_rows(
        rows,
        breakpoint_column="design_temperature",
        output_columns=policy.output_columns,
        query_value=150.0,
        policy=policy,
    )
    assert result.values["allowable_stress"] == pytest.approx(250.0)
    assert result.column_provenance["allowable_stress"].interpolated is True
    assert result.column_provenance["quality_factor"].interpolated is False
    assert result.values["quality_factor"] == pytest.approx(0.8)


def test_resolve_missing_value_among_columns_raises() -> None:
    rows = [
        {"design_temperature": 100.0, "allowable_stress": 200.0, "allowable_stress_alt": None},
        {"design_temperature": 200.0, "allowable_stress": 300.0, "allowable_stress_alt": 30.0},
    ]
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        missing_value="error",
        interpolate_columns=("allowable_stress", "allowable_stress_alt"),
    )
    with pytest.raises(ValueError, match="Missing value"):
        resolve_table_rows(
            rows,
            breakpoint_column="design_temperature",
            output_columns={
                "allowable_stress": OutputColumnPolicy(method="linear_interpolation"),
                "allowable_stress_alt": OutputColumnPolicy(method="linear_interpolation"),
            },
            query_value=150.0,
            policy=policy,
        )


def test_shared_interpolation_fraction_consistent() -> None:
    rows = [
        {"design_temperature": 0.0, "v1": 0.0, "v2": 100.0},
        {"design_temperature": 100.0, "v1": 100.0, "v2": 200.0},
    ]
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        interpolate_columns=("v1", "v2"),
    )
    result = resolve_table_rows(
        rows,
        breakpoint_column="design_temperature",
        output_columns={
            "v1": OutputColumnPolicy(method="linear_interpolation"),
            "v2": OutputColumnPolicy(method="linear_interpolation"),
        },
        query_value=25.0,
        policy=policy,
    )
    assert result.interpolation_fraction == pytest.approx(0.25)
    for col in ("v1", "v2"):
        assert result.column_provenance[col].interpolation_fraction == pytest.approx(0.25)


def test_per_column_provenance_recorded() -> None:
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        unit="degF",
        interpolate_columns=("allowable_stress",),
    )
    result = resolve_table_rows(
        _sample_rows(),
        breakpoint_column="design_temperature",
        output_columns={"allowable_stress": OutputColumnPolicy(method="linear_interpolation", unit="Pa")},
        query_value=200.0,
        policy=policy,
    )
    prov = result.column_provenance["allowable_stress"]
    assert prov.unit == "Pa"
    assert prov.lower_source_row is not None
    assert prov.upper_source_row is not None
    assert prov.interpolation_fraction is None
    assert prov.interpolated is False


def test_bracketing_runs_once() -> None:
    rows = [
        {"design_temperature": 100.0, "allowable_stress": 200.0, "quality_factor": 0.8},
        {"design_temperature": 200.0, "allowable_stress": 300.0, "quality_factor": 1.0},
        {"design_temperature": 300.0, "allowable_stress": 400.0, "quality_factor": 1.0},
    ]
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        interpolate_columns=("allowable_stress",),
    )
    with patch(
        "engine.executor.table_resolver._find_bracketing",
        wraps=__import__("engine.executor.table_resolver", fromlist=["_find_bracketing"])._find_bracketing,
    ) as mock_bracket:
        resolve_table_rows(
            rows,
            breakpoint_column="design_temperature",
            output_columns={
                "allowable_stress": OutputColumnPolicy(method="linear_interpolation"),
                "quality_factor": OutputColumnPolicy(method="exact"),
            },
            query_value=150.0,
            policy=policy,
        )
        assert mock_bracket.call_count == 1


def test_undeclared_column_not_interpolated() -> None:
    rows = [
        {"design_temperature": 100.0, "allowable_stress": 200.0, "notes": 1.0},
        {"design_temperature": 200.0, "allowable_stress": 300.0, "notes": 2.0},
    ]
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        interpolate_columns=("allowable_stress",),
    )
    result = resolve_table_rows(
        rows,
        breakpoint_column="design_temperature",
        output_columns={
            "allowable_stress": OutputColumnPolicy(method="linear_interpolation"),
            "notes": OutputColumnPolicy(method="exact"),
        },
        query_value=150.0,
        policy=policy,
    )
    assert result.values["allowable_stress"] == pytest.approx(250.0)
    assert result.column_provenance["notes"].interpolated is False
    assert result.values["notes"] == pytest.approx(1.0)


def test_outside_range_error() -> None:
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        outside_range="error",
        interpolate_columns=("allowable_stress",),
    )
    with pytest.raises(ValueError, match="outside permitted range"):
        resolve_table_rows(
            _sample_rows(),
            breakpoint_column="design_temperature",
            output_columns={"allowable_stress": OutputColumnPolicy(method="linear_interpolation")},
            query_value=50.0,
            policy=policy,
        )


def test_clamp_to_boundary() -> None:
    rows = [
        {"design_temperature": 900.0, "coefficient_Y": 0.4},
        {"design_temperature": 1000.0, "coefficient_Y": 0.7},
    ]
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        outside_range="clamp_to_boundary",
        min_bound=900.0,
        max_bound=1250.0,
        interpolate_columns=("coefficient_Y",),
    )
    result = resolve_table_rows(
        rows,
        breakpoint_column="design_temperature",
        output_columns={"coefficient_Y": OutputColumnPolicy(method="linear_interpolation")},
        query_value=100.0,
        policy=policy,
    )
    assert result.query_value == pytest.approx(900.0)
    assert result.values["coefficient_Y"] == pytest.approx(0.4)


def test_duplicate_breakpoints_error() -> None:
    rows = [
        {"design_temperature": 100.0, "allowable_stress": 200.0},
        {"design_temperature": 100.0, "allowable_stress": 210.0},
    ]
    policy = RowResolutionPolicy(
        breakpoint_column="design_temperature",
        method="linear_interpolation",
        duplicate_breakpoints="error",
        interpolate_columns=("allowable_stress",),
    )
    with pytest.raises(ValueError, match="Duplicate breakpoints"):
        resolve_table_rows(
            rows,
            breakpoint_column="design_temperature",
            output_columns={"allowable_stress": OutputColumnPolicy(method="linear_interpolation")},
            query_value=150.0,
            policy=policy,
        )
