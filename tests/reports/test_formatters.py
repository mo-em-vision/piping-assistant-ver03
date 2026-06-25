"""Tests for HTML report formatting."""

from __future__ import annotations

from pathlib import Path

from engine.reports.formatters import _markdown_to_html, render_html
from engine.reports.report_data import build_report_from_task
from engine.reference.standards_reader import StandardsReader


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "standards", standard="asme_b31.3")


def test_html_includes_katex_and_report_tables() -> None:
    markdown = """## Engineering Analysis

$$
t = \\frac{PD}{2(SEW + PY)}
$$

| Symbol | Value |
| --- | --- |
| P | 8.000 bar |
"""
    html = _markdown_to_html(markdown)

    assert "equation-display" in html
    assert "report-table" in html


def test_completed_report_html_has_no_task_reference_line() -> None:
    from engine.state.state_manager import TaskStateManager
    from tests.acceptance.helpers import run_completed_workflow

    reader = _reader()
    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-design-html-format"
    run_completed_workflow(manager, reader, task_id)
    report = build_report_from_task(
        manager.get_task(task_id),
        reader,
        user_request="Verify wall thickness",
    )
    html = render_html(report)

    assert "Task reference" not in html
    assert "katex" in html.lower()
    assert "report-table" in html
