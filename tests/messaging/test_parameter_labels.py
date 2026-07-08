"""Tests for parameter display labels in user-facing prompts."""

from __future__ import annotations

from engine.graph.node_interaction import (
    InteractionMode,
    NodeInteractionSpec,
    propose_default_values,
    question_for_interaction,
)
from engine.reference.parameter_keys import parameter_display_label


def test_parameter_display_label_uses_param_name() -> None:
    label = parameter_display_label("straight_pipe_section")
    assert label == "Straight Pipe Section"
    assert "straight_pipe_section" not in label


def test_question_for_interaction_uses_display_label_for_defaults() -> None:
    spec = NodeInteractionSpec(
        variable="straight_pipe_section",
        node_id="304.1.1-a",
        mode=InteractionMode.VALUE_RESOLUTION,
        confirmation_required=True,
        default=True,
        unit="dimensionless",
        default_condition="Applied to a straight section of a pipe.",
    )
    proposed = propose_default_values([spec], {}, task_id="test-task")
    prompt = question_for_interaction(spec, proposed)
    assert "straight_pipe_section" not in prompt
    assert "Straight Pipe Section" in prompt
    assert "dimensionless" not in prompt
