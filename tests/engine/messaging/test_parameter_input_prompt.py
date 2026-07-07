"""Tests for parameter input prompt builder."""

from __future__ import annotations

from pathlib import Path

from engine.messaging.parameter_input_prompt import build_parameter_input_prompt
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


def _reader():
    from engine.reference.standards_reader import StandardsReader

    root = Path(__file__).resolve().parents[3]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_pressure_loading_prompt_uses_workflow_interaction_question() -> None:
    reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("param-prompt-pressure", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design", "selected_root": "pipe_wall_thickness_design"}

    prompt = build_parameter_input_prompt(reader, task, "pressure_loading")
    assert prompt is not None
    assert "internal or external pressure" in prompt.lower()
    assert "304.1.2" not in prompt
    assert "304.1.3" not in prompt
