"""Shared KaTeX/LaTeX formatting for equation display traces."""

from __future__ import annotations

import re
from typing import Iterable

_HIDDEN_UNITS = frozenset({"dimensionless", ""})


def format_numeric_display(value: float) -> str:
    """Format a numeric value for display strings only (raw value kept separately)."""
    if abs(value) >= 1_000_000 or (abs(value) > 0 and abs(value) < 0.001):
        return f"{value:g}"
    rounded = round(value, 6)
    if rounded == int(rounded):
        return f"{int(rounded)}"
    text = f"{rounded:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def format_unit_latex(unit: str) -> str:
    normalized = unit.strip()
    if not normalized or normalized in _HIDDEN_UNITS:
        return ""
    if normalized == "°C":
        return r"\mathrm{^\circ C}"
    if normalized == "°F":
        return r"\mathrm{^\circ F}"
    escaped = normalized.replace(" ", r"\ ")
    return rf"\mathrm{{{escaped}}}"


def format_quantity_latex(value: float, unit: str | None) -> str:
    numeric = format_numeric_display(value)
    unit_latex = format_unit_latex(unit or "")
    if unit_latex:
        return f"{numeric}\\ {unit_latex}"
    return numeric


def format_substituted_term(value: float, unit: str | None = None) -> str:
    """Wrap a substituted numeric value for inline KaTeX."""
    return f"({format_quantity_latex(value, unit)})"


def display_text_to_latex(text: str) -> str:
    """Convert plain display text to minimal structural LaTeX."""
    normalized = re.sub(r"\s+", " ", text.strip())
    if " = " in normalized and " / " in normalized:
        left, right = normalized.split(" = ", 1)
        numerator, denominator = right.split(" / ", 1)
        return (
            f"{left.strip()} = "
            f"\\frac{{{numerator.strip()}}}{{{denominator.strip()}}}"
        )
    return normalized


def _symbol_pattern(symbol: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z_]){re.escape(symbol)}(?![A-Za-z_])")


_IMPLICIT_PRODUCT_RUN = re.compile(r"(?<![A-Za-z_])([A-Z][A-Z]+)(?![A-Za-z_])")


def _decompose_implicit_product(run: str, symbols: frozenset[str]) -> list[str] | None:
    """Split concatenated symbol products such as PD into [P, D] when all parts are known."""
    if run in symbols:
        return None

    ordered = sorted(symbols, key=len, reverse=True)
    decompositions: list[list[str]] = []

    def search(remaining: str, path: list[str]) -> None:
        if not remaining:
            if len(path) > 1:
                decompositions.append(path)
            return
        for symbol in ordered:
            if remaining.startswith(symbol):
                search(remaining[len(symbol) :], path + [symbol])

    search(run, [])
    if not decompositions:
        return None
    return min(decompositions, key=len)


def expand_implicit_symbol_products(
    symbolic_latex: str,
    symbols: Iterable[str],
) -> str:
    """Insert spaces between implicitly multiplied symbols (e.g. PD -> P D)."""
    symbol_set = frozenset(str(symbol).strip() for symbol in symbols if str(symbol).strip())
    if not symbol_set:
        return symbolic_latex

    def replacer(match: re.Match[str]) -> str:
        run = match.group(1)
        decomposed = _decompose_implicit_product(run, symbol_set)
        if decomposed is None:
            return run
        return " ".join(decomposed)

    return _IMPLICIT_PRODUCT_RUN.sub(replacer, symbolic_latex)


def substitute_symbols_in_latex(
    symbolic_latex: str,
    substitutions: dict[str, str],
    *,
    symbol_order: Iterable[str] | None = None,
) -> str:
    """Replace symbols longest-first to avoid partial token matches."""
    text = expand_implicit_symbol_products(symbolic_latex, substitutions)
    order = list(symbol_order) if symbol_order is not None else sorted(substitutions, key=len, reverse=True)
    for symbol in order:
        replacement = substitutions.get(symbol)
        if not replacement:
            continue
        text = _symbol_pattern(symbol).sub(lambda _match, rep=replacement: rep, text)
    return text


def format_substituted_equation(
    symbolic_latex: str,
    substitutions: dict[str, str],
    *,
    symbol_order: Iterable[str] | None = None,
    result_latex: str | None = None,
) -> str:
    """Build substituted LaTeX from symbolic form and numeric term replacements."""
    substituted = substitute_symbols_in_latex(
        symbolic_latex,
        substitutions,
        symbol_order=symbol_order,
    )
    if result_latex:
        return f"{substituted} = {result_latex}"
    return substituted
