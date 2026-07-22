"""Timeline completion must use facts and plan resolution, not calculation outputs."""

from __future__ import annotations

from pathlib import Path

from api.serializers import task_state
from api.workflow_timeline import workflow_input_step_done
from api.workflow_bootstrap import refresh_task_planning
from engine.navigation.submittable_projection import submittable_parameter_ids
from engine.planner.goal_navigation import build_current_ask
from engine.planner.plan_selection import planner_next_field_from_task
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.helpers.facts import legacy_input, set_fact_from_input
from tests.navigation.contract.test_current_ask_ownership import _pipe_wall_task


def test_timeline_done_requires_fact_or_plan_resolution(project_root: Path) -> None:
    """Calculation output alone must not mark a timeline input step done."""
    manager, task, reader, _, _, planning = _pipe_wall_task(
        project_root,
        task_id="timeline-fact-only",
    )
    all_missing = set(planning.get("missing_inputs") or [])

    task.outputs["allowable_stress"] = 193_000_000.0
    task.outputs["S"] = 193_000_000.0
    assert not workflow_input_step_done(task, "allowable_stress", all_missing)

    set_fact_from_input(
        task,
        legacy_input("allowable_stress", 193_000_000.0, "Pa"),
    )
    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    planning = planning_projection(task)
    all_missing = set(planning.get("missing_inputs") or [])

    assert workflow_input_step_done(task, "allowable_stress", all_missing)


def test_step_progress_cannot_change_navigation_state(project_root: Path) -> None:
    """Identical plan/facts/trace with different step_progress → same navigation."""
    manager_a, task_a, reader, _, _, planning_a = _pipe_wall_task(
        project_root,
        task_id="step-progress-a",
    )
    manager_b, task_b, _, _, _, planning_b = _pipe_wall_task(
        project_root,
        task_id="step-progress-b",
    )

    trace = list(task_a.outputs.get("_execution_trace") or [])
    task_b.outputs["_execution_trace"] = trace
    manager_b.replace_task(task_b.task_id, task_b)

    manager_a.store_step_progress(task_a.task_id, "304.1.2-a", "completed")
    manager_b.store_step_progress(task_b.task_id, "ghost-node", "completed")
    manager_b.store_step_progress(task_b.task_id, "other-node", "running")

    ask_a = build_current_ask(task_a, planning_a, reader=reader)
    ask_b = build_current_ask(task_b, planning_b, reader=reader)
    assert ask_a == ask_b

    sub_a = submittable_parameter_ids(task_a, planning_a)
    sub_b = submittable_parameter_ids(task_b, planning_b)
    assert sub_a == sub_b

    assert planner_next_field_from_task(task_a) == planner_next_field_from_task(task_b)

    state_a = task_state(task_a, manager_a, reader=reader)
    state_b = task_state(task_b, manager_b, reader=reader)
    assert state_a.get("current_ask") == state_b.get("current_ask")
    assert (state_a.get("workflow_state") or {}).get("visited_nodes") == (
        state_b.get("workflow_state") or {}
    ).get("visited_nodes")


def test_workflow_state_visited_nodes_use_execution_trace(project_root: Path) -> None:
    """visited_nodes follow execution trace, not step_progress telemetry."""
    manager = TaskStateManager()
    task = manager.create_task("visited-trace", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["_execution_trace"] = [
        {"node_id": "node-alpha"},
        {"node_id": "node-beta"},
    ]
    manager.replace_task(task.task_id, task)
    manager.store_step_progress(task.task_id, "telemetry-only", "completed")

    reader_path = project_root / "knowledge" / "standards"
    from engine.reference.standards_reader import StandardsReader

    reader = StandardsReader(reader_path, standard="asme_b31.3")
    workflow_state = manager.get_workflow_state(task.task_id, reader=reader)

    assert workflow_state.visited_nodes == ("node-alpha", "node-beta")
    assert "telemetry-only" not in workflow_state.visited_nodes
