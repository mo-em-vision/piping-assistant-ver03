"""Sympy-based equation evaluation for micro-graph equation nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import sympy as sp


@dataclass
class EquationEvalResult:
    outputs: dict[str, float]
    substitution: str
    result_text: str
    display: str


def _identifiers(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))


def _parse_assignment(expr_text: str) -> tuple[sp.Symbol, sp.Expr]:
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


def _format_substitution(
    display: str,
    symbols: dict[str, float],
    result_symbol: str,
    result_value: float,
) -> str:
  parts: list[str] = []
  for symbol_name, value in symbols.items():
      if symbol_name == result_symbol:
          continue
      parts.append(f"{symbol_name}={value:g}")
  sub_line = display
  for symbol_name, value in symbols.items():
      sub_line = re.sub(rf"\b{re.escape(symbol_name)}\b", f"{value:g}", sub_line)
  return f"{sub_line}  →  {result_symbol} = {result_value:g}"


def evaluate_equation(
    *,
    sympy_expr: str,
    display_latex: str,
    symbol_values: dict[str, float],
) -> EquationEvalResult:
    """Evaluate a sympy assignment expression with substituted symbol values."""
    lhs, rhs = _parse_assignment(sympy_expr)
    output_symbol = str(lhs)
    free_symbols = sorted(rhs.free_symbols, key=lambda sym: str(sym))
    subs: dict[sp.Symbol, float] = {}
    resolved: dict[str, float] = {}
    for sym in free_symbols:
        name = str(sym)
        if name not in symbol_values:
            raise KeyError(f"Missing value for symbol: {name}")
        value = float(symbol_values[name])
        subs[sym] = value
        resolved[name] = value

    evaluated = float(rhs.subs(subs))
    resolved[output_symbol] = evaluated
    substitution = _format_substitution(
        display_latex or sympy_expr,
        resolved,
        output_symbol,
        evaluated,
    )
    return EquationEvalResult(
        outputs={output_symbol: evaluated},
        substitution=substitution,
        result_text=f"{output_symbol} = {evaluated:g}",
        display=display_latex or sympy_expr,
    )
