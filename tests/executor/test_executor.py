"""Executor integration tests."""

from __future__ import annotations

from pathlib import Path

from engine.executor.executor import execute_workflow
from engine.reports.report_data import build_report_from_task
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.execution import ExecutionStatus
from models.input import EngineeringInput, InputSource
from models.task import TaskStatus
from tests.acceptance.helpers import sample_inputs as _sample_inputs
from tests.helpers.facts import fact_get_value, legacy_input
from engine.state.fact_migration import fact_from_engineering_input
from models.fact import SourceType, ValidationStatus


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_execute_workflow_completes() -> None:
    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-design-exec"
    manager.create_task(task_id)
    for engineering_input in _sample_inputs().values():
        manager.store_input(task_id, engineering_input)

    result = execute_workflow(
        task_id,
        "pipe_wall_thickness_design",
        state=manager,
        reader=_reader(),
    )

    assert result.status == ExecutionStatus.COMPLETED
    task = manager.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED
    assert task.outputs.get("required_thickness") is not None
    assert task.outputs.get("allowable_stress") == 193_000_000.0
    assert isinstance(task.outputs.get("_execution_trace"), list)
    assert len(result.node_results) >= 2
    lifecycle = task.outputs.get("_lifecycle_events")
    assert isinstance(lifecycle, list)
    assert lifecycle
    event_names = [item["event"] for item in lifecycle]
    assert "beforeEnter" in event_names
    assert "onExecute" in event_names
    assert "onExit" in event_names
    assert event_names.index("beforeEnter") < event_names.index("onExecute")
    assert event_names.index("onExecute") < event_names.index("onExit")
    assert result.lifecycle_events == lifecycle


def test_execute_workflow_pauses_on_missing_input() -> None:
    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-design-pause"
    manager.create_task(task_id)
    manager.store_input(
        task_id, fact_from_engineering_input(legacy_input(input_id="design_pressure",
            value=500,
            unit="psi",
            source=InputSource.USER,
        ),
    )

    result = execute_workflow(
        task_id,
        "pipe_wall_thickness_design",
        state=manager,
        reader=_reader(),
    )

    assert result.status == ExecutionStatus.AWAITING_INPUT
    assert manager.get_task(task_id).status == TaskStatus.AWAITING_INPUT
    lifecycle = manager.get_task(task_id).outputs.get("_lifecycle_events")
    if isinstance(lifecycle, list) and lifecycle:
        blocked = lifecycle[-1]["node_id"]
        node_events = [item for item in lifecycle if item["node_id"] == blocked]
        names = [item["event"] for item in node_events]
        assert "beforeEnter" in names
        assert "onEnter" in names
        assert "onExit" not in names


def test_report_reflects_execution_outputs() -> None:
    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-design-report"
    manager.create_task(task_id)
    for engineering_input in _sample_inputs().values():
        manager.store_input(task_id, engineering_input)

    execute_workflow(task_id, "pipe_wall_thickness_design", state=manager, reader=_reader(), task_id=
        task_id, workflow_id=str(manager.get_task(
        task_id).outputs.get('workflow') or '')))
    task = manager.get_task(task_id)
    report = build_report_from_task(task, _reader())

    assert report.status == "PASS"
    assert report.sections[0].outputs.get("required_thickness") is not None
    assert len(report.traversal) >= 1
