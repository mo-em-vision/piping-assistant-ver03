"""Phase 3 — persisted navigation cache removal contract tests."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from api.serializers import task_state
from api.workflow_bootstrap import refresh_task_planning
from engine.inspection.builder import build_inspection_payload
from engine.navigation.submittable_projection import submittable_parameter_ids
from engine.planner.goal_navigation import build_current_ask
from engine.planner.plan_inspector import (
    engineering_plan_view_for_task,
    planner_inspector_summary_for_task,
)
from engine.planner.plan_selection import planner_next_field_from_task
from engine.reference.standards_reader import StandardsReader
from engine.router import MAWP_DESIGN
from engine.state.goal_projection import goal_summary_dict, planning_projection
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from storage.session_store import _DEPRECATED_NAVIGATION_CACHE_KEYS, _task_from_dict, _task_to_dict
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.graph.conftest import PIPE_WALL_ROOT
from tests.helpers.facts import set_fact_from_input
from tests.navigation.contract.test_current_ask_ownership import _pipe_wall_task

_FAKE_CACHE_FIELD = "fake_cache_field_injected"


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _mawp_task(project_root: Path, *, task_id: str = "cache-removal-mawp"):
    manager = TaskStateManager()
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN
    task.outputs["selected_root"] = MAWP_DESIGN
    reader = _reader(project_root)
    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    planning = planning_projection(task)
    return manager, task, reader, planning


def _inject_fake_navigation_caches(task) -> str:
    real_field = planner_next_field_from_task(task)
    assert real_field is not None
    task.outputs["graph_navigation"] = {
        "active_field": _FAKE_CACHE_FIELD,
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": [_FAKE_CACHE_FIELD]},
        "missing_user_inputs": [_FAKE_CACHE_FIELD],
        "warnings": [],
    }
    task.outputs["engineering_plan_view"] = {
        "overview": {"goal": "FAKE GOAL"},
        "next_input": {"field": _FAKE_CACHE_FIELD, "label": "Fake input"},
        "phases": [],
    }
    task.outputs["planner_inspector_summary"] = {
        "next_input": {"field": _FAKE_CACHE_FIELD, "label": "Fake input"},
        "current_phase": "parameter_gathering",
        "root_goal": {"title": "FAKE"},
    }
    return real_field


def _simulate_old_task_load(task) -> Any:
    """Load a task payload that still carries deprecated cache keys (pre-migration file)."""
    payload = copy.deepcopy(_task_to_dict(task))
    for key in _DEPRECATED_NAVIGATION_CACHE_KEYS:
        if key in task.outputs:
            payload["outputs"][key] = copy.deepcopy(task.outputs[key])
    return _task_from_dict(payload)


def _task_state_navigation_slice(state: dict[str, Any]) -> dict[str, Any]:
    progress = state.get("progress") or {}
    workflow_state = state.get("workflow_state") or {}
    return {
        "current_ask": state.get("current_ask"),
        "submittable_parameters": list(progress.get("submittable_parameters") or []),
        "timeline": progress.get("timeline"),
        "current_step_id": progress.get("current_step_id"),
        "missing_inputs": list(progress.get("missing_inputs") or []),
        "workflow_current_node": workflow_state.get("current_node"),
        "workflow_visited_nodes": workflow_state.get("visited_nodes"),
        "status": state.get("status"),
    }


def test_removed_navigation_caches_are_not_authoritative(project_root: Path) -> None:
    manager, task, reader, _, _, planning = _pipe_wall_task(
        project_root,
        task_id="cache-not-authoritative",
    )
    real_field = _inject_fake_navigation_caches(task)

    restored = _simulate_old_task_load(task)
    restored_planning = planning_projection(restored)

    ask = build_current_ask(restored, restored_planning, reader=reader)
    assert ask is not None
    assert ask.get("parameter_id") == real_field
    assert ask.get("parameter_id") != _FAKE_CACHE_FIELD

    submittable = list(submittable_parameter_ids(restored, restored_planning))
    assert real_field in submittable
    assert _FAKE_CACHE_FIELD not in submittable

    expected_summary = goal_summary_dict(restored)
    assert restored_planning.get("current_phase") == expected_summary.get("current_phase")
    assert restored_planning.get("phase_missing") == expected_summary.get("phase_missing")
    assert restored_planning.get("missing_inputs") == expected_summary.get("missing_inputs")

    view = restored_planning.get("engineering_plan_view") or {}
    overview = view.get("overview") or {}
    next_input = overview.get("next_input") or view.get("next_input") or {}
    assert next_input.get("field") == real_field

    summary = restored_planning.get("planner_inspector_summary") or {}
    assert (summary.get("next_input") or {}).get("field") == real_field

    state = task_state(restored, manager, reader=reader)
    assert state.get("current_ask", {}).get("parameter_id") == real_field
    assert "graph_navigation" not in (state.get("outputs") or {})


def test_cache_stripped_task_state_parity_pipe_wall(project_root: Path) -> None:
    manager, task, reader, _, _, _ = _pipe_wall_task(
        project_root,
        task_id="parity-pipe-wall",
    )
    before = _task_state_navigation_slice(task_state(task, manager, reader=reader))

    for key in _DEPRECATED_NAVIGATION_CACHE_KEYS:
        task.outputs.pop(key, None)
    restored = _task_from_dict(_task_to_dict(task))
    after = _task_state_navigation_slice(task_state(restored, manager, reader=reader))

    assert before == after


def test_cache_stripped_task_state_parity_mawp(project_root: Path) -> None:
    manager, task, reader, _ = _mawp_task(
        project_root,
        task_id="parity-mawp",
    )
    before = _task_state_navigation_slice(task_state(task, manager, reader=reader))

    for key in _DEPRECATED_NAVIGATION_CACHE_KEYS:
        task.outputs.pop(key, None)
    restored = _task_from_dict(_task_to_dict(task))
    after = _task_state_navigation_slice(task_state(restored, manager, reader=reader))

    assert before == after


@pytest.mark.parametrize("fixture_name", ["pipe_wall", "mawp"])
def test_inspection_projection_parity_after_cache_strip(
    project_root: Path,
    fixture_name: str,
) -> None:
    if fixture_name == "pipe_wall":
        manager, task, reader, _, _, _ = _pipe_wall_task(
            project_root,
            task_id=f"inspect-parity-{fixture_name}",
        )
    else:
        manager, task, reader, _ = _mawp_task(
            project_root,
            task_id=f"inspect-parity-{fixture_name}",
        )

    before_view = engineering_plan_view_for_task(task)
    before_summary = planner_inspector_summary_for_task(task)
    assert isinstance(before_view, dict)
    assert isinstance(before_summary, dict)

    for key in _DEPRECATED_NAVIGATION_CACHE_KEYS:
        task.outputs.pop(key, None)
    restored = _task_from_dict(_task_to_dict(task))

    after_view = engineering_plan_view_for_task(restored)
    after_summary = planner_inspector_summary_for_task(restored)
    assert after_view == before_view
    assert after_summary == before_summary

    inspection = build_inspection_payload(restored, manager=manager, reader=reader)
    assert inspection.get("engineering_plan_view") == before_view
    assert inspection.get("planner_inspector_summary") == before_summary


def test_deprecated_cache_keys_stripped_on_save(project_root: Path) -> None:
    manager, task, reader, _, _, _ = _pipe_wall_task(
        project_root,
        task_id="save-strip-caches",
    )
    _inject_fake_navigation_caches(task)

    serialized = _task_to_dict(task)
    for key in _DEPRECATED_NAVIGATION_CACHE_KEYS:
        assert key not in serialized.get("outputs", {})


def test_fresh_refresh_does_not_persist_navigation_caches(project_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("fresh-no-caches", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = _reader(project_root)
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        set_fact_from_input(task, inp)
    refresh_task_planning(task, reader, propose_defaults=False)

    for key in _DEPRECATED_NAVIGATION_CACHE_KEYS:
        assert key not in task.outputs
    assert isinstance(task.outputs.get("engineering_plan"), dict)
