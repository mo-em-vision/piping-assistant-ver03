"""Tests for PARAM resolution-branch requirement emission."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.resolution_branch_requirements import (
    alternative_id,
    resolution_branch_fact_key,
    resolution_requirement_id,
)
from tests.planner.test_plan_requirements import _gates_satisfied_task, _reader


def test_outside_diameter_resolution_from_param_metadata() -> None:
    _, task = _gates_satisfied_task()
    plan = build_engineering_plan(task, _reader())

    resolution_id = resolution_requirement_id("outside_diameter")
    diameter = plan.requirements[resolution_id]
    assert diameter.field == "outside_diameter"
    assert diameter.question_spec is not None
    assert diameter.question_spec.field == resolution_branch_fact_key("outside_diameter")

    alt_ids = {alt.id for alt in diameter.alternatives or []}
    assert alternative_id("outside_diameter", "direct_od") in alt_ids
    assert alternative_id("outside_diameter", "nps_lookup") in alt_ids
    assert "REQ-nominal_pipe_size" in plan.requirements
    assert "REQ-outside_diameter_lookup" in plan.requirements
