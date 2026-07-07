"""Tests for workflow-authored root goal metadata resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.planner.workflow_goal_metadata import (
    resolve_root_goal_spec,
    workflow_title_for_goal,
)
from engine.reference.standards_reader import StandardsReader


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath(
        "knowledge", "standards", "asme", "asme_b31.3"
    ).exists(),
    reason="ASME B31.3 pack required",
)
def test_pipe_wall_root_goal_resolved_from_workflow_metadata() -> None:
    reader = _reader()
    spec = resolve_root_goal_spec(
        reader,
        "pipe_wall_thickness_design",
        fallback_target_field="minimum_required_thickness",
    )

    assert spec.key == "calculate-minimum-required-thickness"
    assert spec.id == "GOAL-calculate-minimum-required-thickness"
    assert spec.target_parameter == "PARAM-minimum-required-thickness"
    assert spec.target_field == "minimum_required_thickness"
    assert spec.title == workflow_title_for_goal(reader, "pipe_wall_thickness_design")
    assert spec.title == "Pipe Wall Thickness Design"


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath(
        "knowledge", "standards", "asme", "asme_b31.3"
    ).exists(),
    reason="ASME B31.3 pack required",
)
def test_mawp_root_goal_resolved_from_workflow_metadata() -> None:
    reader = _reader()
    spec = resolve_root_goal_spec(
        reader,
        "mawp_design",
        fallback_target_field="mawp",
    )

    assert spec.target_parameter == "PARAM-maximum-allowable-working-pressure"
    assert spec.target_field == "mawp"
    assert spec.key == "calculate-mawp"
    assert spec.title == "Maximum Allowable Working Pressure (MAWP)"
