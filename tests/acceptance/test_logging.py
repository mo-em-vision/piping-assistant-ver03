"""Acceptance criteria §22 — logging requirements."""

from __future__ import annotations

from engine.events.event_logger import EventLogger
from engine.executor.executor import Executor
from engine.graph.graph_engine import GraphEngine
from models.event import EventType
from models.input import EngineeringInput, InputSource
from tests.acceptance.helpers import PIPE_WALL_THICKNESS_ROOT, run_completed_workflow, sample_inputs


class TestLoggingAcceptance:
    """§22 Logging Requirements — validation and execution events."""

    def test_executor_logs_validation_and_calculation_events(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "acceptance-logging-events"
        state_manager.create_task(task_id)
        for engineering_input in sample_inputs().values():
            state_manager.store_input(task_id, engineering_input)

        events = EventLogger()
        plan = GraphEngine().build_plan(
            task_id=task_id,
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs=sample_inputs(),
            reader=standards_reader,
        )
        Executor(standards_reader, events=events).execute_plan(plan, state=state_manager)

        event_types = {event.event for event in events.events}
        assert EventType.DECISION_CREATED in event_types
        assert EventType.CALCULATION_STARTED in event_types
        assert EventType.CALCULATION_COMPLETED in event_types

    def test_input_change_is_visible_in_task_conflicts(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "acceptance-logging-input-change"
        run_completed_workflow(state_manager, standards_reader, task_id)
        state_manager.store_input(
            task_id,
            EngineeringInput(
                input_id="design_temperature",
                value=400,
                unit="F",
                source=InputSource.USER,
                original_value=400,
                original_unit="F",
            ),
        )
        conflict = state_manager.get_task(task_id).conflicts[-1]

        assert conflict.input_id == "design_temperature"
        assert conflict.previous_value == 200
        assert conflict.new_value == 400

    def test_warnings_are_recorded_on_task(self, standards_reader, state_manager) -> None:
        task_id = "acceptance-logging-warnings"
        run_completed_workflow(state_manager, standards_reader, task_id)
        task = state_manager.get_task(task_id)

        assert task.warnings
        assert task.outputs.get("_validation_trace")
