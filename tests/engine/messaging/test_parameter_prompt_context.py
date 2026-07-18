"""Tests for PARAM metadata prompt context."""

from __future__ import annotations

from pathlib import Path

from engine.messaging.parameter_prompt_context import (
    parameter_metadata_context,
    parameter_prompt_from_metadata,
    short_prompt_from_metadata,
)


def _reader():
    from engine.reference.standards_reader import StandardsReader

    root = Path(__file__).resolve().parents[3]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_parameter_metadata_context_loads_prompt_and_examples() -> None:
    reader = _reader()
    ctx = parameter_metadata_context(reader, "internal_design_gage_pressure")
    assert ctx is not None
    assert ctx.prompt
    assert ctx.help_text
    assert ctx.input_examples
    assert ctx.canonical_symbol == "P"


def test_parameter_prompt_from_metadata_prefers_user_prompt() -> None:
    reader = _reader()
    ctx = parameter_metadata_context(reader, "corrosion_allowance")
    prompt = parameter_prompt_from_metadata(ctx)
    assert prompt is not None
    assert "corrosion allowance" in prompt.lower()
    assert "minimum required thickness" in prompt.lower()


def test_short_prompt_from_metadata_uses_user_prompt_prompt() -> None:
    reader = _reader()
    ctx = parameter_metadata_context(reader, "outside_diameter")
    short = short_prompt_from_metadata(ctx)
    assert short == "Enter outside diameter D."
