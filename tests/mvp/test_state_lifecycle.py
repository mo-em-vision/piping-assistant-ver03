"""MVP strategy §20 — state manager full lifecycle."""

from __future__ import annotations

from storage.session_store import SessionStore
from engine.executor.executor import execute_workflow
from engine.reports.report_generator import ReportGenerator
from engine.state.state_manager import TaskStateManager
from models.execution import ExecutionStatus
from models.task import TaskStatus
from tests.acceptance.helpers import (
    PIPE_WALL_THICKNESS_ROOT,
    rebuild_report_from_task,
    run_completed_workflow,
    sample_inputs,
)


class TestStateManagerLifecycle:
    """§20 State Manager — create → collect → pause → change → resume → recalculate → report."""

    def test_full_state_lifecycle(self, standards_reader, state_manager, tmp_path) -> None:
        task_id = "pipe-wall-thickness-design-mvp-state-lifecycle"

        # Create task and collect partial inputs
        state_manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        state_manager.store_input(task_id, sample_inputs()["internal_design_gage_pressure"])

        # Pause on missing input
        paused = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert paused.status == ExecutionStatus.AWAITING_INPUT

        # Collect remaining inputs
        for key, engineering_input in sample_inputs().items():
            if key != "design_pressure":
                state_manager.store_input(task_id, engineering_input)

        # Resume and recalculate
        completed = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert completed.status == ExecutionStatus.COMPLETED

        # Change input and recalculate
        original_thickness = state_manager.get_task(task_id).outputs["required_thickness"]
        state_manager.store_input(task_id, sample_inputs(temperature=400)["design_temperature"])
        execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        updated_thickness = state_manager.get_task(task_id).outputs["required_thickness"]
        assert original_thickness != updated_thickness

        # Generate report
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)
        storage = ReportGenerator(standards_reader.standards_root).generate(
            report,
            tmp_path,
            formats=("markdown",),
        )
        assert storage.markdown_path

    def test_persisted_session_supports_resume(self, standards_reader, tmp_path) -> None:
        store = SessionStore(tmp_path / "sessions", session_id="mvp")
        manager = TaskStateManager()
        task_id = "pipe-wall-thickness-design-mvp-state-persist"
        run_completed_workflow(manager, standards_reader, task_id)
        store.save_state_manager(manager)

        loaded = store.load_state_manager()
        task = loaded.get_task(task_id)
        assert task.outputs.get("required_thickness") is not None
