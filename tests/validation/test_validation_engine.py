"""Validation Layer tests."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from engine.validation.validation_engine import ValidationEngine
from models.input import InputSource
from models.validation import ComplianceStatus
from tests.acceptance.helpers import sample_inputs as _sample_inputs
from tests.helpers.facts import facts_from_inputs, legacy_input


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
        state.store_input(
            task.task_id,
            fact_from_engineering_input(inp, task_id=task.task_id),
        )
    task = state.get_task(task.task_id)
    reader = _reader()
    plan = GraphEngine().build_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.fact_store.active_facts()),
        reader=reader,
    )

    result = ValidationEngine(reader).validate_plan(plan, task)

    assert result.status in {ComplianceStatus.PASS, ComplianceStatus.PASS_WITH_WARNING}


def test_catalog_material_name_passes_stress_table_validation() -> None:
    reader = _reader()
    engine = ValidationEngine(reader)
    inputs = facts_from_inputs(
        _sample_inputs(material="A106 Gr B"),
        task_id="catalog-material-test",
    )

    result = engine.validate_node(
        "asme-b313-table-A-1",
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
    sample = _sample_inputs()
    sample["design_temperature"] = legacy_input("design_temperature", 900, "F")
    inputs = facts_from_inputs(sample, task_id="temperature-bounds-test")

    result = engine.validate_node(
        "asme-b313-table-A-1",
        task_inputs=inputs,
        dependency_outputs={},
        prior_nodes_completed=set(),
    )

    assert result.status == ComplianceStatus.FAIL
    assert any(finding.rule == "temperature_table_bounds" for finding in result.errors)


def test_invalid_pressure_string_fails() -> None:
    reader = _reader()
    sample = _sample_inputs()
    sample["design_pressure"] = legacy_input("design_pressure", "abc", "psi")
    inputs = facts_from_inputs(sample, task_id="invalid-pressure-test")

    result = ValidationEngine(reader).validate_node(
        "304.1.2-a",
        task_inputs=inputs,
        dependency_outputs={"allowable_stress": 193_000_000.0, "S": 193_000_000.0},
        prior_nodes_completed={"asme-b313-table-A-1"},
    )

    assert result.status == ComplianceStatus.FAIL
    assert any(
        finding.rule in {"invalid_type", "positive_value"} for finding in result.errors
    )


def test_unconfirmed_weld_efficiency_is_incomplete() -> None:
    reader = _reader()
    sample = _sample_inputs()
    sample["weld_joint_efficiency"] = legacy_input(
        "weld_joint_efficiency",
        1.0,
        source=InputSource.DEFAULT,
        requires_confirmation=True,
    )
    inputs = facts_from_inputs(sample, task_id="unconfirmed-efficiency-test")

    result = ValidationEngine(reader).validate_node(
        "304.1.2-a",
        task_inputs=inputs,
        dependency_outputs={"allowable_stress": 193_000_000.0, "S": 193_000_000.0},
        prior_nodes_completed={"asme-b313-table-A-1"},
    )

    assert result.status == ComplianceStatus.INCOMPLETE
    assert any(finding.rule == "missing_assumption" for finding in result.errors)
