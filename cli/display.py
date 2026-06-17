"""Rich terminal output helpers."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from cli.responses import CLIResponse
from models.task import Task

console = Console()


def print_banner(title: str = "Piping Assistant") -> None:
    console.print(Panel.fit(f"[bold]{title}[/bold]", border_style="blue"))


def print_assistant(message: str) -> None:
    console.print(Panel(Markdown(message), title="Assistant", border_style="green"))


def print_error(message: str) -> None:
    console.print(Panel(message, title="Error", border_style="red"))


def print_debug_block(title: str, payload: Any) -> None:
    if isinstance(payload, (dict, list)):
        body = json.dumps(payload, indent=2, default=str)
    else:
        body = str(payload)
    console.print(Panel(body, title=title, border_style="yellow"))


def print_cli_response(response: CLIResponse) -> None:
    parts: list[str] = []
    if response.message:
        parts.append(response.message)
    if response.question:
        parts.append(response.question)
    if response.required_by:
        parts.append(f"_Required by: {response.required_by}_")
    if not parts:
        parts.append(f"Status: {response.status}")
    print_assistant("\n\n".join(parts))


def print_task_table(tasks: list[Task]) -> None:
    table = Table(title="Tasks")
    table.add_column("Task ID")
    table.add_column("Status")
    table.add_column("Warnings", justify="right")

    for task in tasks:
        table.add_row(task.task_id, task.status.value, str(len(task.warnings)))

    console.print(table)
