"""Tests for workflow parameter prompt resolution via PARAM nodes."""

from __future__ import annotations

from pathlib import Path

from engine.messaging.parameter_input_prompt import (
    build_parameter_input_prompt,
    resolve_parameter_prompt_text,
)
from engine.messaging.parameter_prompt_context import parameter_metadata_context, report_metadata_gaps
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


def _reader():
    from engine.reference.standards_reader import StandardsReader

    root = Path(__file__).resolve().parents[3]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_resolve_parameter_prompt_text_prefers_field_question() -> None:
    prompt = resolve_parameter_prompt_text(
        "material_grade",
        field_question="Custom material question.",
    )
    assert prompt == "Custom material question."


def test_resolve_parameter_prompt_text_uses_param_question() -> None:
    reader = _reader()
    prompt = resolve_parameter_prompt_text("material_grade", reader=reader)
    assert "material specification" in prompt.lower()
    assert "ASTM A106 Grade B" in prompt


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


def test_build_parameter_input_prompt_material_uses_param_question() -> None:
    reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("param-prompt-material", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design", "selected_root": "pipe_wall_thickness_design"}

    prompt = build_parameter_input_prompt(reader, task, "material_grade")
    assert prompt is not None
    assert "allowable stress" in prompt.lower() or "material specification" in prompt.lower()


def test_gatherable_param_nodes_have_useful_descriptions() -> None:
    reader = _reader()
    gatherable = [
        "straight_pipe_section",
        "pressure_design_case",
        "internal_design_gage_pressure",
        "nominal_pipe_size",
        "outside_diameter",
        "material_grade",
        "design_temperature",
        "pipe_construction_type",
        "corrosion_allowance",
    ]
    for parameter_id in gatherable:
        ctx = parameter_metadata_context(reader, parameter_id)
        gaps = report_metadata_gaps(parameter_id, ctx, required_fields=("description",))
        assert not gaps, gaps
