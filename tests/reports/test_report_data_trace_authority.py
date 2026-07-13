"""Report must follow execution trace for engineering analysis content."""

from __future__ import annotations

from pathlib import Path

from engine.reports.report_data import build_report_from_task
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.api.test_equation_display_trace import (
    EQ_2_ID,
    EQ_3A_ID,
    _apply_simulated_completed_state,
)


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _equation_section_bodies(report) -> dict[str, str]:
    return {
        section.section_id: section.body_markdown
        for section in report.display_sections or []
        if section.section_id.startswith("equation-")
    }


def test_report_engineering_display_sections_use_execution_trace_not_task_outputs() -> None:
    """Corrupting task.outputs must not change trace-backed equation sections in the report."""
    standards_reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("report-trace-authority", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)

    baseline = build_report_from_task(task, standards_reader)
    baseline_equations = _equation_section_bodies(baseline)
    baseline_traversal = [step.node_id for step in baseline.traversal]

    assert baseline_traversal == [EQ_3A_ID, EQ_2_ID]
    assert baseline_equations
    assert "2.252" in baseline_equations[f"equation-{EQ_2_ID}"]

    sentinel = 999.888
    task.outputs["t"] = sentinel
    task.outputs["required_thickness"] = sentinel
    task.outputs["t_m"] = sentinel
    task.outputs["minimum_required_thickness"] = sentinel

    corrupted = build_report_from_task(task, standards_reader)
    corrupted_equations = _equation_section_bodies(corrupted)

    assert [step.node_id for step in corrupted.traversal] == baseline_traversal
    assert corrupted_equations == baseline_equations
    for body in corrupted_equations.values():
        assert str(sentinel) not in body


def test_report_traversal_follows_execution_trace_order() -> None:
    """Traversal steps must mirror _execution_trace order rather than a replanned graph walk."""
    standards_reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("report-trace-order", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)

    forward = build_report_from_task(task, standards_reader)
    assert [step.node_id for step in forward.traversal] == [EQ_3A_ID, EQ_2_ID]

    trace = list(task.outputs.get("_execution_trace") or [])
    task.outputs["_execution_trace"] = list(reversed(trace))

    reversed_report = build_report_from_task(task, standards_reader)
    assert [step.node_id for step in reversed_report.traversal] == [EQ_2_ID, EQ_3A_ID]
