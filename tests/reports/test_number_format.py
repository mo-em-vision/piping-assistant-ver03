"""Tests for report number formatting."""

from __future__ import annotations

from engine.reports.number_format import format_report_number, round_numbers_in_text


def test_format_report_number_rounds_to_three_decimals() -> None:
    assert format_report_number(2.252389391087652) == "2.252"
    assert format_report_number(8.0) == "8.000"


def test_round_numbers_in_text() -> None:
    assert round_numbers_in_text("Thickness is 2.252389 mm at 195.1 MPa") == (
        "Thickness is 2.252 mm at 195.100 MPa"
    )
