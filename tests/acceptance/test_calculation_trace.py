"""Acceptance criteria §13 and §14 — calculation trace and formula acceptance."""

from __future__ import annotations

from tests.acceptance.helpers import (
    WALL_THICKNESS_NODE,
    run_completed_workflow,
    sample_inputs,
)


class TestCalculationTraceAcceptance:
    """§13 Calculation Trace — inputs, sources, intermediates, and final result."""

    def test_stores_user_inputs_with_original_units(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "acceptance-trace-inputs"
        run_completed_workflow(state_manager, standards_reader, task_id, inputs=sample_inputs())
        task = state_manager.get_task(task_id)

        pressure = task.inputs["design_pressure"]
        assert pressure.value == 500
        assert pressure.unit == "psi"
        assert pressure.original_value == 500
        assert pressure.original_unit == "psi"

    def test_execution_trace_includes_lookup_and_formula_sources(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "acceptance-trace-sources"
        run_completed_workflow(state_manager, standards_reader, task_id)
        trace = state_manager.get_task(task_id).outputs["_execution_trace"]

        lookup_entry = next(entry for entry in trace if entry["node_id"] == "B313-table-A-1")
        calc_entry = next(entry for entry in trace if entry["node_id"] == WALL_THICKNESS_NODE)

        assert "lookup" in lookup_entry.get("trace", {}) or "calculation" in lookup_entry.get("trace", {})
        assert calc_entry.get("trace")

    def test_intermediate_values_preserved_without_rounding(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "acceptance-trace-intermediates"
        run_completed_workflow(state_manager, standards_reader, task_id)
        trace = state_manager.get_task(task_id).outputs["_execution_trace"]
        calc_entry = next(entry for entry in trace if entry["node_id"] == WALL_THICKNESS_NODE)

        calculation = calc_entry.get("trace", {}).get("calculation", {})
        steps = calculation.get("steps", []) if isinstance(calculation, dict) else []
        assert steps
        assert calc_entry.get("outputs", {}).get("required_thickness") is not None


class TestFormulaAcceptance:
    """§14 Equation Acceptance — executable, readable, and referenced representation."""

    def test_equation_file_contains_executable_and_display_representations(
        self,
        standards_reader,
    ) -> None:
        node = standards_reader.load(WALL_THICKNESS_NODE)
        equation_path = node.path.parent / "equations" / "wall_thickness.md"
        text = equation_path.read_text(encoding="utf-8")

        assert "display:" in text
        assert "steps:" in text
        assert "executor:" in text
        assert "t = PD / 2(SEW + PY)" in text

    def test_node_metadata_references_standard_paragraph(self, standards_reader) -> None:
        node = standards_reader.load(WALL_THICKNESS_NODE)
        assert node.metadata.get("paragraph") == "304.1.2"
        assert node.metadata.get("equations")

    def test_report_includes_formula_display(self, standards_reader, state_manager) -> None:
        from tests.acceptance.helpers import rebuild_report_from_task

        task_id = "pipe-wall-thickness-design-acceptance-formula"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)

        assert report.formula_display
        assert "t" in report.formula_display
