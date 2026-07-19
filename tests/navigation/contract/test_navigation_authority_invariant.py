"""Regression guard: navigation authority must come from EngineeringPlan on supported workflows."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from api.parameter_definitions import build_parameter_definitions
from api.serializers import task_state
from api.workflow_bootstrap import refresh_task_planning, task_ready_for_execution
from engine.navigation.submittable_projection import submittable_parameter_ids
from engine.planner.goal_navigation import build_current_ask, next_actionable_goal
from engine.planner.plan_selection import (
    planner_next_field_from_task,
    planner_submittable_fields_from_task,
)
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN, is_supported_planning_workflow
from engine.state.goal_projection import planning_projection
from storage.session_store import _task_from_dict, _task_to_dict
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.graph.conftest import PIPE_WALL_ROOT
from tests.helpers.facts import set_fact_from_input
from tests.navigation.contract.test_current_ask_ownership import _pipe_wall_task


def test_submittable_fields_have_parameter_definitions(project_root: Path) -> None:
    """Every planner submittable field must appear in composer parameter definitions."""
    manager, task, reader, _, _, planning = _pipe_wall_task(
        project_root,
        task_id="submittable-definitions",
    )

    submittable = list(submittable_parameter_ids(task, planning))
    assert submittable

    definitions = build_parameter_definitions(task, reader=reader)
    defined_ids = {str(item["name"]) for item in definitions}
    for field_id in submittable:
        assert field_id in defined_ids, f"{field_id!r} missing from parameter definitions"

    state = task_state(task, manager, reader=reader)
    api_submittable = list(state.get("progress", {}).get("submittable_parameters") or [])
    api_defined = {str(item["name"]) for item in state.get("parameters") or []}
    for field_id in api_submittable:
        assert field_id in api_defined, f"{field_id!r} missing from task_state.parameters"


def test_no_navigation_authority_outside_engineering_plan(project_root: Path) -> None:
    """Supported workflows must not derive ask/submittable/execution gate from goal_store alone."""
    manager, task, reader, _, plan, planning = _pipe_wall_task(
        project_root,
        task_id="authority-invariant",
    )

    planner_next = planner_next_field_from_task(task)
    assert planner_next is not None

    roots = task.goal_store.roots()
    assert roots
    for child in list(task.goal_store.children(roots[0].id)):
        task.goal_store.goals.pop(child.id, None)

    goal_next = next_actionable_goal(task)
    if goal_next is not None:
        assert goal_next.key != f"input-{planner_next}"

    ask = build_current_ask(task, planning, reader=reader)
    assert ask is not None
    assert ask.get("kind") == "input"
    assert ask.get("parameter_id") == planner_next

    planner_submittable = planner_submittable_fields_from_task(task) or []
    submittable = submittable_parameter_ids(task, planning)
    assert planner_next in submittable
    assert set(planner_submittable).issubset(set(submittable))

    state = task_state(task, manager, reader=reader)
    assert state.get("current_ask", {}).get("parameter_id") == planner_next

    assert task_ready_for_execution(task) is False


def test_lightweight_refresh_syncs_goal_store_projection(project_root: Path, monkeypatch) -> None:
    from engine.planning import planning_refresh as planning_refresh_module

    manager, task, reader, _, _, _ = _pipe_wall_task(
        project_root,
        task_id="lightweight-sync",
    )
    before_children = len(task.goal_store.goals)

    monkeypatch.setattr(
        planning_refresh_module,
        "structure_unchanged_for_skip",
        lambda *_args, **_kwargs: True,
    )
    refresh_task_planning(task, reader, propose_defaults=False, allow_lightweight_refresh=True)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)

    from engine.planning.plan_projection_sync import plan_projection_is_consistent

    assert plan_projection_is_consistent(task)
    assert len(task.goal_store.goals) >= before_children - 1


def test_save_load_navigation_parity(project_root: Path) -> None:
    manager, task, reader, _, _, planning = _pipe_wall_task(
        project_root,
        task_id="save-load-parity",
    )

    before_ask = build_current_ask(task, planning, reader=reader)
    before_submittable = list(submittable_parameter_ids(task, planning))

    restored = _task_from_dict(_task_to_dict(task))
    restored_planning = planning_projection(restored)
    after_ask = build_current_ask(restored, restored_planning, reader=reader)
    after_submittable = list(submittable_parameter_ids(restored, restored_planning))

    assert before_ask == after_ask
    assert before_submittable == after_submittable


@pytest.mark.parametrize(
    ("module_path", "forbidden_name"),
    [
        ("engine.planner.goal_navigation", "next_actionable_goal"),
    ],
)
def test_stored_plan_current_ask_does_not_call_forbidden_navigation(
    module_path: str,
    forbidden_name: str,
) -> None:
    import importlib

    module = importlib.import_module(module_path)
    source = inspect.getsource(module._build_stored_plan_current_ask)
    assert forbidden_name not in source


def test_supported_workflow_registry_single_source() -> None:
    from api import workflow_bootstrap
    from engine.router import supported_planning_workflows

    assert workflow_bootstrap._SUPPORTED_PLANNING_WORKFLOWS == supported_planning_workflows()


def test_is_supported_planning_workflow_matches_router() -> None:
    from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN, is_supported_planning_workflow

    assert is_supported_planning_workflow(PIPE_WALL_ROOT)
    assert is_supported_planning_workflow(PIPE_WALL_THICKNESS_DESIGN)
    assert is_supported_planning_workflow(MAWP_DESIGN)
    assert not is_supported_planning_workflow("unknown_workflow")
