"""Validation Layer tests."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from engine.validation.validation_engine import ValidationEngine
from models.input import EngineeringInput, InputSource
from models.validation import ComplianceStatus


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "standards", standard="asme_b31.3")


def _sample_inputs() -> dict[str, EngineeringInput]:
    return {
        "design_pressure": EngineeringInput(
            input_id="design_pressure",
            value=500,
            unit="psi",
            source=InputSource.USER,
        ),
        "outside_diameter": EngineeringInput(
            input_id="outside_diameter",
            value=10,
            unit="in",
            source=InputSource.USER,
        ),
        "material": EngineeringInput(
            input_id="material",
            value="SA-106B",
            unit="dimensionless",
            source=InputSource.USER,
        ),
        "design_temperature": EngineeringInput(
            input_id="design_temperature",
            value=200,
            unit="F",
            source=InputSource.USER,
        ),
    }


def test_validate_plan_incomplete_when_inputs_missing() -> None:
    state = TaskStateManager()
    task = state.create_task("val-incomplete")
    reader = _reader()
    plan = GraphEngine().build_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs={},
        reader=reader,
    )

    result = ValidationEngine(reader).validate_plan(plan, task)

    assert result.status == ComplianceStatus.INCOMPLETE
    assert any(finding.rule == "missing_input" for finding in result.errors)


def test_validate_plan_pass_with_warnings_for_limitations() -> None:
    state = TaskStateManager()
    task = state.create_task("val-pass")
    for inp in _sample_inputs().values():
        state.store_input(task.task_id, inp)
    task = state.get_task(task.task_id)
    reader = _reader()
    plan = GraphEngine().build_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.inputs),
        reader=reader,
    )

    result = ValidationEngine(reader).validate_plan(plan, task)

    assert result.status in {ComplianceStatus.PASS, ComplianceStatus.PASS_WITH_WARNING}


def test_temperature_out_of_table_range_fails() -> None:
    reader = _reader()
    engine = ValidationEngine(reader)
    inputs = _sample_inputs()
    inputs["design_temperature"] = EngineeringInput(
        input_id="design_temperature",
        value=900,
        unit="F",
        source=InputSource.USER,
    )

    result = engine.validate_node(
        "B313-material-stress",
        task_inputs=inputs,
        dependency_outputs={},
        prior_nodes_completed=set(),
    )

    assert result.status == ComplianceStatus.FAIL
    assert any(finding.rule == "temperature_table_bounds" for finding in result.errors)


def test_invalid_pressure_string_fails() -> None:
    reader = _reader()
    inputs = _sample_inputs()
    inputs["design_pressure"] = EngineeringInput(
        input_id="design_pressure",
        value="abc",
        unit="psi",
        source=InputSource.USER,
    )

    result = ValidationEngine(reader).validate_node(
        "B313-304.1.1",
        task_inputs=inputs,
        dependency_outputs={"allowable_stress": 193_000_000.0, "S": 193_000_000.0},
        prior_nodes_completed={"B313-material-stress"},
    )

    assert result.status == ComplianceStatus.FAIL
    assert any(
        finding.rule in {"invalid_type", "positive_value"} for finding in result.errors
    )
