"""Task management commands."""

from __future__ import annotations

import typer

from cli.display import print_assistant, print_error, print_task_table
from cli.session_store import SessionStore
from config.loader import CLIConfig
from engine.state.state_manager import TaskNotFoundError
from models.fact import fact_scalar_value, fact_unit


def register_task_commands(app: typer.Typer, config: CLIConfig) -> None:
    task_app = typer.Typer(help="Manage engineering tasks.")
    app.add_typer(task_app, name="task")

    @task_app.command("list")
    def task_list() -> None:
        """List tasks in the current session."""
        store = SessionStore(config.sessions_dir)
        manager = store.load_state_manager()
        tasks = manager.list_tasks()
        if not tasks:
            print_assistant("No tasks in this session.")
            return
        print_task_table(tasks)

    @task_app.command("resume")
    def task_resume(task_id: str) -> None:
        """Resume a previously stored task."""
        store = SessionStore(config.sessions_dir)
        manager = store.load_state_manager()
        try:
            task = manager.set_active_task(task_id)
        except TaskNotFoundError:
            print_error(f"Task not found: {task_id}")
            raise typer.Exit(code=1) from None

        store.save_state_manager(manager)
        active_keys = set(task.fact_store.active_facts())
        waiting = [
            key
            for key in ("design_pressure", "outside_diameter", "allowable_stress")
            if key not in active_keys
        ]
        if waiting:
            detail = f"Waiting for: {', '.join(waiting)}"
        else:
            detail = f"Status: {task.status.value}"
        print_assistant(f"Task `{task_id}` restored.\n\nCurrent state:\n\n{detail}")

    @task_app.command("trace")
    def task_trace(task_id: str) -> None:
        """Display execution trace from stored task state."""
        store = SessionStore(config.sessions_dir)
        manager = store.load_state_manager()
        try:
            task = manager.get_task(task_id)
        except TaskNotFoundError:
            print_error(f"Task not found: {task_id}")
            raise typer.Exit(code=1) from None

        lines = [f"Task: {task_id}", f"Status: {task.status.value}", ""]
        steps = manager.list_step_progress(task_id)
        if steps:
            lines.append("Step progress:")
            for step in steps:
                lines.append(f"- {step.step_id}: {step.status}")

        active_facts = task.fact_store.active_facts()
        if active_facts:
            lines.append("")
            lines.append("Facts:")
            for key, fact in active_facts.items():
                original = fact.original_value
                original_unit = fact.original_unit
                value = fact_scalar_value(fact)
                unit = fact_unit(fact)
                if original is not None:
                    lines.append(
                        f"- {key}: {value} {unit} "
                        f"(original: {original} {original_unit or unit})"
                    )
                else:
                    lines.append(f"- {key}: {value} {unit}")

        if task.outputs:
            lines.append("")
            lines.append("Outputs:")
            for key, value in task.outputs.items():
                lines.append(f"- {key}: {value}")

        if task.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in task.warnings:
                lines.append(f"- {warning}")

        if len(lines) <= 3:
            lines.append("No execution trace recorded yet.")

        print_assistant("\n".join(lines))
