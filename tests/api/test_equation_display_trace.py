"""Integration tests for generic equation display traces."""

from __future__ import annotations

from engine.equation.equation_display_trace_builder import build_equation_display_trace
from engine.state.state_manager import TaskStateManager
from models.calculation import CalculationResult, CalculationStatus, QuantityResult
from models.equation_display_trace import EquationDisplayTrace
from models.task import TaskStatus

from api.equation_display_trace_serializer import find_trace_for_equation
from api.equation_evaluation_display import build_equation_trace_block
from api.output_blocks import build_display_outputs
from tests.helpers.goals import task_with_planning


EQ_3A_ID = "asme-b313-304-1-2-eq-3a"
EQ_2_ID = "asme-b313-304-1-1-eq-2"


def _wall_thickness_variables() -> dict[str, float]:
    return {
        "P": 3_447_378.0,
        "D": 0.254,
        "S": 193_000_000.0,
        "E_j": 1.0,
        "W": 1.0,
        "Y": 0.4,
        "t": 2.0,
    }


def _apply_simulated_completed_state(task, reader) -> None:
    eq_3a = reader.load(EQ_3A_ID)
    eq_2 = reader.load(EQ_2_ID)
    variables = _wall_thickness_variables()
    t_value = 2.0
    t_m_value = 2.252

    trace_3a = build_equation_display_trace(
        reader=reader,
        equation_id=EQ_3A_ID,
        equation_metadata=eq_3a.metadata,
        symbol_values=variables,
        source_node_id="304.1.2-a",
        dependency_outputs={},
        task_inputs=task.fact_store.active_facts(),
        calculation=CalculationResult(
            calculation_id=EQ_3A_ID,
            final_result=QuantityResult(symbol="t", value=t_value, unit="mm"),
            status=CalculationStatus.PASS,
        ),
        task=task,
    )
    trace_2 = build_equation_display_trace(
        reader=reader,
        equation_id=EQ_2_ID,
        equation_metadata=eq_2.metadata,
        symbol_values={"t": t_value, "c": 0.252, "t_m": t_m_value},
        source_node_id="304.1.1-a",
        dependency_outputs={"t": t_value, "required_thickness": t_value},
        task_inputs=task.fact_store.active_facts(),
        calculation=CalculationResult(
            calculation_id=EQ_2_ID,
            final_result=QuantityResult(symbol="t_m", value=t_m_value, unit="mm"),
            status=CalculationStatus.PASS,
        ),
        task=task,
    )

    task.outputs.setdefault("workflow", "pipe_wall_thickness_design")
    task.outputs["t"] = t_value
    task.outputs["required_thickness"] = t_value
    task.outputs["minimum_required_thickness"] = t_m_value
    task.outputs["t_m"] = t_m_value
    task.outputs["thin_wall"] = True
    task.outputs["_execution_trace"] = [
        {
            "node_id": EQ_3A_ID,
            "trace": {
                "calculation": {"final_result": {"value": t_value, "unit": "mm"}},
                "variables_si": variables,
                "equation_display_trace": trace_3a.to_dict(),
            },
        },
        {
            "node_id": EQ_2_ID,
            "trace": {
                "calculation": {"final_result": {"value": t_m_value, "unit": "mm"}},
                "equation_display_trace": trace_2.to_dict(),
            },
        },
    ]


def test_completed_state_emits_equation_display_trace_for_eq_3a(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-display-trace-3a", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)

    payload = task.outputs["_execution_trace"][0]["trace"]["equation_display_trace"]
    trace = EquationDisplayTrace.from_dict(payload)
    assert trace.status == "evaluated"
    assert trace.symbolic_latex
    assert trace.substituted_latex
    assert trace.result_latex
    assert trace.result is not None
    assert trace.result.symbol == "t"
    if trace.substituted_latex and trace.result_latex:
        assert trace.result_latex not in trace.substituted_latex


def test_eq_3a_trace_block_includes_substitution(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-display-trace-3a-block", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "formula_parameters",
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    _apply_simulated_completed_state(task, standards_reader)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    trace_blocks = [
        block
        for block in blocks
        if block.get("equation_node_id") == EQ_3A_ID
        and block.get("display_role") == "equation"
        and block.get("display_state") == "evaluated"
    ]
    assert trace_blocks
    payload = trace_blocks[0].get("equation_display_trace")
    assert isinstance(payload, dict)
    assert payload.get("status") == "evaluated"
    assert payload.get("substituted_latex")
    result_latex = str(payload.get("result_latex") or "")
    substituted_latex = str(payload.get("substituted_latex") or "")
    if result_latex and substituted_latex:
        assert result_latex not in substituted_latex


def test_eq_2_trace_uses_calculated_t_not_awaiting_input(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-display-trace-eq2", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)

    trace = find_trace_for_equation(task, EQ_2_ID)
    assert trace is not None
    t_input = next(item for item in trace.inputs if item.symbol == "t")
    assert t_input.value is not None
    assert t_input.display_value
    assert "Awaiting user input" not in (t_input.display_value or "")


def test_lookup_coefficients_resolved_in_eq_3a_trace(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-display-trace-lookup", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)

    payload = task.outputs["_execution_trace"][0]["trace"]["equation_display_trace"]
    trace = EquationDisplayTrace.from_dict(payload)
    by_symbol = {item.symbol: item for item in trace.inputs}
    for symbol in ("S", "E_j", "W", "Y"):
        assert symbol in by_symbol
        assert by_symbol[symbol].value is not None
        assert by_symbol[symbol].display_value


def test_blocked_trace_before_evaluation_has_no_substitution(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-display-trace-blocked", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "formula_parameters",
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")

    block = build_equation_trace_block(task, standards_reader, "304.1.2-a")
    assert block is not None
    payload = block.get("equation_display_trace")
    assert isinstance(payload, dict)
    assert payload.get("status") == "blocked"
    assert payload.get("substituted_latex") in {None, ""}


def test_post_eval_pipe_wall_keeps_minimum_thickness_equation(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-display-trace-legacy", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "formula_parameters",
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    _apply_simulated_completed_state(task, standards_reader)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = {block.get("id") for block in blocks}
    assert "equation-asme-b313-304-1-1-eq-2" in ids
    assert "path-calculation-substituted-equation" not in ids
