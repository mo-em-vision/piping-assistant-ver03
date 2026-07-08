"""Tests for shared equation LaTeX formatting."""

from __future__ import annotations

from engine.equation.latex_format import (
    display_text_to_latex,
    format_numeric_display,
    format_quantity_latex,
    format_substituted_equation,
    format_unit_latex,
    substitute_symbols_in_latex,
)


def test_format_unit_latex_uses_mathrm() -> None:
    assert format_unit_latex("mm") == r"\mathrm{mm}"
    assert format_unit_latex("MPa") == r"\mathrm{MPa}"


def test_format_quantity_latex() -> None:
    assert format_quantity_latex(2.252, "mm") == r"2.252\ \mathrm{mm}"


def test_display_text_to_latex_fraction() -> None:
    latex = display_text_to_latex("t = PD / 2(SEW + PY)")
    assert latex == "t = \\frac{PD}{2(SEW + PY)}"


def test_substitute_symbols_longest_first() -> None:
    substitutions = {
        "SEW": "(1)(2)(3)",
        "S": "(9)",
        "E": "(8)",
        "W": "(7)",
    }
    text = substitute_symbols_in_latex("2(SEW + PY)", substitutions)
    assert "(9)" not in text
    assert "(1)(2)(3)" in text


def test_format_substituted_equation_appends_result() -> None:
    latex = format_substituted_equation(
        "t_m = t + c",
        {"t": "(4.5)", "c": "(0.5)"},
        symbol_order=("t", "c"),
        result_latex=r"5\ \mathrm{mm}",
    )
    assert latex.startswith("t_m = ")
    assert "= 5\\ \\mathrm{mm}" in latex


def test_format_numeric_display_rounds_for_display_only() -> None:
    assert format_numeric_display(2.2520004) == "2.252"
