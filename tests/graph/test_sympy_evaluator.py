"""Sympy equation evaluator tests."""

from __future__ import annotations

import pytest

from engine.equation.sympy_evaluator import evaluate_equation


def test_minimum_required_thickness() -> None:
    result = evaluate_equation(
        sympy_expr="t_m = t + c",
        display_latex="t_m = t + c",
        symbol_values={"t": 4.5, "c": 0.5},
    )
    assert result.outputs["t_m"] == pytest.approx(5.0)
    assert "t_m" in result.substitution


def test_wall_thickness_internal_pressure() -> None:
    result = evaluate_equation(
        sympy_expr="t = P*D / (2*(S*E*W + P*Y))",
        display_latex="t = PD / (2(SEW + PY))",
        symbol_values={
            "P": 2e6,
            "D": 0.273,
            "S": 138e6,
            "E": 1.0,
            "W": 1.0,
            "Y": 0.4,
        },
    )
    assert result.outputs["t"] > 0
    assert "t" in result.result_text
