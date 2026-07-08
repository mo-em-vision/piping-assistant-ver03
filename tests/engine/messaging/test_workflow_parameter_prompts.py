"""Tests for workflow parameter prompt catalog."""

from __future__ import annotations

from pathlib import Path

from engine.messaging.parameter_input_prompt import build_parameter_input_prompt
from engine.messaging.workflow_parameter_prompts import (
    default_workflow_parameter_prompt,
    resolve_workflow_parameter_prompt,
)
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


def test_default_material_prompt_explains_allowable_stress_lookup() -> None:
    prompt = default_workflow_parameter_prompt("material")
    assert prompt is not None
    assert "allowable stress" in prompt.lower()
    assert "ASTM A106 Grade B" in prompt


def test_resolve_workflow_parameter_prompt_prefers_field_question() -> None:
    prompt = resolve_workflow_parameter_prompt(
        "material",
        field_question="Custom material question.",
    )
    assert prompt == "Custom material question."


def test_build_parameter_input_prompt_straight_pipe_uses_numbered_gate() -> None:
    from api.workflow_bootstrap import bootstrap_new_task
    from config.loader import CLIConfig
    from engine.reference.standards_reader import StandardsReader

    root = Path(__file__).resolve().parents[3]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("param-prompt-straight", status=TaskStatus.AWAITING_INPUT)
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        standards_root=root / "knowledge" / "standards",
        sessions_dir=root / "sessions",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    bootstrap_new_task(task, "pipe_wall_thickness_design", config)

    prompt = build_parameter_input_prompt(reader, task, "straight_pipe_section")
    assert prompt is not None
    assert "straight pipe" in prompt.lower()
    assert "1." in prompt
    assert "2." in prompt


def test_build_parameter_input_prompt_material_uses_metadata_description() -> None:
    from engine.reference.standards_reader import StandardsReader

    root = Path(__file__).resolve().parents[3]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("param-prompt-material", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design", "selected_root": "pipe_wall_thickness_design"}

    prompt = build_parameter_input_prompt(reader, task, "material_grade")
    assert prompt is not None
    assert "allowable stress" in prompt.lower() or "material specification" in prompt.lower()
