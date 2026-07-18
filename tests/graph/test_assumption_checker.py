"""Assumption checker tests."""

from __future__ import annotations

from pathlib import Path

from engine.graph.assumption_checker import (
    evaluate_path_assumptions,
    evaluate_path_execution_assumptions,
)
from engine.graph.graph_engine import GraphEngine
from engine.reference.standards_reader import StandardsReader
from models.input import InputSource, InputStatus
from tests.acceptance.helpers import (
    confirmed_default_inputs,
    internal_pressure_assumption,
    straight_section_assumption,
)
from tests.helpers.facts import facts_from_inputs, legacy_input


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_wall_thickness_requires_straight_pipe_before_pressure_design_case() -> None:
    reader = _reader()
    result = GraphEngine().evaluate_assumptions(
        "pipe_wall_thickness_design",
        reader,
        existing_inputs={},
    )

    assert "straight_pipe_section" in result.missing_fields
    assert "pipe" in result.field_questions["straight_pipe_section"].lower()


def test_wall_thickness_requires_pressure_design_case_after_straight_pipe() -> None:
    reader = _reader()
    inputs = facts_from_inputs(
        {"straight_pipe_section": straight_section_assumption()},
        task_id="assumption-test",
    )
    engine = GraphEngine()
    plan = engine.build_plan(
        task_id="assumption-test",
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
        reader=reader,
    )
    missing = engine.required_user_inputs(
        "pipe_wall_thickness_design",
        reader,
        existing_inputs=set(inputs.keys()),
        task_inputs=inputs,
        plan=plan,
    )

    assert "pressure_design_case" in missing


def test_internal_pressure_satisfies_assumption() -> None:
    reader = _reader()
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_design_case": internal_pressure_assumption(),
        },
        task_id="assumption-test",
    )
    plan = GraphEngine().build_plan(
        task_id="assumption-test",
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
        reader=reader,
    )
    result = evaluate_path_assumptions(plan.execution_order, reader, existing_inputs=inputs)

    assert "pressure_design_case" not in result.missing_fields
    assert not result.blocked
    assert "304.1.1-a" in plan.nodes
    assert "304.1.2-a" in plan.nodes


def test_external_pressure_expands_external_node() -> None:
    reader = _reader()
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_design_case": legacy_input(
                "pressure_design_case",
                "external_pressure",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="assumption-test",
    )
    plan = GraphEngine().build_plan(
        task_id="assumption-test",
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
        reader=reader,
    )

    assert "304.1.1-a" in plan.nodes
    assert "304.1.3" in plan.nodes
    assert "304.1.2-a" not in plan.nodes
    result = evaluate_path_assumptions(plan.execution_order, reader, existing_inputs=inputs)
    assert not result.blocked


def test_execution_assumptions_do_not_require_lookup_derived_coefficients() -> None:
    reader = _reader()
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_design_case": internal_pressure_assumption(),
            "d_input_mode": legacy_input(
                "d_input_mode", "direct_od", source=InputSource.USER, status=InputStatus.CONFIRMED
            ),
            "design_pressure": legacy_input("design_pressure", 500, "psi"),
            "outside_diameter": legacy_input("outside_diameter", 10, "in"),
            "design_temperature": legacy_input("design_temperature", 200, "F"),
        },
        task_id="assumption-test",
    )
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
    assert "weld_joint_strength_reduction_factor_W" not in result.missing_fields
    assert "temperature_coefficient_Y" not in result.missing_fields


def test_execution_assumptions_satisfied_with_confirmed_defaults() -> None:
    reader = _reader()
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_design_case": internal_pressure_assumption(),
            **confirmed_default_inputs(),
        },
        task_id="assumption-test",
    )
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
