"""Calculation engine tests."""

from __future__ import annotations

from pathlib import Path

from engine.executor.calculation_engine import CalculationEngine
from engine.executor.unit_manager import convert_to_si


def _wall_thickness_formula_data() -> dict:
    from engine.reference.standards_reader import StandardsReader

    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards")
    node = reader.load("asme-b313-304-1-2-eq-3a")
    return dict(node.metadata)


def test_wall_thickness_formula_known_values() -> None:
    p_pa, _ = convert_to_si(500, "psi")
    d_mm, _ = convert_to_si(10, "in")
    s_pa = 193_000_000.0
    variables = {"P": p_pa, "D": d_mm, "S": s_pa, "E_j": 1.0, "W": 1.0, "Y": 0.4}

    result = CalculationEngine().execute_formula_steps(
        calculation_id="test-wall-thickness",
        formula_data=_wall_thickness_formula_data(),
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


def test_formula_steps_use_e_j_quality_factor_symbol() -> None:
    p_pa, _ = convert_to_si(8.0, "bar")
    d_mm = 168.3
    s_pa = 206_944_000.0
    variables = {"P": p_pa, "D": d_mm, "S": s_pa, "E_j": 1.0, "W": 1.0, "Y": 0.4}
    formula_data = {
        "steps": [
            {
                "name": "compute_denominator_terms",
                "expressions": [
                    {"expression": "S * E_j * W", "assign": "SEW"},
                    {"expression": "P * Y", "assign": "PY"},
                ],
            },
            {
                "name": "compute_required_thickness",
                "expressions": [
                    {"expression": "P * D / (2 * (SEW + PY))", "assign": "t"},
                ],
            },
        ],
        "outputs": [{"symbol": "t", "unit": "mm"}],
    }

    result = CalculationEngine().execute_formula_steps(
        calculation_id="test-ej-symbol",
        formula_data=formula_data,
        variables=variables,
    )

    assert result.final_result is not None
    expected = p_pa * d_mm / (2 * (s_pa * 1.0 * 1.0 + p_pa * 0.4))
    assert abs(float(result.final_result.value) - expected) < 1e-6


def test_psi_to_pa_doc_reference() -> None:
    p_pa, unit = convert_to_si(500, "psi")
    assert unit == "Pa"
    assert abs(p_pa - 3_447_378.65) < 1.0
