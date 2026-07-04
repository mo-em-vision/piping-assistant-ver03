"""Acceptance criteria §9, §10, and §20 — validation, error handling, safety."""

from __future__ import annotations

from engine.executor.executor import execute_workflow
from engine.graph.graph_engine import GraphEngine
from engine.planner.planner import Planner
from engine.validation.validation_engine import ValidationEngine
from models.execution import ExecutionStatus
from models.input import EngineeringInput, InputSource
from models.task import TaskStatus
from models.validation import ComplianceStatus
from tests.acceptance.helpers import (
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus
    PIPE_WALL_THICKNESS_ROOT,
    pipe_thickness_intent,
    sample_inputs,
)


class TestValidationAcceptance:
    """§9 Validation Acceptance — input, unit, and engineering checks."""

    def test_missing_values_mark_plan_incomplete(self, standards_reader, state_manager) -> None:
        task = state_manager.create_task("acceptance-val-missing")
        plan = GraphEngine().build_plan(
            task_id=task.task_id,
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs={},
            reader=standards_reader,
        )
        result = ValidationEngine(standards_reader).validate_plan(plan, task)
        assert result.status == ComplianceStatus.INCOMPLETE
        assert any(finding.rule == "missing_input" for finding in result.errors)

    def test_invalid_format_rejected(self, standards_reader) -> None:
        inputs = sample_inputs(pressure="abc")
        result = ValidationEngine(standards_reader).validate_node(
            "304.1.2-a",
            task_inputs=inputs,
            dependency_outputs={"allowable_stress": 193_000_000.0, "S": 193_000_000.0},
            prior_nodes_completed={"asme-b313-table-A-1"},
        )
        assert result.status == ComplianceStatus.FAIL

    def test_unit_conversion_is_supported(self, standards_reader) -> None:
        inputs = sample_inputs()
        result = ValidationEngine(standards_reader).validate_node(
            "304.1.2-a",
            task_inputs=inputs,
            dependency_outputs={"allowable_stress": 193_000_000.0, "S": 193_000_000.0},
            prior_nodes_completed={"asme-b313-table-A-1"},
        )
        assert result.status in {ComplianceStatus.PASS, ComplianceStatus.PASS_WITH_WARNING}

    def test_engineering_temperature_limit_enforced(self, standards_reader) -> None:
        inputs = sample_inputs(temperature=900)
        result = ValidationEngine(standards_reader).validate_node(
            "asme-b313-table-A-1",
            task_inputs=inputs,
            dependency_outputs={},
            prior_nodes_completed=set(),
        )
        assert result.status == ComplianceStatus.FAIL
        assert any(finding.rule == "temperature_table_bounds" for finding in result.errors)


class TestErrorHandlingAcceptance:
    """§10 Error Handling — identify, explain, and request missing parameters."""

    def test_missing_input_identifies_parameter_and_reason(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task = state_manager.create_task("acceptance-error-missing", status=TaskStatus.AWAITING_INPUT)
        plan = Planner(standards_reader, state=state_manager).plan(
            pipe_thickness_intent(),
            task,
            user_message="Calculate pipe thickness",
        )

        assert (
            "straight_pipe_section" in plan.missing_assumptions
            or "straight_pipe_section" in (plan.phase_missing.get("expansion_assumptions") or [])
        )
        assert any("straight" in question.lower() for question in plan.questions)

    def test_execution_pauses_and_requests_missing_values(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "acceptance-error-pause"
        state_manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        state_manager.store_input(task_id, sample_inputs()["design_pressure"])

        result = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert result.status == ExecutionStatus.AWAITING_INPUT
        assert state_manager.get_task(task_id).status == TaskStatus.AWAITING_INPUT


class TestSafetyAndComplianceAcceptance:
    """§20 Safety and Compliance — prevent invalid execution, allow override, record warnings."""

    def test_invalid_execution_is_prevented(self, standards_reader, state_manager) -> None:
        task_id = "acceptance-safety-block"
        state_manager.create_task(task_id)
        for key, value in sample_inputs().items():
            if key != "design_pressure":
                state_manager.store_input(task_id, value)
        state_manager.store_input(
            task_id,
            EngineeringInput(
                input_id="design_pressure",
                value="abc",
                unit="psi",
                source=InputSource.USER,
            ),
        )

        result = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert result.status == ExecutionStatus.ERROR

    def test_controlled_override_allows_continuation(self, standards_reader, state_manager) -> None:
        task_id = "acceptance-safety-override"
        state_manager.create_task(task_id)
        for engineering_input in sample_inputs(temperature=900).values():
            state_manager.store_input(task_id, engineering_input)
        task = state_manager.get_task(task_id)
        task.outputs["validation_overrides"] = ["temperature_table_bounds"]

        result = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert result.status == ExecutionStatus.COMPLETED
        assert state_manager.get_task(task_id).warnings

    def test_override_records_warning_in_validation_trace(self, standards_reader, state_manager) -> None:
        task_id = "acceptance-safety-override-trace"
        state_manager.create_task(task_id)
        for engineering_input in sample_inputs(temperature=900).values():
            state_manager.store_input(task_id, engineering_input)
        state_manager.get_task(task_id).outputs["validation_overrides"] = ["temperature_table_bounds"]

        result = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        task = state_manager.get_task(task_id)
        trace = task.outputs.get("_validation_trace", [])

        assert result.status == ExecutionStatus.COMPLETED
        plan_entry = next(entry for entry in trace if entry.get("scope") == "plan")
        assert plan_entry.get("status") in {"PASS_WITH_WARNING", "PASS"}
        assert task.outputs.get("validation_overrides") == ["temperature_table_bounds"]
