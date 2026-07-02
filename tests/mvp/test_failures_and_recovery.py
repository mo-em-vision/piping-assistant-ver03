"""MVP strategy §14–§15 — failure and recovery testing."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.executor import execute_workflow
from engine.validation.validation_engine import ValidationEngine
from models.execution import ExecutionStatus
from models.input import EngineeringInput, InputSource
from models.task import TaskStatus
from models.validation import ComplianceStatus
from tests.acceptance.helpers import (
    MATERIAL_STRESS_NODE,
    PIPE_WALL_THICKNESS_ROOT,
    sample_inputs,
)
from tests.e2e.scenario_loader import load_scenario
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus


FAILURE_SCENARIOS = [
    "pipe_wall_thickness_missing_inputs",
    "pipe_wall_thickness_invalid_pressure",
    "pipe_wall_thickness_temperature_limit",
    "pipe_wall_thickness_external_pressure",
]

RECOVERY_SCENARIOS = [
    "pipe_wall_thickness_temperature_recovery",
]


class TestFailureTesting:
    """§14 Failure Testing — missing input, invalid unit, engineering limits."""

    def test_missing_temperature_requests_information(self, standards_reader, state_manager) -> None:
        task_id = "mvp-failure-missing-temp"
        state_manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        inputs = sample_inputs()
        del inputs["design_temperature"]
        for engineering_input in inputs.values():
            state_manager.store_input(task_id, engineering_input)

        result = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert result.status == ExecutionStatus.AWAITING_INPUT

    def test_invalid_unit_rejected(self, standards_reader) -> None:
        from engine.validation.unit_validator import UnitValidator

        inputs = sample_inputs()
        inputs["outside_diameter"] = EngineeringInput(
            input_id="outside_diameter",
            value=10,
            unit="feet",
            source=InputSource.USER,
        )
        result = UnitValidator().validate_node_inputs(
            "B313-304.1.2",
            reader=standards_reader,
            task_inputs=inputs,
        )
        assert any(
            finding.rule in {"unit_incompatible", "unit_converted"}
            for finding in result.errors + result.warnings
        )

    @pytest.mark.parametrize("scenario_name", FAILURE_SCENARIOS)
    def test_failure_scenarios(self, scenario_runner, scenarios_dir: Path, scenario_name: str) -> None:
        scenario = load_scenario(scenarios_dir / f"{scenario_name}.yaml")
        scenario_runner.run(scenario)


class TestRecoveryTesting:
    """§15 Recovery Testing — user corrections rebuild workflow."""

    @pytest.mark.parametrize("scenario_name", RECOVERY_SCENARIOS)
    def test_recovery_scenarios(self, scenario_runner, scenarios_dir: Path, scenario_name: str) -> None:
        scenario = load_scenario(scenarios_dir / f"{scenario_name}.yaml")
        scenario_runner.run(scenario)

    def test_corrected_temperature_rebuilds_report(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        from tests.acceptance.helpers import rebuild_report_from_task, run_completed_workflow

        task_id = "pipe-wall-thickness-design-mvp-recovery-report"
        state_manager.create_task(task_id)
        for engineering_input in sample_inputs(temperature=900).values():
            state_manager.store_input(task_id, engineering_input)
        execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)

        state_manager.store_input(task_id, sample_inputs(temperature=400)["design_temperature"])
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)

        assert report.status == "PASS"
        assert state_manager.get_task(task_id).outputs.get("required_thickness") is not None

