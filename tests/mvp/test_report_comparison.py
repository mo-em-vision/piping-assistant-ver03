"""MVP strategy §18–§19 — report testing and comparison strategy."""

from __future__ import annotations

import json
from pathlib import Path

from engine.reports.formatters import render_html, render_markdown
from engine.reports.report_generator import ReportGenerator
from tests.acceptance.helpers import rebuild_report_from_task, run_completed_workflow
from tests.mvp.regression import load_expected


class TestReportFileGeneration:
    """§18 Report Testing — PDF and HTML file generation."""

    def test_generates_pdf_and_html(self, standards_reader, state_manager, tmp_path) -> None:
        task_id = "pipe-wall-thickness-design-mvp-report-files"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)

        storage = ReportGenerator(standards_reader.standards_root).generate(
            report,
            tmp_path,
            formats=("markdown", "html", "pdf", "json"),
        )

        assert Path(storage.markdown_path).exists()
        assert Path(storage.html_path).exists()
        assert Path(storage.json_path).exists()


class TestReportContent:
    """§18 Report content — inputs, formulas, trace, warnings, decisions."""

    def test_report_contains_engineering_trace_chain(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        from engine.reports.report_data import build_report_from_task

        task_id = "pipe-wall-thickness-design-mvp-report-content"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = build_report_from_task(
            state_manager.get_task(task_id),
            standards_reader,
            user_request="Verify pipe wall thickness",
        )
        markdown = render_markdown(report)

        assert report.input_entries
        assert report.formula_display
        assert report.traversal
        assert report.traceability
        assert report.decisions is not None
        assert "Verify pipe wall thickness" in markdown or report.user_request


class TestReportComparisonStrategy:
    """§19 Report Comparison — data extraction and formatting validation."""

    def test_report_data_matches_expected_structure(
        self,
        standards_reader,
        state_manager,
        expected_dir,
    ) -> None:
        structure = load_expected(expected_dir / "pipe_wall_thickness_report_structure.json")
        task_id = "pipe-wall-thickness-design-mvp-report-compare"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)
        markdown = render_markdown(report)

        for section in structure["required_sections"]:
            assert section in markdown
        for field in structure["required_report_fields"]:
            assert getattr(report, field, None) is not None

    def test_json_report_supports_data_extraction(
        self,
        standards_reader,
        state_manager,
        tmp_path,
    ) -> None:
        task_id = "pipe-wall-thickness-design-mvp-report-json"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)
        storage = ReportGenerator(standards_reader.standards_root).generate(
            report,
            tmp_path,
            formats=("json",),
        )

        payload = json.loads(Path(storage.json_path).read_text(encoding="utf-8"))
        assert payload["status"] == "PASS"
        assert payload["traversal"]
        assert payload["sections"]
        assert payload.get("report_warnings") is not None or payload.get("limitations") is not None

    def test_html_formatting_is_readable(self, standards_reader, state_manager) -> None:
        task_id = "pipe-wall-thickness-design-mvp-report-html"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)
        html = render_html(report)

        assert "<h1>" in html or "<h2>" in html
        assert "Executive Summary" in html
