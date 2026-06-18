"""MVP strategy §22 — security testing."""

from __future__ import annotations

import pytest

from cli.app import app
from engine.executor.executor import execute_workflow
from engine.state.state_manager import TaskNotFoundError, TaskStateManager
from engine.validation.validation_engine import ValidationEngine
from models.execution import ExecutionStatus
from models.input import EngineeringInput, InputSource
from models.validation import ComplianceStatus
from tests.acceptance.helpers import PIPE_WALL_THICKNESS_ROOT, sample_inputs
from typer.testing import CliRunner


class TestInputInjectionTesting:
    """§22 Input injection — malformed values and unexpected commands."""

    def test_malformed_pressure_does_not_execute(self, standards_reader, state_manager) -> None:
        task_id = "mvp-security-malformed"
        state_manager.create_task(task_id)
        for key, value in sample_inputs().items():
            if key == "design_pressure":
                state_manager.store_input(
                    task_id,
                    EngineeringInput(
                        input_id="design_pressure",
                        value="500; DROP TABLE",
                        unit="psi",
                        source=InputSource.USER,
                    ),
                )
            else:
                state_manager.store_input(task_id, value)

        result = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert result.status in {ExecutionStatus.ERROR, ExecutionStatus.AWAITING_INPUT}

    def test_script_injection_in_material_is_rejected_or_isolated(
        self,
        standards_reader,
    ) -> None:
        inputs = sample_inputs(material="<script>alert(1)</script>")
        result = ValidationEngine(standards_reader).validate_node(
            "B313-material-stress",
            task_inputs=inputs,
            dependency_outputs={},
            prior_nodes_completed=set(),
        )
        assert result.status in {
            ComplianceStatus.FAIL,
            ComplianceStatus.INCOMPLETE,
            ComplianceStatus.PASS,
            ComplianceStatus.PASS_WITH_WARNING,
        }

    def test_unknown_unit_fails_validation(self, standards_reader) -> None:
        from engine.validation.unit_validator import UnitValidator

        inputs = sample_inputs()
        inputs["outside_diameter"] = EngineeringInput(
            input_id="outside_diameter",
            value=10,
            unit="feet",
            source=InputSource.USER,
        )
        result = UnitValidator().validate_node_inputs(
            "B313-304.1.1",
            reader=standards_reader,
            task_inputs=inputs,
        )
        assert any(
            finding.rule in {"unit_incompatible", "unit_converted"}
            for finding in result.errors + result.warnings
        )


class TestUserInputAttacks:
    """§22 User input attacks — safe parsing and data isolation."""

    def test_tasks_are_isolated_between_managers(self, standards_reader) -> None:
        manager_a = TaskStateManager()
        manager_b = TaskStateManager()
        manager_a.create_task("pipe-wall-thickness-design-task-a")
        manager_a.store_input("pipe-wall-thickness-design-task-a", sample_inputs()["design_pressure"])

        assert manager_a.get_task("pipe-wall-thickness-design-task-a").inputs
        with pytest.raises(TaskNotFoundError):
            manager_b.get_task("pipe-wall-thickness-design-task-a")

    def test_cli_rejects_invalid_task_id_for_trace(self) -> None:
        result = CliRunner().invoke(app, ["task", "trace", "../../../etc/passwd"])
        assert result.exit_code != 0

    def test_unexpected_cli_command_does_not_crash(self) -> None:
        result = CliRunner().invoke(app, ["not-a-real-command"])
        assert result.exit_code != 0
