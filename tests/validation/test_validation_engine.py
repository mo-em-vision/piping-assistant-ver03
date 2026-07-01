"""Validation Layer tests."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from engine.validation.validation_engine import ValidationEngine
from models.input import EngineeringInput, InputSource
from models.validation import ComplianceStatus
from tests.acceptance.helpers import sample_inputs as _sample_inputs


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


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


def test_catalog_material_name_passes_stress_table_validation() -> None:
    reader = _reader()
    engine = ValidationEngine(reader)
    inputs = _sample_inputs(material="A106 Gr B")

    result = engine.validate_node(
        "B313-table-A-1",
        task_inputs=inputs,
        dependency_outputs={},
        prior_nodes_completed=set(),
    )

    assert not any(
        finding.rule == "material_not_in_table" for finding in result.errors
    )


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
        "B313-table-A-1",
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
        "B313-304.1.2",
        task_inputs=inputs,
        dependency_outputs={"allowable_stress": 193_000_000.0, "S": 193_000_000.0},
        prior_nodes_completed={"B313-table-A-1"},
    )

    assert result.status == ComplianceStatus.FAIL
    assert any(
        finding.rule in {"invalid_type", "positive_value"} for finding in result.errors
    )


def test_unconfirmed_weld_efficiency_is_incomplete() -> None:
    reader = _reader()
    inputs = _sample_inputs()
    inputs["weld_joint_efficiency"] = EngineeringInput(
        input_id="weld_joint_efficiency",
        value=1.0,
        unit="dimensionless",
        source=InputSource.DEFAULT,
        requires_confirmation=True,
    )

    result = ValidationEngine(reader).validate_node(
        "B313-304.1.2",
        task_inputs=inputs,
        dependency_outputs={"allowable_stress": 193_000_000.0, "S": 193_000_000.0},
        prior_nodes_completed={"B313-table-A-1"},
    )

    assert result.status == ComplianceStatus.INCOMPLETE
    assert any(finding.rule == "missing_assumption" for finding in result.errors)
