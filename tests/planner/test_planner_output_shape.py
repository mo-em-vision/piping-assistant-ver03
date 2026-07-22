"""Planner API output shape: canonical engineering_plan vs legacy_goal_map."""

from __future__ import annotations

from api.serializers import task_state
from engine.inspection.builder import build_inspection_payload
from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.goal_builder import build_goal_tree
from tests.planner.helpers import _reader, fresh_pipe_wall_task


def test_task_state_engineering_plan_is_canonical_not_goal_map() -> None:
    manager, task = fresh_pipe_wall_task(task_id="output-shape-pwt")
    reader = _reader()
    build_goal_tree(task, reader)
    manager.replace_task(task.task_id, task)

    payload = task_state(task, manager, reader=reader, projection_mode="full")

    plan = payload.get("engineering_plan")
    assert isinstance(plan, dict)
    assert plan["task_id"] == task.task_id
    assert plan["workflow_id"] == "pipe_wall_thickness_design"
    assert "plan_id" in plan
    assert "requirements" in plan
    assert "root_goal" in plan
    assert "dependencies" in plan
    assert "input_strategy" in plan
    assert "phases" in plan
    assert "graph" in plan
    assert "legacy_goal_map" in plan
    assert "traversal" in plan
    assert "GOAL-calculate-minimum-required-thickness" not in plan
    assert "REQ-straight_pipe_section" in plan["requirements"]
    assert plan["root_goal"]["target_parameter"] == "PARAM-minimum-required-thickness"
    assert plan["root_goal"]["required_outputs"] == [
        "minimum_required_thickness",
        "calculation_report",
    ]

    legacy = payload.get("legacy_goal_map")
    assert isinstance(legacy, dict)
    assert "GOAL-calculate-minimum-required-thickness" in legacy
    assert plan is not legacy
    assert payload.get("goals") is None


def test_fresh_plan_has_nested_structure_not_flat_goal_keys() -> None:
    _, task = fresh_pipe_wall_task(task_id="output-shape-nested")
    reader = _reader()
    plan = build_engineering_plan(task, reader)
    assert plan is not None

    assert plan.root_goal.id.startswith("GOAL-")
    assert "REQ-straight_pipe_section" in plan.requirements
    assert "REQ-pressure_design_case" in plan.requirements
    assert plan.requirements["REQ-straight_pipe_section"].key == "input-straight_pipe_section"
    assert plan.requirements["REQ-straight_pipe_section"].title
    assert len(plan.dependencies) > 0
    assert plan.input_strategy is not None
    assert plan.phases
    assert plan.graph.expanded_node_ids is not None
    assert plan.traversal is not None
    assert plan.legacy_goal_map is not None
    assert plan.root_goal.id in plan.legacy_goal_map

    payload = plan.to_dict()
    assert "GOAL-calculate-minimum-required-thickness" not in payload
    assert "requirements" in payload
    assert payload["requirements"]["REQ-straight_pipe_section"]["key"] == "input-straight_pipe_section"
    assert "legacy_goal_map" in payload
    assert "GOAL-calculate-minimum-required-thickness" in payload["legacy_goal_map"]


def test_build_legacy_goal_map_matches_embedded_adapter() -> None:
    from engine.planner.legacy_goal_adapter import build_legacy_goal_map

    _, task = fresh_pipe_wall_task(task_id="output-shape-legacy")
    reader = _reader()
    plan = build_engineering_plan(task, reader)
    assert plan is not None

    rebuilt = build_legacy_goal_map(plan)
    assert set(rebuilt.keys()) == set(plan.legacy_goal_map.keys())
    assert plan.root_goal.id in rebuilt


def test_inspection_payload_separates_canonical_plan_and_legacy_goal_map() -> None:
    manager, task = fresh_pipe_wall_task(task_id="output-shape-inspect")
    reader = _reader()
    build_goal_tree(task, reader)
    manager.replace_task(task.task_id, task)

    payload = build_inspection_payload(task, manager=manager, reader=reader)

    plan = payload.get("engineering_plan")
    assert isinstance(plan, dict)
    assert "plan_id" in plan
    assert "legacy_goal_map" in plan

    view = payload.get("engineering_plan_view")
    assert isinstance(view, dict)
    assert "overview" in view

    legacy = payload.get("legacy_goal_map")
    assert isinstance(legacy, dict)
    assert "REQ-straight_pipe_section" in legacy
    assert legacy == plan.get("legacy_goal_map")
    assert payload.get("goals") is None
