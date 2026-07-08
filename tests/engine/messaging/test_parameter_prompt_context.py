"""Tests for messaging-owned PARAM metadata context."""

from __future__ import annotations

from pathlib import Path

from engine.messaging.parameter_prompt_context import (
    parameter_metadata_context,
    parameter_prompt_from_metadata,
    report_metadata_gaps,
)
from engine.reference.standards_reader import StandardsReader


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[3]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_parameter_metadata_context_reads_description() -> None:
    reader = _reader()
    ctx = parameter_metadata_context(reader, "material_grade")
    assert ctx is not None
    assert ctx.description
    assert "allowable stress" in ctx.description.lower()


def test_parameter_prompt_from_metadata_prefers_question() -> None:
    reader = _reader()
    ctx = parameter_metadata_context(reader, "material_grade")
    prompt = parameter_prompt_from_metadata(ctx)
    assert prompt is not None
    assert ctx is not None
    assert "allowable stress" in prompt.lower()


def test_parameter_prompt_skips_thin_description() -> None:
    reader = _reader()
    ctx = parameter_metadata_context(reader, "corrosion_allowance")
    prompt = parameter_prompt_from_metadata(ctx)
    assert prompt is None


def test_report_metadata_gaps_lists_missing_node() -> None:
    gaps = report_metadata_gaps("nonexistent_parameter_xyz", None)
    assert gaps
    assert "not found" in gaps[0].lower()
