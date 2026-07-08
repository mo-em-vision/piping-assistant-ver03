"""Acceptance criteria §11, §12, and §23 — state handling and storage."""

from __future__ import annotations

from storage.session_store import SessionStore
from engine.executor.executor import execute_workflow
from engine.reports.report_generator import ReportGenerator
from models.execution import ExecutionStatus
from models.task import TaskStatus
from tests.acceptance.helpers import (
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus
    PIPE_WALL_THICKNESS_ROOT,
    rebuild_report_from_task,
    run_completed_workflow,
    sample_inputs,
)


class TestTaskStateHandling:
    """§11 Task State Handling — preserve active task, inputs, and traversal; resume after interrupt."""

    def test_preserves_active_task_and_inputs(self, state_manager) -> None:
        task_id = "acceptance-state-preserve"
        state_manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        state_manager.store_input(task_id, sample_inputs()["internal_design_gage_pressure"])

        active = state_manager.get_active_task()
        assert active is not None
        assert active.task_id == task_id
        assert "design_pressure" in active.inputs

    def test_can_resume_after_missing_input_interrupt(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "acceptance-state-resume"
        state_manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        state_manager.store_input(task_id, sample_inputs()["internal_design_gage_pressure"])

        paused = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert paused.status == ExecutionStatus.AWAITING_INPUT

        for engineering_input in sample_inputs().values():
            state_manager.store_input(task_id, engineering_input)

        resumed = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert resumed.status == ExecutionStatus.COMPLETED
        assert state_manager.get_task(task_id).status == TaskStatus.COMPLETED


class TestChangedInputsAcceptance:
    """§12 Changed Inputs — detect changes, record conflicts, recalculate dependents."""

    def test_input_change_records_conflict_and_recalculates(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "acceptance-state-change"
        run_completed_workflow(state_manager, standards_reader, task_id)
        original_stress = state_manager.get_task(task_id).outputs["allowable_stress"]

        state_manager.store_input(task_id, sample_inputs(temperature=400)["design_temperature"])
        task = state_manager.get_task(task_id)
        assert any(conflict.input_id == "design_temperature" for conflict in task.conflicts)

        execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        updated_stress = state_manager.get_task(task_id).outputs["allowable_stress"]
        assert original_stress != updated_stress
        assert task.conflicts


class TestStorageAcceptance:
    """§23 Storage Acceptance — versioning, replay, and audit queries."""

    def test_session_store_persists_task_for_replay(self, tmp_path, standards_reader, state_manager) -> None:
        task_id = "pipe-wall-thickness-design-storage-replay"
        run_completed_workflow(state_manager, standards_reader, task_id)

        store = SessionStore(tmp_path / "sessions", session_id="acceptance")
        store.save_state_manager(state_manager)
        loaded = store.load_state_manager()
        task = loaded.get_task(task_id)

        assert task.outputs.get("required_thickness") is not None
        assert task.outputs.get("_execution_trace")

    def test_replay_rebuilds_report_from_stored_state(
        self,
        tmp_path,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "pipe-wall-thickness-design-storage-report"
        run_completed_workflow(state_manager, standards_reader, task_id)
        store = SessionStore(tmp_path / "sessions", session_id="acceptance")
        store.save_state_manager(state_manager)

        loaded = store.load_state_manager()
        task = loaded.get_task(task_id)
        report = rebuild_report_from_task(task, standards_reader)

        generator = ReportGenerator(standards_reader.standards_root)
        storage = generator.generate(report, tmp_path / "reports", formats=("markdown", "html"))
        assert storage.markdown_path
        assert "Executive Summary" in open(storage.markdown_path, encoding="utf-8").read()

    def test_audit_query_can_explain_calculation_history(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "pipe-wall-thickness-design-storage-audit"
        run_completed_workflow(state_manager, standards_reader, task_id)
        task = state_manager.get_task(task_id)

        assert task.outputs.get("graph_version")
        assert task.outputs.get("_validation_trace")
        assert task.outputs.get("_execution_trace")
        assert task.fact_store.active_facts()
        assert task.outputs.get("required_thickness") is not None
