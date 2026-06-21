"""Tests for shared prompt formatting helpers."""

from __future__ import annotations

from engine.messaging.prompt_format import format_parameter_block


def test_parameter_block_puts_fields_on_separate_lines() -> None:
    lines = format_parameter_block(
        "P",
        "Internal design gage pressure",
        value="8 bar",
        guidance="enter design pressure",
        options=("Confirm default (P = 1)", "Enter a different value"),
    )

    text = "\n".join(lines)
    assert "P\n" in text or text.strip().startswith("P")
    assert "Description: Internal design gage pressure" in text
    assert "Value: 8 bar" in text
    assert "Needed: enter design pressure" in text
    assert "Choose one:" in text
    assert "1. Confirm default" in text
