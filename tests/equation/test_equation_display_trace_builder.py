"""Tests for generic equation display trace builder."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest

from engine.equation.equation_display_trace_builder import build_equation_display_trace
from engine.equation.equation_renderer import render_equation_steps
from engine.executor.node_runner import NodeRunner
from models.calculation import CalculationResult, CalculationStatus, CalculationStep, QuantityResult


@pytest.fixture()
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture()
def standards_reader(project_root: Path):
    from engine.reference.standards_reader import StandardsReader

    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


class _StubReader:
    graph_store = type("Store", (), {"available": False})()

    def load(self, node_id: str):
        raise FileNotFoundError(node_id)


def test_simple_equation_builds_evaluated_trace() -> None:
    metadata = {
        "display_latex": "a = b + c",
        "requires": [
            {"symbol": "b", "parameter": "PARAM-b"},
            {"symbol": "c", "parameter": "PARAM-c"},
        ],
        "calculates": [{"symbol": "a"}],
        "paragraph_number": "1.0-a",
        "name": "Simple sum",
    }
    calculation = CalculationResult(
        calculation_id="test:a",
        steps=[
            CalculationStep(name="sum", inputs={"b": 2.0, "c": 3.0}, result={"a": 5.0}),
        ],
        final_result=QuantityResult(symbol="a", value=5.0, unit="mm"),
        status=CalculationStatus.PASS,
    )
    trace = build_equation_display_trace(
        reader=_StubReader(),
        equation_id="eq-simple",
        equation_metadata=metadata,
        symbol_values={"b": 2.0, "c": 3.0, "a": 5.0},
        calculation=calculation,
        source_node_id="section-1",
    )
    assert trace.status == "evaluated"
    assert trace.symbolic_latex == "a = b + c"
    assert trace.substituted_latex is not None
    assert "2" in trace.substituted_latex
    assert trace.result is not None
    assert trace.result.value == pytest.approx(5.0)


def test_blocked_trace_includes_partial_substitution() -> None:
    metadata = {
        "display": {"text": "a = b + c"},
        "requires": [{"symbol": "b"}, {"symbol": "c"}],
    }
    trace = build_equation_display_trace(
        reader=_StubReader(),
        equation_id="eq-blocked",
        equation_metadata=metadata,
        symbol_values={"b": 2.0},
    )
    assert trace.status == "blocked"
    assert trace.substituted_latex is not None
    assert "2" in trace.substituted_latex
    assert trace.result_latex is None
    assert trace.latex_source == "metadata_display_text"


def test_partial_substitution_preserves_output_symbol_on_lhs() -> None:
    """Output quantity must stay symbolic on the LHS during partial substitution."""
    metadata = {
        "display_latex": "t_m = t + c",
        "requires": [{"symbol": "t"}, {"symbol": "c"}],
        "calculates": [{"symbol": "t_m"}],
    }
    trace = build_equation_display_trace(
        reader=_StubReader(),
        equation_id="eq-tm-partial",
        equation_metadata=metadata,
        symbol_values={"t": 2.0, "t_m": 5.0},
        dependency_outputs={"t": 2.0, "t_m": 5.0, "minimum_required_thickness": 5.0},
    )
    assert trace.status == "blocked"
    assert trace.substituted_latex is not None
    assert trace.substituted_latex.startswith("t_m")
    lhs, _rhs = trace.substituted_latex.split("=", 1)
    assert "5" not in lhs
    assert "2" in trace.substituted_latex


def test_evaluated_substitution_preserves_output_symbol_on_lhs() -> None:
    metadata = {
        "display_latex": "t_m = t + c",
        "requires": [{"symbol": "t"}, {"symbol": "c"}],
        "calculates": [{"symbol": "t_m"}],
    }
    trace = build_equation_display_trace(
        reader=_StubReader(),
        equation_id="eq-tm-evaluated",
        equation_metadata=metadata,
        symbol_values={"t": 2.0, "c": 0.5, "t_m": 2.5},
        dependency_outputs={"t": 2.0, "c": 0.5, "t_m": 2.5},
        calculation=CalculationResult(
            calculation_id="eq-tm-evaluated",
            final_result=QuantityResult(symbol="t_m", value=2.5, unit="mm"),
            status=CalculationStatus.PASS,
        ),
    )
    assert trace.status == "evaluated"
    assert trace.substituted_latex is not None
    assert trace.substituted_latex.startswith("t_m")
    lhs, _rhs = trace.substituted_latex.split("=", 1)
    assert "2.5" not in lhs
    assert "2" in trace.substituted_latex
    assert "0.5" in trace.substituted_latex
    assert trace.result_latex is not None


def test_render_steps_enrichment() -> None:
    metadata = {
        "display_latex": "t_m = t + c",
        "requires": [{"symbol": "t"}, {"symbol": "c"}],
        "calculates": [{"symbol": "t_m"}],
    }
    steps = render_equation_steps(
        sympy_expr="t_m = t + c",
        display_latex="t_m = t + c",
        symbol_values={"t": 4.5, "c": 0.5},
    )
    trace = build_equation_display_trace(
        reader=_StubReader(),
        equation_id="eq-tm",
        equation_metadata=metadata,
        symbol_values={"t": 4.5, "c": 0.5, "t_m": 5.0},
        render_steps=steps,
        calculation=CalculationResult(
            calculation_id="eq-tm",
            final_result=QuantityResult(symbol="t_m", value=5.0, unit="mm"),
            status=CalculationStatus.PASS,
        ),
    )
    assert trace.status == "evaluated"
    assert trace.result_latex == "5"


def test_node_runner_attach_helper_produces_trace_dict(standards_reader) -> None:
    runner = NodeRunner(standards_reader)
    record = standards_reader.load("asme-b313-304-1-1-eq-2")
    result = render_equation_steps(
        sympy_expr="t_m = t + c",
        display_latex="t_m = t + c",
        symbol_values={"t": 4.5, "c": 0.5},
    )
    trace = runner._attach_equation_display_trace(
        {},
        record=record,
        symbol_values={"t": 4.5, "c": 0.5, "t_m": 5.0},
        dependency_outputs={"t": 4.5},
        task_inputs={},
        calculation=runner._calculation_from_sympy_result(record, {"t_m": 5.0}),
        render_steps=result,
    )
    payload = trace.get("equation_display_trace")
    assert isinstance(payload, dict)
    assert payload.get("status") == "evaluated"


def test_trace_serializes_round_trip() -> None:
    metadata = {"display_latex": "x = y", "requires": [{"symbol": "y"}]}
    trace = build_equation_display_trace(
        reader=_StubReader(),
        equation_id="eq-x",
        equation_metadata=metadata,
        symbol_values={"y": 1.0, "x": 1.0},
        calculation=CalculationResult(
            calculation_id="eq-x",
            final_result=QuantityResult(symbol="x", value=1.0, unit=""),
            status=CalculationStatus.PASS,
        ),
    )
    restored = type(trace).from_dict(asdict(trace))
    assert restored.equation_id == trace.equation_id
    assert restored.status == trace.status


def test_eq_3a_substitutes_concatenated_symbols_from_fact_values(standards_reader) -> None:
    """P, D, and Y must substitute even when written as implicit products (PD, PY)."""
    from engine.state.fact_migration import fact_from_engineering_input
    from models.input import EngineeringInput, InputSource, InputStatus

    record = standards_reader.load("asme-b313-304-1-2-eq-3a")
    facts = {
        "internal_design_gage_pressure": fact_from_engineering_input(
            EngineeringInput(
                input_id="internal_design_gage_pressure",
                value=3_447_378.0,
                unit="Pa",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id="trace-test",
            workflow_id="pipe_wall_thickness_design",
        ),
        "outside_diameter": fact_from_engineering_input(
            EngineeringInput(
                input_id="outside_diameter",
                value=254.0,
                unit="mm",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id="trace-test",
            workflow_id="pipe_wall_thickness_design",
        ),
    }
    trace = build_equation_display_trace(
        reader=standards_reader,
        equation_id="asme-b313-304-1-2-eq-3a",
        equation_metadata=record.metadata,
        symbol_values={
            "S": 193_000_000.0,
            "E_j": 1.0,
            "W": 1.0,
            "Y": 0.4,
        },
        task_inputs=facts,
        dependency_outputs={
            "temperature_coefficient_Y": 0.4,
            "Y": 0.4,
        },
    )
    assert trace.substituted_latex is not None
    substituted = trace.substituted_latex
    assert "PD" not in substituted
    assert "PY" not in substituted
    for symbol in ("P", "D", "Y"):
        input_row = next(item for item in trace.inputs if item.symbol == symbol)
        assert input_row.value is not None
        assert input_row.display_value in substituted
