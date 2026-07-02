"""Tests for B31.3 §302.3.5 displacement stress equations."""

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
def paragraph_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    pack = resolve_standard_pack(root / "knowledge" / "standards", "asme_b31.3")
    return pack / "nodes" / "paragraph" / "302.3.5"


@pytest.fixture
def equation_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    pack = resolve_standard_pack(root / "knowledge" / "standards", "asme_b31.3")
    return pack / "nodes" / "equation"


def test_eq_1a_allowable_displacement_stress_range(paragraph_dir: Path) -> None:
    py_path = paragraph_dir / "eq_1a_allowable_displacement_stress_range.py"
    if not py_path.is_file():
        pytest.skip("Companion Python equation module not present on disk")
    variables = {"f": 1.0, "S_c": 100_000_000.0, "S_h": 80_000_000.0}
    result = calculate_allowable_displacement_stress_range(node_dir=paragraph_dir, variables=variables)

    assert result.status.value == "PASS"
    assert result.final_result is not None
    assert result.final_result.symbol == "S_A"
    expected = 1.0 * (1.25 * 100_000_000.0 + 0.25 * 80_000_000.0)
    assert abs(result.final_result.value - expected) < 1e-6
    assert result.final_result.unit == "Pa"


def test_eq_1b_allowable_displacement_stress_range_with_margin(paragraph_dir: Path) -> None:
    py_path = paragraph_dir / "eq_1b_allowable_displacement_stress_range_with_margin.py"
    if not py_path.is_file():
        pytest.skip("Companion Python equation module not present on disk")
    variables = {
        "f": 1.0,
        "S_c": 100_000_000.0,
        "S_h": 120_000_000.0,
        "S_L": 80_000_000.0,
    }
    result = calculate_allowable_displacement_stress_range_with_margin(
        node_dir=paragraph_dir,
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
    paragraph_dir: Path,
    N: float,
    f_m: float,
    expected_f: float,
) -> None:
    py_path = paragraph_dir / "eq_1c_stress_range_factor.py"
    if not py_path.is_file():
        pytest.skip("Companion Python equation module not present on disk")
    result = calculate_stress_range_factor(
        node_dir=paragraph_dir,
        variables={"N": N, "f_m": f_m},
    )

    assert result.status.value == "PASS"
    assert result.final_result is not None
    assert result.final_result.symbol == "f"
    raw_f = 6.0 * (N ** -0.2)
    assert abs(result.final_result.value - min(raw_f, f_m)) < 1e-9
    assert abs(result.final_result.value - expected_f) < 1e-9


def test_b313_302_3_5_equation_nodes_exist(equation_dir: Path) -> None:
    expected = (
        "asme_b313_302_3_5_eq_1a",
        "asme_b313_302_3_5_eq_1b",
        "asme_b313_302_3_5_eq_1c",
    )
    for node_id in expected:
        path = equation_dir / f"{node_id}.yaml"
        assert path.is_file(), node_id
        text = path.read_text(encoding="utf-8")
        for token in ("type: equation", "authorized_by", node_id):
            assert token in text
