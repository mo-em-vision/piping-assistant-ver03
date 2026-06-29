"""SymPy-based four-step equation rendering (Phase 10)."""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy as sp
from sympy.core.parameters import evaluate


@dataclass(frozen=True)
class EquationRenderSteps:
    """Ordered equation display steps from symbolic substitution."""

    original: str
    substituted: str
    simplified: str
    evaluated: str


def _identifiers(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))


def parse_assignment(expr_text: str) -> tuple[sp.Symbol, sp.Expr]:
    """Parse ``lhs = rhs`` into a symbol and expression."""
    text = expr_text.strip()
    if "=" not in text:
        raise ValueError(f"Equation must be an assignment: {expr_text}")
    lhs_text, rhs_text = text.split("=", 1)
    lhs_text = lhs_text.strip()
    rhs_text = rhs_text.strip()
    names = _identifiers(lhs_text) | _identifiers(rhs_text)
    local_symbols = {name: sp.Symbol(name) for name in names}
    lhs = sp.sympify(lhs_text, locals=local_symbols)
    rhs = sp.sympify(rhs_text, locals=local_symbols)
    if not isinstance(lhs, sp.Symbol):
        raise ValueError(f"Left-hand side must be a single symbol: {lhs_text}")
    return lhs, rhs


def _format_expr(expr: sp.Expr) -> str:
    return sp.sstr(expr, full_prec=False)


def render_equation_steps(
    *,
    sympy_expr: str,
    display_latex: str,
    symbol_values: dict[str, float],
    evaluated_value: float | None = None,
) -> EquationRenderSteps:
    """Build four display steps using symbolic substitution (no regex replacement)."""
    lhs, rhs = parse_assignment(sympy_expr)
    output_symbol = str(lhs)
    original = (display_latex or sympy_expr).strip()

    free_symbols = sorted(rhs.free_symbols, key=lambda sym: str(sym))
    subs: dict[sp.Symbol, float] = {}
    for sym in free_symbols:
        name = str(sym)
        if name not in symbol_values:
            raise KeyError(f"Missing value for symbol: {name}")
        subs[sym] = float(symbol_values[name])

    with evaluate(False):
        substituted_rhs = rhs.subs(subs)
    simplified_rhs = sp.simplify(substituted_rhs)
    evaluated = (
        float(evaluated_value)
        if evaluated_value is not None
        else float(simplified_rhs)
    )

    return EquationRenderSteps(
        original=original,
        substituted=f"{output_symbol} = {_format_expr(substituted_rhs)}",
        simplified=f"{output_symbol} = {_format_expr(simplified_rhs)}",
        evaluated=f"{output_symbol} = {evaluated:g}",
    )
