"""Tests for B313-302.3.5 subsection (d) displacement stress equations."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.functions import (
    calculate_allowable_displacement_stress_range,
    calculate_allowable_displacement_stress_range_with_margin,
    calculate_stress_range_factor,
)
from engine.reference.standards_paths import resolve_standard_pack


@pytest.fixture
def node_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    pack = resolve_standard_pack(root / "standards", "asme_b31.3")
    return pack / "nodes" / "B313-302.3.5"


def test_eq_1a_allowable_displacement_stress_range(node_dir: Path) -> None:
    variables = {"f": 1.0, "S_c": 100_000_000.0, "S_h": 80_000_000.0}
    result = calculate_allowable_displacement_stress_range(node_dir=node_dir, variables=variables)

    assert result.status.value == "PASS"
    assert result.final_result is not None
    assert result.final_result.symbol == "S_A"
    expected = 1.0 * (1.25 * 100_000_000.0 + 0.25 * 80_000_000.0)
    assert abs(result.final_result.value - expected) < 1e-6
    assert result.final_result.unit == "Pa"


def test_eq_1b_allowable_displacement_stress_range_with_margin(node_dir: Path) -> None:
    variables = {
        "f": 1.0,
        "S_c": 100_000_000.0,
        "S_h": 120_000_000.0,
        "S_L": 80_000_000.0,
    }
    result = calculate_allowable_displacement_stress_range_with_margin(
        node_dir=node_dir,
        variables=variables,
    )

    assert result.status.value == "PASS"
    assert result.final_result is not None
    expected = 1.0 * (1.25 * (100_000_000.0 + 120_000_000.0) - 80_000_000.0)
    assert abs(result.final_result.value - expected) < 1e-6


@pytest.mark.parametrize(
    ("N", "f_m", "expected_f"),
    [
        (1000.0, 1.2, 1.2),
        (1.0, 1.2, 1.2),
        (10.0, 1.0, 1.0),
    ],
)
def test_eq_1c_stress_range_factor(
    node_dir: Path,
    N: float,
    f_m: float,
    expected_f: float,
) -> None:
    result = calculate_stress_range_factor(
        node_dir=node_dir,
        variables={"N": N, "f_m": f_m},
    )

    assert result.status.value == "PASS"
    assert result.final_result is not None
    assert result.final_result.symbol == "f"
    raw_f = 6.0 * (N ** -0.2)
    assert abs(result.final_result.value - min(raw_f, f_m)) < 1e-9
    assert abs(result.final_result.value - expected_f) < 1e-9


def test_b313_302_3_5_equation_files_exist(node_dir: Path) -> None:
    for name in (
        "eq_1a_allowable_displacement_stress_range.md",
        "eq_1a_allowable_displacement_stress_range.py",
        "eq_1b_allowable_displacement_stress_range_with_margin.md",
        "eq_1b_allowable_displacement_stress_range_with_margin.py",
        "eq_1c_stress_range_factor.md",
        "eq_1c_stress_range_factor.py",
    ):
        assert (node_dir / "equations" / name).exists()
