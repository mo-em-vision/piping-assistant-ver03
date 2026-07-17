"""Navigation determinism characterization tests."""

from __future__ import annotations

from pathlib import Path

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.graph.conftest import PIPE_WALL_ROOT
from tests.navigation.helpers.contracts import (
    graph_active_direct_inputs,
    navigation_projection,
    planner_active_direct_inputs,
)


def _deterministic_task(project_root: Path):
    from engine.reference.standards_reader import StandardsReader

    manager = TaskStateManager()
    task = manager.create_task("nav-determinism", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
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


def test_identical_facts_produce_identical_navigation_projection(project_root: Path) -> None:
    from api.workflow_bootstrap import refresh_task_planning

    manager, task, reader, facts = _deterministic_task(project_root)

    plan_a = build_engineering_plan(task, reader, existing_inputs=facts)
    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    projection_a = navigation_projection(
        task,
        manager,
        reader,
        root_id=PIPE_WALL_ROOT,
        facts=facts,
        plan=plan_a,
    )

    plan_b = build_engineering_plan(task, reader, existing_inputs=facts)
    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    projection_b = navigation_projection(
        task,
        manager,
        reader,
        root_id=PIPE_WALL_ROOT,
        facts=facts,
        plan=plan_b,
    )

    assert projection_a == projection_b
    assert set(projection_a["graph_active_direct_inputs"]) == graph_active_direct_inputs(
        reader,
        PIPE_WALL_ROOT,
        facts=facts,
    )
    assert planner_active_direct_inputs(plan_a) == planner_active_direct_inputs(plan_b)
