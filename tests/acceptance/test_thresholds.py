"""Acceptance criteria §24 — testing thresholds."""

from __future__ import annotations

from engine.executor.executor import execute_workflow
from models.execution import ExecutionStatus
from models.task import TaskStatus
from tests.acceptance.helpers import PIPE_WALL_THICKNESS_ROOT, run_completed_workflow, sample_inputs


class TestThresholdHappyPath:
    """§24 Happy Path."""

    def test_valid_inputs_complete_workflow(self, standards_reader, state_manager) -> None:
        result = run_completed_workflow(
            state_manager,
            standards_reader,
            "pipe-wall-thickness-design-acceptance-happy",
        )
        task = state_manager.get_task("pipe-wall-thickness-design-acceptance-happy")

        assert result.status == ExecutionStatus.COMPLETED
        assert task.outputs.get("required_thickness") is not None
        assert task.status == TaskStatus.COMPLETED


class TestThresholdFailureHandling:
    """§24 Failure Handling."""

    def test_missing_input_pauses_execution(self, standards_reader, state_manager) -> None:
        task_id = "acceptance-threshold-missing"
        state_manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        state_manager.store_input(task_id, sample_inputs()["internal_design_gage_pressure"])

        result = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert result.status == ExecutionStatus.AWAITING_INPUT
