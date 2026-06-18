"""MVP strategy §8–§9 — engineering calculation and reference data regression."""

from __future__ import annotations

from tests.acceptance.helpers import (
    MATERIAL_STRESS_NODE,
    WALL_THICKNESS_NODE,
    run_completed_workflow,
    sample_inputs,
)
from tests.mvp.regression import assert_regression_outputs, compute_reference_thickness, load_expected


class TestEngineeringCalculationRegression:
    """§8 Engineering Calculation Testing — inputs, formula, intermediates, final result."""

    def test_full_workflow_matches_reference_data(
        self,
        standards_reader,
        state_manager,
        expected_dir,
    ) -> None:
        reference = load_expected(expected_dir / "pipe_wall_thickness_calculation.json")
        task_id = "pipe-wall-thickness-design-mvp-regression"
        run_completed_workflow(state_manager, standards_reader, task_id, inputs=sample_inputs())
        task = state_manager.get_task(task_id)

        assert_regression_outputs(task, reference)

    def test_calculation_trace_contains_intermediate_steps(
        self,
        standards_reader,
        state_manager,
        expected_dir,
    ) -> None:
        reference = load_expected(expected_dir / "pipe_wall_thickness_calculation.json")
        task_id = "pipe-wall-thickness-design-mvp-intermediates"
        run_completed_workflow(state_manager, standards_reader, task_id)
        trace = state_manager.get_task(task_id).outputs["_execution_trace"]

        calc_entry = next(entry for entry in trace if entry["node_id"] == WALL_THICKNESS_NODE)
        calculation = calc_entry.get("trace", {}).get("calculation", {})
        steps = calculation.get("steps", []) if isinstance(calculation, dict) else []
        assert steps

        for symbol in reference.get("intermediate_symbols", []):
            step_text = str(steps)
            assert symbol in step_text or symbol in str(calc_entry.get("trace", {}))

    def test_execution_order_matches_reference(
        self,
        standards_reader,
        state_manager,
        expected_dir,
    ) -> None:
        reference = load_expected(expected_dir / "pipe_wall_thickness_calculation.json")
        task_id = "pipe-wall-thickness-design-mvp-order"
        result = run_completed_workflow(state_manager, standards_reader, task_id)

        executed = [item.node_id for item in result.node_results if item.status.value == "completed"]
        assert executed == reference["execution_order"]

    def test_reference_thickness_formula_is_stable(self) -> None:
        thickness = compute_reference_thickness()
        assert thickness > 0
        repeat = compute_reference_thickness()
        assert thickness == repeat
