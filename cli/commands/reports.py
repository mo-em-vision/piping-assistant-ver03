"""Report generation command (MVP stub)."""

from __future__ import annotations

from pathlib import Path

import typer

from cli.display import print_assistant, print_error
from cli.session_store import SessionStore
from config.loader import CLIConfig
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
            help="Report format: pdf or html",
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

        report_format = (format or config.report_format).lower()
        if report_format not in {"pdf", "html"}:
            print_error("Supported formats: pdf, html")
            raise typer.Exit(code=1)

        output_dir = store.session_path / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        placeholder = output_dir / f"{task_id}.{report_format}"
        placeholder.write_text(
            (
                f"Report placeholder for task {task_id}\n"
                f"Format: {report_format}\n\n"
                "Report Generator is not yet implemented. "
                "Execution trace → Report Data → AI Presentation → output will be wired in a later step."
            ),
            encoding="utf-8",
        )

        print_assistant(
            f"Report generation is not fully implemented yet.\n\n"
            f"Placeholder written to: {placeholder}\n\n"
            "The CLI invoked the report command without bypassing future Report Generator wiring."
        )
