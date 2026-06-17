"""Report generator — formats ReportData into engineering documents."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_reader import StandardsReader
from engine.reports.formatters import render_html, render_json, render_markdown, write_pdf
from engine.reports.presentation import apply_presentation
from engine.reports.report_data import build_report_for_task_id
from engine.state.state_manager import TaskStateManager
from models.report import ReportData, ReportStorage


class ReportGenerator:
    """Build and render reports from task state without performing calculations."""

    def __init__(self, standards_root: Path, *, standard: str = "asme_b31.3") -> None:
        self._reader = StandardsReader(standards_root, standard=standard)

    def build(
        self,
        task_id: str,
        manager: TaskStateManager,
        *,
        user_request: str = "",
    ) -> ReportData:
        return build_report_for_task_id(
            task_id,
            manager,
            self._reader,
            user_request=user_request,
        )

    def generate(
        self,
        report: ReportData,
        output_dir: Path,
        *,
        formats: tuple[str, ...] = ("markdown", "html", "json"),
        use_ai: bool = False,
    ) -> ReportStorage:
        output_dir.mkdir(parents=True, exist_ok=True)
        base = report.task_id or report.report_id

        presentation = apply_presentation(report, use_ai=use_ai)
        markdown = render_markdown(report)
        html = render_html(report, presentation=presentation)
        json_text = render_json(report)

        md_path = output_dir / f"{base}.md"
        html_path = output_dir / f"{base}.html"
        json_path = output_dir / f"{base}.json"
        pdf_path = output_dir / f"{base}.pdf"

        md_path.write_text(markdown, encoding="utf-8")
        html_path.write_text(html, encoding="utf-8")
        json_path.write_text(json_text, encoding="utf-8")

        pdf_written: str | None = None
        if "pdf" in formats:
            if write_pdf(html, pdf_path):
                pdf_written = str(pdf_path)
            else:
                pdf_path.write_text(
                    "PDF generation requires xhtml2pdf. Install with: pip install xhtml2pdf\n",
                    encoding="utf-8",
                )
                pdf_written = str(pdf_path)

        data_path = output_dir / f"{base}_report_data.json"
        data_path.write_text(json_text, encoding="utf-8")

        return ReportStorage(
            report_data_path=str(data_path),
            pdf_path=pdf_written if "pdf" in formats else None,
            html_path=str(html_path) if "html" in formats else None,
            markdown_path=str(md_path),
            json_path=str(json_path),
        )

    @staticmethod
    def save_draft(report: ReportData, output_dir: Path) -> Path:
        """Persist report data for regeneration without recalculation."""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{report.task_id}_draft.json"
        path.write_text(render_json(report), encoding="utf-8")
        return path
