"""Planner-owned submittable field projection tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.workflow_bootstrap import refresh_task_planning
from api.parameter_definitions import build_parameter_definitions, submit_task_input
from api.serializers import task_state
from engine.navigation.submittable_projection import (
    legacy_submittable_parameter_ids,
    submittable_parameter_ids,
)
from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.plan_inspector import engineering_plan_from_dict
from engine.planner.plan_phases import derive_submittable_fields
from engine.planner.plan_selection import planner_submittable_fields_from_task
from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from engine.state.task_state_canonical import build_canonical_task_state
from models.engineering_plan import InputStrategy
from models.input import InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.graph.conftest import PIPE_WALL_ROOT
from tests.helpers.facts import facts_from_inputs, legacy_input, set_fact_from_input
from tests.navigation.fixtures.synthetic_nav_pack import (
    WORKFLOW_ROOT,
    build_synthetic_nav_pack,
    synthetic_gate_open_facts,
)
from tests.navigation.helpers.contracts import (
    is_planner_direct_input_requirement,
    planner_submittable_projection,
)
from engine.router import MAWP_DESIGN

_FRESH_PWT = ["design_temperature"]
_NPS_BRANCH = ["design_temperature"]
_DIRECT_OD = ["design_temperature"]
_MAWP_FRESH = ["pressure_design_case"]


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
        set_fact_from_input(task, inp)
    _refresh(task, reader)
    manager.replace_task(task.task_id, task)
    return manager, manager.get_task(task.task_id), reader


def _gatherable_fields(plan) -> set[str]:
    return {
        req.field
        for req in plan.requirements.values()
        if is_planner_direct_input_requirement(req)
    }


def test_input_strategy_submittable_fields_default_is_none() -> None:
    strategy = InputStrategy(mode="single_next_question", current_phase="parameter_gathering")
    assert strategy.submittable_fields is None


def test_input_strategy_serializes_and_deserializes_submittable_fields() -> None:
    strategy = InputStrategy(
        mode="single_next_question",
        current_phase="parameter_gathering",
        next_fields=["internal_design_gage_pressure"],
        submittable_fields=["internal_design_gage_pressure"],
    )
    payload = strategy.to_dict()
    assert payload["submittable_fields"] == ["internal_design_gage_pressure"]
    restored = engineering_plan_from_dict(
        {
            "plan_id": "PLAN-test",
            "task_id": "task-1",
            "workflow_id": "pipe_wall_thickness_design",
            "root_goal": {
                "id": "root",
                "key": "root",
                "title": "Root",
            },
            "requirements": {},
            "dependencies": [],
            "input_strategy": payload,
            "phases": [],
            "graph": {},
        }
    )
    assert restored is not None
    assert restored.input_strategy is not None
    assert restored.input_strategy.submittable_fields == ["internal_design_gage_pressure"]


def test_older_stored_plan_without_submittable_projection_reads_as_unavailable() -> None:
    manager = TaskStateManager()
    task = manager.create_task("legacy-plan", status=TaskStatus.AWAITING_INPUT)
    task.outputs["engineering_plan"] = {
        "plan_id": "PLAN-old",
        "task_id": task.task_id,
        "workflow_id": "pipe_wall_thickness_design",
        "root_goal": {"id": "root", "key": "root", "title": "Root"},
        "requirements": {},
        "dependencies": [],
        "input_strategy": {
            "mode": "single_next_question",
            "current_phase": "parameter_gathering",
            "next_fields": ["internal_design_gage_pressure"],
            "blocked_fields": [],
            "resolved_fields": [],
        },
        "phases": [],
        "graph": {},
    }
    assert planner_submittable_fields_from_task(task) is None


def test_explicit_empty_submittable_projection_is_distinct_from_missing(project_root: Path) -> None:
    _, task, reader = _pipe_wall_task(project_root, task_id="explicit-empty")
    raw = task.outputs.get("engineering_plan")
    assert isinstance(raw, dict)
    strategy = raw.get("input_strategy")
    assert isinstance(strategy, dict)
    assert "submittable_fields" in strategy
    assert planner_submittable_fields_from_task(task) == planner_submittable_projection(
        build_engineering_plan(task, reader, existing_inputs=dict(task.fact_store.active_facts()))
    )


@pytest.mark.parametrize(
    ("fixture_name", "task_id", "extra_inputs", "expected"),
    [
        ("fresh-pwt", "sub-fresh", (), _FRESH_PWT),
        (
            "nps-branch",
            "sub-nps",
            (
                legacy_input("internal_design_gage_pressure", 8.0, "bar"),
                legacy_input(
                    "outside_diameter__resolution_branch",
                    "nps_lookup",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            ),
            _NPS_BRANCH,
        ),
        (
            "direct-od",
            "sub-direct",
            (
                legacy_input(
                    "outside_diameter__resolution_branch",
                    "direct_od",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            ),
            _DIRECT_OD,
        ),
    ],
)
def test_planner_matches_legacy_normal_forward_pipe_wall(
    project_root: Path,
    fixture_name: str,
    task_id: str,
    extra_inputs: tuple,
    expected: list[str],
) -> None:
    _, task, reader = _pipe_wall_task(project_root, task_id=task_id, extra_inputs=extra_inputs)
    planning = planning_projection(task)
    plan = build_engineering_plan(task, reader, existing_inputs=dict(task.fact_store.active_facts()))
    assert plan is not None
    planner_submittable = planner_submittable_projection(plan)
    legacy = legacy_submittable_parameter_ids(task, planning)
    assert planner_submittable == expected
    assert legacy == expected
    assert set(plan.input_strategy.next_fields) <= set(planner_submittable or [])
    assert set(planner_submittable or []) <= _gatherable_fields(plan)


def test_fresh_mawp_planner_matches_legacy(project_root: Path) -> None:
    reader = _reader(project_root)
    manager = TaskStateManager()
    task = manager.create_task("sub-mawp", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN
    task.outputs["selected_root"] = MAWP_DESIGN
    _refresh(task, reader)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    planning = planning_projection(task)
    plan = build_engineering_plan(task, reader, existing_inputs=dict(task.fact_store.active_facts()))
    assert plan is not None
    assert planner_submittable_projection(plan) == _MAWP_FRESH
    assert legacy_submittable_parameter_ids(task, planning) == _MAWP_FRESH


def test_synthetic_branch_x_and_y_match_legacy(tmp_path: Path) -> None:
    reader_x, _ = build_synthetic_nav_pack(tmp_path / "x")
    facts_x = synthetic_gate_open_facts(task_id="branch-x")
    facts_x.update(
        facts_from_inputs(
            {
                "alpha_resolution__resolution_branch": legacy_input(
                    "alpha_resolution__resolution_branch",
                    "branch_x",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            },
            task_id="branch-x",
        )
    )
    manager = TaskStateManager()
    task_x = manager.create_task("branch-x", status=TaskStatus.AWAITING_INPUT)
    task_x.outputs["workflow"] = WORKFLOW_ROOT
    for fact in facts_x.values():
        manager.store_fact(task_x.task_id, fact)
    task_x = manager.get_task(task_x.task_id)
    plan_x = build_engineering_plan(task_x, reader_x, existing_inputs=dict(task_x.fact_store.active_facts()))
    assert plan_x is not None
    from engine.planner.legacy_goal_adapter import store_engineering_plan_on_task

    store_engineering_plan_on_task(task_x, plan_x)
    assert planner_submittable_projection(plan_x) == plan_x.input_strategy.next_fields
    assert planner_submittable_projection(plan_x) == ["alpha_input_x"]

    reader_y, _ = build_synthetic_nav_pack(tmp_path / "y")
    facts_y = facts_from_inputs(
        {
            "alpha_gate": legacy_input("alpha_gate", True, source=InputSource.USER, status=InputStatus.CONFIRMED),
            "alpha_path": legacy_input("alpha_path", "path_y", source=InputSource.USER, status=InputStatus.CONFIRMED),
            "alpha_resolution__resolution_branch": legacy_input(
                "alpha_resolution__resolution_branch",
                "branch_y",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="branch-y",
    )
    manager_y = TaskStateManager()
    task_y = manager_y.create_task("branch-y", status=TaskStatus.AWAITING_INPUT)
    task_y.outputs["workflow"] = WORKFLOW_ROOT
    for fact in facts_y.values():
        manager_y.store_fact(task_y.task_id, fact)
    task_y = manager_y.get_task(task_y.task_id)
    plan_y = build_engineering_plan(task_y, reader_y, existing_inputs=dict(task_y.fact_store.active_facts()))
    assert plan_y is not None
    store_engineering_plan_on_task(task_y, plan_y)
    assert planner_submittable_projection(plan_y) == plan_y.input_strategy.next_fields
    assert planner_submittable_projection(plan_y) == ["alpha_input_y"]


def test_canonical_progress_matches_planner_projection(project_root: Path) -> None:
    manager, task, reader = _pipe_wall_task(project_root, task_id="canonical-sub")
    planning = planning_projection(task)
    canonical = build_canonical_task_state(task, manager, planning=planning, reader=reader)
    planner = planner_submittable_fields_from_task(task)
    assert planner is not None
    assert canonical["progress"]["submittable_parameters"] == planner


def test_api_submission_gate_accepts_planner_submittable(project_root: Path) -> None:
    manager, task, reader = _pipe_wall_task(project_root, task_id="gate-accept")
    planning = planning_projection(task)
    submittable = planner_submittable_fields_from_task(task)
    assert submittable
    field = submittable[0]
    updated = submit_task_input(
        manager,
        task.task_id,
        parameter=field,
        value=8.0 if field == "internal_design_gage_pressure" else True,
        unit="bar" if field == "internal_design_gage_pressure" else None,
        standards_root=reader.standards_root,
    )
    assert updated is not None


def test_parameter_definitions_submittable_flags_match_planner(project_root: Path) -> None:
    manager, task, reader = _pipe_wall_task(project_root, task_id="defs-sub")
    planner = set(planner_submittable_fields_from_task(task) or [])
    definitions = build_parameter_definitions(task, reader=reader)
    for definition in definitions:
        name = definition["name"]
        if name in planner:
            assert definition["submittable"] is True
        elif definition["status"] == "pending":
            assert definition["submittable"] is False


def test_single_next_invariant_on_derive() -> None:
    from models.engineering_plan import PlanRequirement, QuestionSpec

    requirements = {
        "REQ-a": PlanRequirement(
            id="REQ-a",
            field="internal_design_gage_pressure",
            parameter_node_id=None,
            requirement_class="user_input",
            status="missing",
            phase="parameter_gathering",
            question_spec=QuestionSpec(
                field="internal_design_gage_pressure",
                label="Pressure",
                expected_value_class="pressure",
                priority=1,
                ask_policy="ask_now",
            ),
        )
    }
    submittable = derive_submittable_fields(
        requirements,
        next_fields=["internal_design_gage_pressure"],
        current_phase="parameter_gathering",
        mode="single_next_question",
    )
    assert submittable == ["internal_design_gage_pressure"]
