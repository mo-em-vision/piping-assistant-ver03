"""Pipe wall activation and internal/external pressure branching contract tests."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.tools import GraphTools
from tests.planner.helpers import _reader, gates_satisfied_pipe_wall_task
from tests.planner.plan_contract import (
    REQ_MINIMUM_REQUIRED_THICKNESS_EQ,
    REQ_REQUIRED_WALL_THICKNESS,
)

_INTERNAL_PRESSURE_REQUIREMENT_IDS = (
    "REQ-internal_design_gage_pressure",
    "REQ-diameter_resolution",
    "REQ-material_grade",
    "REQ-design_temperature",
    "REQ-pipe_construction_type",
    REQ_REQUIRED_WALL_THICKNESS,
    REQ_MINIMUM_REQUIRED_THICKNESS_EQ,
)


def _gates_open_plan():
    _, task = gates_satisfied_pipe_wall_task()
    graph = GraphTools(_reader())
    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.fact_store.active_facts()),
    )
    return build_engineering_plan(
        task,
        _reader(),
        preview=preview,
        existing_inputs=dict(task.fact_store.active_facts()),
    )


def test_gates_open_internal_pressure_requirements_are_active() -> None:
    plan = _gates_open_plan()

    for req_id in _INTERNAL_PRESSURE_REQUIREMENT_IDS:
        req = plan.requirements[req_id]
        assert req.activation_status == "active", req_id
