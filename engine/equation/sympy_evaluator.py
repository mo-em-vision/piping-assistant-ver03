"""Sympy-based equation evaluation for micro-graph equation nodes."""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

from engine.equation.equation_renderer import (
    EquationRenderSteps,
    parse_assignment,
    render_equation_steps,
)

# Backward-compatible alias for equation validation callers.
_parse_assignment = parse_assignment


@dataclass
class EquationEvalResult:
    outputs: dict[str, float]
    substitution: str
    result_text: str
    display: str
    render_steps: EquationRenderSteps


def evaluate_equation(
    *,
    sympy_expr: str,
    display_latex: str,
    symbol_values: dict[str, float],
) -> EquationEvalResult:
    """Evaluate a sympy assignment expression with substituted symbol values."""
    lhs, rhs = parse_assignment(sympy_expr)
    output_symbol = str(lhs)
    free_symbols = sorted(rhs.free_symbols, key=lambda sym: str(sym))
    subs: dict[sp.Symbol, float] = {}
    for sym in free_symbols:
        name = str(sym)
        if name not in symbol_values:
            raise KeyError(f"Missing value for symbol: {name}")
        subs[sym] = float(symbol_values[name])

    evaluated = float(rhs.subs(subs))
    steps = render_equation_steps(
        sympy_expr=sympy_expr,
        display_latex=display_latex,
        symbol_values=symbol_values,
        evaluated_value=evaluated,
    )
    substitution = f"{steps.substituted}  →  {steps.evaluated}"
    return EquationEvalResult(
        outputs={output_symbol: evaluated},
        substitution=substitution,
        result_text=steps.evaluated,
        display=display_latex or sympy_expr,
        render_steps=steps,
    )
