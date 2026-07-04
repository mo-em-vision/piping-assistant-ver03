"""Report generator tests."""

from __future__ import annotations

from pathlib import Path

from engine.reports.formatters import render_html, render_markdown
from engine.reports.report_data import build_report_from_task
from engine.reports.report_generator import ReportGenerator
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource
from models.task import Task, new_task, TaskStatus
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_build_pipe_wall_thickness_report_incomplete() -> None:
    task = new_task("pipe-wall-thickness-design-abc", status=TaskStatus.AWAITING_INPUT)
    report = build_report_from_task(task, _reader())

    assert report.workflow == "pipe_wall_thickness_design"
    assert report.status == "INCOMPLETE"
    assert "design_pressure" in report.missing_inputs
    assert report.formula_display is not None
    assert any(section.node == "304.1.2-a" for section in report.sections)


def test_build_report_with_inputs() -> None:
    task = new_task("pipe-wall-thickness-design-xyz", status=TaskStatus.ACTIVE)
    set_fact_from_input(task, legacy_input(input_id="design_pressure",
        value=500,
        unit="psi",
        source=InputSource.USER,
        original_value=500,
        original_unit="psi",))
    report = build_report_from_task(task, _reader())

    assert len(report.input_entries) == 1
    assert report.input_entries[0].original_value == 500


def test_render_markdown_contains_sections() -> None:
    task = new_task("pipe-wall-thickness-design-md", status=TaskStatus.AWAITING_INPUT)
    report = build_report_from_task(task, _reader())
    md = render_markdown(report)

    assert "Purpose" in md
    assert "304.1.2-a" in md or "304.1.2" in md
    assert "Technical Appendix" in md


def test_generator_writes_outputs(tmp_path) -> None:
    root = Path(__file__).resolve().parents[2]
    manager = TaskStateManager()
    manager.create_task("pipe-wall-thickness-design-gen", status=TaskStatus.AWAITING_INPUT)

    generator = ReportGenerator(root / "knowledge" / "standards")
    report = generator.build("pipe-wall-thickness-design-gen", manager)
    storage = generator.generate(report, tmp_path, formats=("markdown", "html", "json"))

    assert Path(storage.markdown_path).exists()
    assert Path(storage.html_path).exists()
    assert Path(storage.json_path).exists()
    html = Path(storage.html_path).read_text(encoding="utf-8")
    assert "Pipe Wall Thickness" in html
