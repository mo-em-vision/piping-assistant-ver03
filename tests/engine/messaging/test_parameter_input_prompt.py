"""Tests for parameter input prompt builder."""

from __future__ import annotations

from pathlib import Path

from engine.messaging.parameter_input_prompt import (
    build_parameter_input_prompt,
    build_short_parameter_input_prompt,
)
from engine.messaging.parameter_prompt_context import parameter_metadata_context
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


def _reader():
    from engine.reference.standards_reader import StandardsReader

    root = Path(__file__).resolve().parents[3]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_pressure_loading_prompt_uses_numbered_branch_options() -> None:
    reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("param-prompt-pressure", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design", "selected_root": "pipe_wall_thickness_design"}

    prompt = build_parameter_input_prompt(reader, task, "pressure_loading")
    assert prompt is not None
    assert "internal or external" in prompt.lower()
    assert "1." in prompt
    assert "2." in prompt
    assert "304.1.2" in prompt
    assert "304.1.3" in prompt


def test_resolution_prefers_interaction_before_metadata_description() -> None:
    reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("param-prompt-order", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design", "selected_root": "pipe_wall_thickness_design"}

    prompt = build_parameter_input_prompt(reader, task, "pressure_loading")
    assert prompt is not None
    assert "applied to a straight section" not in prompt.lower()


def test_design_pressure_param_includes_unit_examples() -> None:
    reader = _reader()
    ctx = parameter_metadata_context(reader, "internal_design_gage_pressure")
    assert ctx is not None
    assert ctx.question is not None
    assert "500 psi" in ctx.question
    assert "pressure design thickness" in ctx.question.lower()


def test_short_pressure_loading_prompt_omits_numbered_choices() -> None:
    reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("param-prompt-short-pressure", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design", "selected_root": "pipe_wall_thickness_design"}

    short = build_short_parameter_input_prompt(reader, task, "pressure_loading")
    full = build_parameter_input_prompt(reader, task, "pressure_loading")
    assert short is not None
    assert full is not None
    assert "1." not in short
    assert "304.1.2" not in short
    assert "304.1.2" in full
    assert len(short) < len(full)


def test_short_internal_pressure_prompt_omits_examples() -> None:
    reader = _reader()
    ctx = parameter_metadata_context(reader, "internal_design_gage_pressure")
    assert ctx is not None
    assert ctx.short_question is not None
    assert "500 psi" not in ctx.short_question
    assert ctx.short_question.endswith(".")
