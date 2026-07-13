"""Equation renderer tests (Phase 10)."""

from __future__ import annotations

import inspect

import pytest

from engine.equation.equation_renderer import render_equation_steps
import engine.equation.equation_renderer as equation_renderer_module


def test_minimum_required_thickness_render_steps() -> None:
    steps = render_equation_steps(
        sympy_expr="t_m = t + c",
        display_latex="t_m = t + c",
        symbol_values={"t": 4.5, "c": 0.5},
    )
    assert steps.original == "t_m = t + c"
    assert "4.5" in steps.substituted
    assert "0.5" in steps.substituted
    assert steps.simplified == "t_m = 5.0"
    assert steps.evaluated == "t_m = 5"


def test_wall_thickness_render_steps_use_symbolic_substitution() -> None:
    display = "t = PD / (2(S E_j W + PY))"
    steps = render_equation_steps(
        sympy_expr="t = P*D / (2*(S*E_j*W + P*Y))",
        display_latex=display,
        symbol_values={
            "P": 2e6,
            "D": 0.273,
            "S": 138e6,
            "E_j": 1.0,
            "W": 1.0,
            "Y": 0.4,
        },
    )
    assert steps.original == display
    assert steps.substituted != display
    assert steps.simplified != display
    assert "2000000" in steps.substituted or "2.0e+06" in steps.substituted
    assert steps.evaluated.startswith("t = ")
    assert float(steps.evaluated.split("=", 1)[1].strip()) > 0


def test_renderer_does_not_use_regex_substitution_on_display() -> None:
    source = inspect.getsource(equation_renderer_module)
    assert "re.sub" not in source


def test_render_steps_requires_all_symbols() -> None:
    with pytest.raises(KeyError, match="Missing value for symbol"):
        render_equation_steps(
            sympy_expr="t_m = t + c",
            display_latex="t_m = t + c",
            symbol_values={"t": 4.5},
        )
