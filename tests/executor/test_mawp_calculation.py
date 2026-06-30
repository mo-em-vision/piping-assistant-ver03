"""Tests for MAWP calculation executors."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.functions import calculate_mawp, calculate_pressure_design_thickness

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_calculate_pressure_design_thickness() -> None:
    node_dir = PROJECT_ROOT / "standards/asme/asme_b31.3/nodes/B313-MAWP-PRESSURE-DESIGN"
    result = calculate_pressure_design_thickness(
        node_dir=node_dir,
        variables={"t_actual": 6.35, "c": 0.5},
    )
    assert result.final_result is not None
    assert result.final_result.value == pytest.approx(5.85)


def test_calculate_mawp_thin_wall() -> None:
    node_dir = PROJECT_ROOT / "standards/asme/asme_b31.3/nodes/B313-MAWP-CALCULATION"
    # SI units: S in Pa, t and D in mm
    s = 137_900_000.0
    t = 5.85
    d = 273.05
    result = calculate_mawp(
        node_dir=node_dir,
        variables={"S": s, "E": 1.0, "W": 1.0, "t": t, "D": d, "Y": 0.4},
    )
    assert result.final_result is not None
    mawp_pa = float(result.final_result.value)
    assert mawp_pa > 0
    expected = 2 * s * 1.0 * 1.0 * t / (d - 2 * 0.4 * t)
    assert mawp_pa == pytest.approx(expected, rel=1e-6)
