"""Assumption checker tests."""

from __future__ import annotations

from pathlib import Path

from engine.graph.assumption_checker import (
    evaluate_path_assumptions,
    evaluate_path_execution_assumptions,
)
from engine.graph.graph_engine import GraphEngine
from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput, InputSource, InputStatus
from tests.acceptance.helpers import confirmed_default_inputs, internal_pressure_assumption


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "standards", standard="asme_b31.3")


def test_wall_thickness_requires_pressure_loading_assumption() -> None:
    reader = _reader()
    result = GraphEngine().evaluate_assumptions(
        "pipe_wall_thickness_design",
        reader,
        existing_inputs={},
    )

    assert "pressure_loading" in result.missing_fields
    assert "internal" in result.field_questions["pressure_loading"].lower()


def test_internal_pressure_satisfies_assumption() -> None:
    reader = _reader()
    inputs = {"pressure_loading": internal_pressure_assumption()}
    plan = GraphEngine().build_plan(
        task_id="assumption-test",
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
        reader=reader,
    )
    result = evaluate_path_assumptions(plan.execution_order, reader, existing_inputs=inputs)

    assert "pressure_loading" not in result.missing_fields
    assert not result.blocked
    assert "B313-304.1.1" in plan.nodes
    assert "B313-304.1.2" in plan.nodes


def test_external_pressure_expands_external_node() -> None:
    reader = _reader()
    inputs = {
        "pressure_loading": EngineeringInput(
            input_id="pressure_loading",
            value="external_pressure",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        )
    }
    plan = GraphEngine().build_plan(
        task_id="assumption-test",
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
        reader=reader,
    )

    assert "B313-304.1.3" in plan.nodes
    assert "B313-304.1.1" in plan.nodes
    assert "B313-304.1.2" not in plan.nodes
    result = evaluate_path_assumptions(plan.execution_order, reader, existing_inputs=inputs)
    assert not result.blocked


def test_execution_assumptions_require_confirmed_defaults() -> None:
    reader = _reader()
    inputs = {
        "pressure_loading": internal_pressure_assumption(),
        "d_input_mode": EngineeringInput(
            "d_input_mode", "direct_od", "dimensionless", InputSource.USER, status=InputStatus.CONFIRMED
        ),
        "design_pressure": EngineeringInput("design_pressure", 500, "psi", InputSource.USER),
        "outside_diameter": EngineeringInput("outside_diameter", 10, "in", InputSource.USER),
        "design_temperature": EngineeringInput("design_temperature", 200, "F", InputSource.USER),
    }
    plan = GraphEngine().build_plan(
        task_id="assumption-test",
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
        reader=reader,
    )
    result = evaluate_path_execution_assumptions(
        plan.execution_order,
        reader,
        existing_inputs=inputs,
    )

    assert "weld_joint_efficiency" in result.missing_fields
    assert "temperature_coefficient" in result.missing_fields


def test_execution_assumptions_satisfied_with_confirmed_defaults() -> None:
    reader = _reader()
    inputs = {
        "pressure_loading": internal_pressure_assumption(),
        **confirmed_default_inputs(),
    }
    plan = GraphEngine().build_plan(
        task_id="assumption-test",
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
        reader=reader,
    )
    result = evaluate_path_execution_assumptions(
        plan.execution_order,
        reader,
        existing_inputs=inputs,
    )

    assert "weld_joint_efficiency" not in result.missing_fields
