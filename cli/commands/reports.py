"""Report generation command."""

from __future__ import annotations

import typer

from cli.display import print_assistant, print_error
from cli.session_store import SessionStore
from config.loader import CLIConfig
from engine.reports.report_generator import ReportGenerator
from engine.state.state_manager import TaskNotFoundError


def register_report_commands(app: typer.Typer, config: CLIConfig) -> None:
    report_app = typer.Typer(help="Generate engineering reports.")
    app.add_typer(report_app, name="report")

    @report_app.command("generate")
    def report_generate(
        task_id: str,
        format: str = typer.Option(
            None,
            "--format",
            "-f",
            help="Report format: pdf, html, markdown, md, or json",
        ),
        with_ai: bool = typer.Option(
            False,
            "--with-ai",
            help="Apply AI presentation layer (does not modify engineering values).",
        ),
        draft: bool = typer.Option(
            False,
            "--draft",
            help="Save report data draft only (no final document).",
        ),
    ) -> None:
        """Generate a report for a completed or in-progress task."""
        store = SessionStore(config.sessions_dir)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError:
            print_error(f"Task not found: {task_id}")
            raise typer.Exit(code=1) from None

        generator = ReportGenerator(
            config.standards_root,
            standard=config.default_standard.lower(),
        )
        report = generator.build(task_id, manager)
        output_dir = store.session_path / "reports"

        if draft:
            path = generator.save_draft(report, output_dir)
            print_assistant(f"Draft report data saved to: {path}")
            return

        report_format = (format or config.report_format).lower()
        format_map = {
            "pdf": ("pdf", "html", "markdown", "json"),
            "html": ("html", "markdown", "json"),
            "markdown": ("markdown", "json"),
            "md": ("markdown", "json"),
            "json": ("json",),
        }
        if report_format not in format_map:
            print_error("Supported formats: pdf, html, markdown, md, json")
            raise typer.Exit(code=1)

        storage = generator.generate(
            report,
            output_dir,
            formats=format_map[report_format],
            use_ai=with_ai,
        )

        lines = [
            f"Report generated for task `{task_id}`.",
            f"Status: {report.status}",
            f"Report data: {storage.report_data_path}",
        ]
        if storage.markdown_path:
            lines.append(f"Markdown: {storage.markdown_path}")
        if storage.html_path:
            lines.append(f"HTML: {storage.html_path}")
        if storage.pdf_path:
            lines.append(f"PDF: {storage.pdf_path}")
        if storage.json_path:
            lines.append(f"JSON: {storage.json_path}")
        if with_ai:
            lines.append("AI presentation layer applied.")

        print_assistant("\n".join(lines))
