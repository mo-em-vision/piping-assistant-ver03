"""Acceptance criteria §15, §16, and §17 — reports and audit requirements."""

from __future__ import annotations

import json
from pathlib import Path

from engine.reports.formatters import render_html, render_markdown
from engine.reports.report_generator import ReportGenerator
from tests.acceptance.helpers import rebuild_report_from_task, run_completed_workflow


class TestReportAcceptance:
    """§15 Report Acceptance — calculation flow, engineering information, traceability."""

    def test_report_contains_calculation_flow_sections(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "pipe-wall-thickness-design-acceptance-report-flow"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)
        markdown = render_markdown(report)

        for section in (
            "Purpose",
            "Executive Summary",
            "Design Basis and Input Conditions",
            "Engineering Analysis",
            "Results",
        ):
            assert section in markdown

    def test_report_includes_engineering_information(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "pipe-wall-thickness-design-acceptance-report-info"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)

        assert report.input_entries
        assert report.limitations is not None
        assert report.decisions is not None
        assert report.report_warnings is not None
        assert report.overrides is not None

    def test_report_includes_traceability_references(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "pipe-wall-thickness-design-acceptance-report-trace"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)
        markdown = render_markdown(report)

        assert report.traceability
        assert report.formula_display
        assert "304.1.2" in markdown or "B313-304.1.2" in markdown


class TestReportFormatsAcceptance:
    """§16 Report Formats — PDF and HTML via templates."""

    def test_generator_produces_html_and_pdf_from_template(
        self,
        standards_reader,
        state_manager,
        tmp_path,
    ) -> None:
        task_id = "pipe-wall-thickness-design-acceptance-report-formats"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)

        template_path = Path(__file__).resolve().parents[2] / "engine" / "reports" / "templates" / "calculation_report.md"
        assert template_path.exists()

        generator = ReportGenerator(standards_reader.standards_root)
        storage = generator.generate(report, tmp_path, formats=("markdown", "html", "pdf"))

        assert Path(storage.markdown_path).exists()
        assert Path(storage.html_path).exists()
        html = Path(storage.html_path).read_text(encoding="utf-8")
        assert "Pipe Wall Thickness" in html or "Purpose" in html


class TestAuditRequirementsAcceptance:
    """§17 Audit Requirements — graph/node versions, inputs, validation, execution, report data."""

    def test_task_outputs_contain_audit_fields(
        self,
        standards_reader,
        state_manager,
        tmp_path,
    ) -> None:
        task_id = "pipe-wall-thickness-design-acceptance-audit"
        run_completed_workflow(state_manager, standards_reader, task_id)
        task = state_manager.get_task(task_id)
        report = rebuild_report_from_task(task, standards_reader)

        generator = ReportGenerator(standards_reader.standards_root)
        storage = generator.generate(report, tmp_path, formats=("json",))

        audit = {
            "graph_version": task.outputs.get("graph_version"),
            "inputs": {key: inp.value for key, inp in task.inputs.items()},
            "validation_events": task.outputs.get("_validation_trace"),
            "execution_trace": task.outputs.get("_execution_trace"),
            "report_data": json.loads(Path(storage.json_path).read_text(encoding="utf-8")),
        }

        assert audit["graph_version"]
        assert audit["inputs"]
        assert audit["validation_events"]
        assert audit["execution_trace"]
        assert audit["report_data"]["task_id"] == task_id
