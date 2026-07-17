"""Pipe wall navigation characterization tests."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.navigation import collection_step_order
from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.plan_selection import planner_next_field_from_task
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from models.input import InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.api.conftest import api_session_id
from tests.api.test_current_ask import (
    _advance_pipe_wall_to_nominal_pipe_size,
    _assert_timeline_follows_collection_field_order,
    _timeline_input_ids,
)
from tests.graph.conftest import PIPE_WALL_ROOT
from tests.helpers.facts import facts_from_inputs, legacy_input
from tests.navigation.helpers.contracts import api_current_ask_parameter


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _pipe_wall_task_with_direct_od(project_root: Path):
    manager = TaskStateManager()
    task = manager.create_task("nav-char-direct-od", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = _reader(project_root)
    for inp in (
        straight_section_assumption(),
        internal_pressure_assumption(),
        legacy_input(
            "outside_diameter__resolution_branch",
            "direct_od",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    ):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id=PIPE_WALL_ROOT,
            ),
        )
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())
    return manager, task, reader, facts


def test_pipe_wall_direct_od_hides_nps_branch_inputs(project_root: Path) -> None:
    manager, task, reader, facts = _pipe_wall_task_with_direct_od(project_root)
    graph = GraphTools(reader)
    missing = graph.required_user_inputs(
        PIPE_WALL_ROOT,
        existing_inputs=set(facts.keys()),
        task_inputs=facts,
    )
    assert "nominal_pipe_size" not in missing
    assert "pipe_schedule" not in missing

    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None
    assert plan.input_strategy is not None
    next_field = plan.input_strategy.next_fields[0] if plan.input_strategy.next_fields else None
    assert next_field not in {"nominal_pipe_size", "pipe_schedule"}

    current_ask = api_current_ask_parameter(task, manager, reader=reader)
    assert current_ask not in {"nominal_pipe_size", "pipe_schedule"}


def test_pipe_wall_corrosion_not_requested_before_primary_thickness_execution(
    project_root: Path,
) -> None:
    manager = TaskStateManager()
    task = manager.create_task("nav-char-corrosion-timing", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = _reader(project_root)

    inputs = [
        straight_section_assumption(),
        internal_pressure_assumption(),
        legacy_input("internal_design_gage_pressure", 8.0, "bar"),
        legacy_input("outside_diameter__resolution_branch", "direct_od"),
        legacy_input("outside_diameter", 168.28, "mm"),
        legacy_input("material_grade", "SA-106 B"),
        legacy_input("design_temperature", 38.0, "C"),
        legacy_input("pipe_construction_type", "seamless"),
    ]
    for inp in inputs:
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id=PIPE_WALL_ROOT,
            ),
        )
    task = manager.get_task(task.task_id)
    facts = dict(task.fact_store.active_facts())

    plan = build_engineering_plan(task, reader, existing_inputs=facts)
    assert plan is not None
    assert plan.input_strategy is not None
    next_field = plan.input_strategy.next_fields[0] if plan.input_strategy.next_fields else None
    assert next_field != "corrosion_allowance"

    from api.workflow_bootstrap import refresh_task_planning
    from engine.state.task_state_canonical import build_canonical_task_state

    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    planning = planning_projection(task)
    canonical_ask = api_current_ask_parameter(task, manager, reader=reader, planning=planning)
    assert canonical_ask != "corrosion_allowance"

    canonical = build_canonical_task_state(task, manager, planning=planning, reader=reader)
    api_submittable = set(canonical.get("progress", {}).get("submittable_parameters") or [])
    assert "corrosion_allowance" not in api_submittable


def _pipe_wall_service(tmp_path: Path, project_root: Path) -> DesktopApiService:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def test_pipe_wall_timeline_presentation_order_is_independent_from_current_ask(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Planner ask, active timeline row, and presentation ordering are separate contracts."""
    service = _pipe_wall_service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = _advance_pipe_wall_to_nominal_pipe_size(service, session_id)

    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(state["task_id"])
    reader = service._reader()
    planning = planning_projection(task)

    planner_next = planner_next_field_from_task(task)
    assert planner_next == "nominal_pipe_size"

    current_ask = state.get("current_ask") or {}
    assert current_ask.get("parameter_id") == "nominal_pipe_size"
    assert api_current_ask_parameter(task, manager, reader=reader, planning=planning) == "nominal_pipe_size"

    timeline = state["progress"]["timeline"]
    active_steps = [
        step
        for step in timeline
        if step.get("status") == "active" and step["id"] not in {"thickness", "report"}
    ]
    assert active_steps[0]["id"] == "nominal_pipe_size"
    assert state["progress"]["current_step_id"] == "nominal_pipe_size"

    input_ids = _timeline_input_ids(state)
    collection_field_order = list(
        task.outputs.get("collection_field_order")
        or collection_step_order(task, planning, reader=reader)
    )
    _assert_timeline_follows_collection_field_order(
        timeline_ids=input_ids,
        collection_field_order=collection_field_order,
    )
    assert input_ids.index("design_temperature") < input_ids.index("nominal_pipe_size")
