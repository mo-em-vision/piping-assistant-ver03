"""Number formatting for human-readable engineering reports."""

from __future__ import annotations

import re
from typing import Any

_DECIMAL_NUMBER_RE = re.compile(r"-?\d+\.\d+")
_REPORT_DECIMALS = 3


def format_report_number(value: Any, *, decimals: int = _REPORT_DECIMALS) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number != number:  # NaN
        return str(value)
    return f"{number:.{decimals}f}"


def round_numbers_in_text(text: str, *, decimals: int = _REPORT_DECIMALS) -> str:
    if not text:
        return text

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        try:
            return f"{float(token):.{decimals}f}"
        except ValueError:
            return token

    return _DECIMAL_NUMBER_RE.sub(replace, text)


def format_report_cell(value: Any, *, decimals: int = _REPORT_DECIMALS) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return format_report_number(value, decimals=decimals)
    return round_numbers_in_text(str(value), decimals=decimals)
