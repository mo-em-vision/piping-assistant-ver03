"""Calculation engine tests."""

from __future__ import annotations

from pathlib import Path

from engine.executor.calculation_engine import CalculationEngine
from engine.executor.unit_manager import convert_to_si


def _formula_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return (
        root
        / "standards"
        / "asme_b31.3"
        / "nodes"
        / "B313-304.1.1"
        / "formulas"
        / "wall_thickness.md"
    )


def test_wall_thickness_formula_known_values() -> None:
    p_pa, _ = convert_to_si(500, "psi")
    d_mm, _ = convert_to_si(10, "in")
    s_pa = 193_000_000.0
    variables = {"P": p_pa, "D": d_mm, "S": s_pa, "E": 1.0, "W": 1.0, "Y": 0.4}

    result = CalculationEngine().execute_from_file(
        calculation_id="test-wall-thickness",
        formula_path=_formula_path(),
        variables=variables,
    )

    assert result.status.value == "PASS"
    assert result.final_result is not None
    t = result.final_result.value

    sew = s_pa * 1.0 * 1.0
    py = p_pa * 0.4
    expected = p_pa * d_mm / (2 * (sew + py))
    assert abs(t - expected) < 1e-6

    intermediates = {}
    for step in result.steps:
        if isinstance(step.result, dict):
            intermediates.update(step.result)
    assert "SEW" in intermediates
    assert "PY" in intermediates
    assert abs(intermediates["SEW"] - sew) < 1e-6
    assert abs(intermediates["PY"] - py) < 1e-6


def test_psi_to_pa_doc_reference() -> None:
    p_pa, unit = convert_to_si(500, "psi")
    assert unit == "Pa"
    assert abs(p_pa - 3_447_378.65) < 1.0
