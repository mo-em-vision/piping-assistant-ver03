"""Tests for structured prompt assembly rendering."""

from __future__ import annotations

from engine.messaging.prompt_format import PromptAssemblyContext, render_parameter_prompt


def test_render_parameter_prompt_includes_examples_and_usage() -> None:
    ctx = PromptAssemblyContext(
        parameter_id="internal_design_gage_pressure",
        label="Internal Design Gage Pressure",
        symbol="P",
        purpose="This value is used in the pressure design thickness equation",
        usage_site="Used in the governing equation: t = PD / (2SE)",
        examples=("500 psi", "8 bar"),
    )
    prompt = render_parameter_prompt(ctx)
    assert "Internal Design Gage Pressure" in prompt
    assert "500 psi" in prompt
    assert "governing equation" in prompt.lower()


def test_render_parameter_prompt_preserves_prebuilt_body() -> None:
    ctx = PromptAssemblyContext(
        parameter_id="pressure_loading",
        label="Pressure Loading",
        body="Input required — custom body.",
        options=("Internal pressure — use §304.1.2", "External pressure — use §304.1.3"),
    )
    prompt = render_parameter_prompt(ctx)
    assert "custom body" in prompt
    assert "1." in prompt
