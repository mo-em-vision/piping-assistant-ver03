"""Planner-owned current ask with submittable compatibility tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.serializers import task_state
from api.workflow_bootstrap import refresh_task_planning
from engine.navigation.submittable_projection import submittable_parameter_ids
from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.plan_phases import _is_askable_requirement
from engine.planner.plan_selection import (
    planner_next_field_from_task,
    planner_next_field_is_submittable,
)
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.router import MAWP_DESIGN
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from engine.state.task_state_canonical import build_canonical_task_state
from models.input import InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.graph.conftest import PIPE_WALL_ROOT
from tests.helpers.facts import legacy_input
from tests.helpers.goals import task_with_planning
from tests.navigation.helpers.contracts import graph_active_direct_inputs, planner_next_field


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _refresh(task, reader: StandardsReader) -> None:
    refresh_task_planning(task, reader, propose_defaults=False)


def _pipe_wall_task(
    project_root: Path,
    *,
    task_id: str,
    extra_inputs: tuple = (),
):
    manager = TaskStateManager()
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = _reader(project_root)
    for inp in (straight_section_assumption(), internal_pressure_assumption(), *extra_inputs):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id=PIPE_WALL_ROOT,
            ),
        )
    task = manager.get_task(task.task_id)
    _refresh(task, reader)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    planning = planning_projection(task)
    return manager, task, reader, facts, plan, planning


def test_nps_lookup_key_is_planner_askable(project_root: Path) -> None:
    _, task, reader, facts, plan, _ = _pipe_wall_task(
        project_root,
        task_id="askability-nps",
        extra_inputs=(
            legacy_input("internal_design_gage_pressure", 8.0, "bar"),
            legacy_input(
                "outside_diameter__resolution_branch",
                "nps_lookup",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        ),
    )
    assert plan is not None
    graph_fields = graph_active_direct_inputs(reader, PIPE_WALL_ROOT, facts=facts)
    assert "nominal_pipe_size" in graph_fields

    nps_req = plan.requirements.get("REQ-nominal_pipe_size")
    assert nps_req is not None
    assert nps_req.requirement_class == "user_input"
    assert nps_req.question_spec is not None
    assert nps_req.status == "missing"
    assert nps_req.activation_status == "active"
    assert _is_askable_requirement(nps_req) is True

    od_lookup = plan.requirements.get("REQ-outside_diameter_lookup")
    if od_lookup is not None:
        assert _is_askable_requirement(od_lookup) is False


@pytest.mark.parametrize(
    ("fixture_id", "extra_inputs", "has_execution"),
    [
        ("fresh_pipe_wall", (), False),
        ("pipe_wall_gates_open", (), False),
        (
            "pipe_wall_nps_branch",
            (
                legacy_input("internal_design_gage_pressure", 8.0, "bar"),
                legacy_input(
                    "outside_diameter__resolution_branch",
                    "nps_lookup",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            ),
            False,
        ),
        (
            "pipe_wall_direct_od",
            (
                legacy_input(
                    "outside_diameter__resolution_branch",
                    "direct_od",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            ),
            False,
        ),
    ],
)
def test_planner_next_is_submittable_for_pipe_wall_fixtures(
    project_root: Path,
    fixture_id: str,
    extra_inputs: tuple,
    has_execution: bool,
) -> None:
    del fixture_id, has_execution
    _, task, _, _, plan, planning = _pipe_wall_task(
        project_root,
        task_id="submittable-compat-pwt",
        extra_inputs=extra_inputs,
    )
    assert plan is not None
    planner_next = planner_next_field(plan)
    if planner_next is None:
        pytest.skip("no planner next field at this fixture state")
    submittable = submittable_parameter_ids(task, planning)
    assert planner_next in submittable
    assert planner_next_field_is_submittable(task, planning) is True


def test_nps_branch_current_ask_matches_planner_and_submittable(project_root: Path) -> None:
    manager, task, reader, _, plan, planning = _pipe_wall_task(
        project_root,
        task_id="ownership-nps",
        extra_inputs=(
            legacy_input("internal_design_gage_pressure", 8.0, "bar"),
            legacy_input(
                "outside_diameter__resolution_branch",
                "nps_lookup",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        ),
    )
    assert plan is not None
    planner_next = planner_next_field(plan)
    assert planner_next is not None
    submittable = submittable_parameter_ids(task, planning)
    assert planner_next in submittable

    state = task_state(task, manager, reader=reader)
    api_ask = (state.get("current_ask") or {}).get("parameter_id")
    canonical = build_canonical_task_state(task, manager, planning=planning, reader=reader)
    blocker_field = (canonical.get("execution") or {}).get("current_blocker", {}).get("field")

    assert api_ask == planner_next
    assert blocker_field == planner_next
    assert api_ask in submittable


@pytest.mark.parametrize(
    ("fixture_id", "extra_inputs"),
    [
        ("fresh_pipe_wall", ()),
        ("pipe_wall_gates_open", ()),
        (
            "pipe_wall_direct_od",
            (
                legacy_input(
                    "outside_diameter__resolution_branch",
                    "direct_od",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            ),
        ),
    ],
)
def test_supported_workflows_current_ask_matches_planner_next(
    project_root: Path,
    fixture_id: str,
    extra_inputs: tuple,
) -> None:
    del fixture_id
    manager, task, reader, _, plan, _ = _pipe_wall_task(
        project_root,
        task_id="ownership-pwt",
        extra_inputs=extra_inputs,
    )
    assert plan is not None
    planner_next = planner_next_field(plan)
    assert planner_next is not None
    state = task_state(task, manager, reader=reader)
    api_ask = (state.get("current_ask") or {}).get("parameter_id")
    assert api_ask == planner_next


def test_post_execution_corrosion_current_ask_matches_planner(project_root: Path) -> None:
    from tests.engine.test_task_state_canonical import _pipe_wall_post_calc_task

    manager = TaskStateManager()
    task, reader = _pipe_wall_post_calc_task(manager, "ownership-corrosion", project_root=project_root)
    planning = planning_projection(task)
    planner_next = planner_next_field_from_task(task)
    assert planner_next == "corrosion_allowance"
    assert planner_next in submittable_parameter_ids(task, planning)
    state = task_state(task, manager, reader=reader)
    assert (state.get("current_ask") or {}).get("parameter_id") == planner_next


def test_fresh_mawp_current_ask_matches_planner(project_root: Path) -> None:
    reader = _reader(project_root)
    manager = TaskStateManager()
    task = manager.create_task("ownership-mawp-fresh", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN
    task.outputs["selected_root"] = MAWP_DESIGN
    _refresh(task, reader)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None
    planner_next = planner_next_field(plan)
    assert planner_next is not None
    planning = planning_projection(task)
    assert planner_next in submittable_parameter_ids(task, planning)
    state = task_state(task, manager, reader=reader)
    assert (state.get("current_ask") or {}).get("parameter_id") == planner_next


def test_mawp_nps_geometry_path_current_ask_matches_planner(project_root: Path) -> None:
    reader = _reader(project_root)
    manager = TaskStateManager()
    task = manager.create_task("ownership-mawp-nps", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN
    task.outputs["selected_root"] = MAWP_DESIGN
    manager.store_fact(
        task.task_id,
        fact_from_engineering_input(
            legacy_input(
                "outside_diameter__resolution_branch",
                "nps_lookup",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id=task.task_id,
            workflow_id=MAWP_DESIGN,
        ),
    )
    task = manager.get_task(task.task_id)
    _refresh(task, reader)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())
    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None
    planner_next = planner_next_field(plan)
    assert planner_next is not None
    planning = planning_projection(task)
    assert planner_next in submittable_parameter_ids(task, planning)
    state = task_state(task, manager, reader=reader)
    assert (state.get("current_ask") or {}).get("parameter_id") == planner_next


def test_prompt_stable_when_planner_and_goal_already_agreed(project_root: Path) -> None:
    manager, task, reader, _, plan, planning = _pipe_wall_task(
        project_root,
        task_id="prompt-stable",
        extra_inputs=(),
    )
    assert plan is not None
    from engine.planner.goal_navigation import build_current_ask, next_actionable_goal
    from models.goal import goal_parameter_key

    goal = next_actionable_goal(task)
    assert goal is not None
    assert goal_parameter_key(goal) == planner_next_field(plan)

    ask_before = build_current_ask(task, planning, reader=reader)
    assert ask_before is not None
    state = task_state(task, manager, reader=reader)
    ask_after = state.get("current_ask")
    assert ask_after is not None
    assert ask_after.get("kind") == ask_before.get("kind")
    assert ask_after.get("parameter_id") == ask_before.get("parameter_id")
    assert ask_after.get("prompt") == ask_before.get("prompt")
    assert ask_after.get("short_prompt") == ask_before.get("short_prompt")


def test_no_plan_task_preserves_legacy_current_ask() -> None:
    manager = TaskStateManager()
    task = manager.create_task("legacy-no-plan", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_assumptions": ["pressure_design_case"],
        "current_phase": "path_decisions",
        "phase_missing": {"path_decisions": ["pressure_design_case"]},
        "phase_questions": {
            "path_decisions": {
                "pressure_design_case": "Is the pipe subjected to internal or external pressure?",
            }
        },
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)
    state = task_state(manager.get_task(task.task_id), manager)
    current_ask = state.get("current_ask")
    assert current_ask is not None
    assert current_ask["kind"] == "input"
    assert current_ask["parameter_id"] == "pressure_design_case"


def test_completed_task_has_no_parameter_current_ask(project_root: Path) -> None:
    reader = _reader(project_root)
    manager = TaskStateManager()
    task = manager.create_task("completed", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    state = task_state(task, manager, reader=reader)
    assert state.get("current_ask") is None


def test_waiting_ready_phase_has_no_parameter_current_ask(project_root: Path) -> None:
    manager, task, reader, _, _, _ = _pipe_wall_task(
        project_root,
        task_id="waiting-ready",
        extra_inputs=(
            legacy_input("internal_design_gage_pressure", 8.0, "bar"),
            legacy_input(
                "outside_diameter__resolution_branch",
                "direct_od",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            legacy_input("outside_diameter", 168.28, "mm"),
            legacy_input("material_grade", "SA-106 B"),
            legacy_input("design_temperature", 38.0, "C"),
            legacy_input("pipe_construction_type", "seamless"),
        ),
    )
    planning = planning_projection(task)
    if planning.get("current_phase") != "ready":
        pytest.skip("fixture did not reach ready phase without execution")
    state = task_state(task, manager, reader=reader)
    assert (state.get("current_ask") or {}).get("parameter_id") is None
