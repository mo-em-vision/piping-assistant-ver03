"""Equation display helpers for engineering reports."""

from __future__ import annotations

import re


def display_to_latex(display: str) -> str:
    text = display.strip()
    if not text:
        return ""
    if "\\frac" in text or "\\tag" in text:
        return re.sub(r"\s+", " ", text).strip()

    text = (
        text.replace("≤", "\\leq ")
        .replace("≥", "\\geq ")
        .replace("<=", "\\leq ")
        .replace(">=", "\\geq ")
    )

    if " = " in text and " / " in text:
        left, right = text.split(" = ", 1)
        if " / " in right and "\\frac" not in right:
            numerator, denominator = right.split(" / ", 1)
            return f"{left.strip()} = \\frac{{{numerator.strip()}}}{{{denominator.strip()}}}"

    text = re.sub(
        r"([A-Za-z][A-Za-z0-9_]*)\s*/\s*([A-Za-z][A-Za-z0-9_]*)",
        r"\\frac{\1}{\2}",
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


def equation_html(latex: str) -> str:
    return f'<div class="equation-display">\\[{latex}\\]</div>'


def equation_markdown(latex: str) -> str:
    return f"$$\n{latex}\n$$"
