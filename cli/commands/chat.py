"""Interactive chat command."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import typer
from rich.prompt import Prompt

from cli.display import print_assistant, print_banner, print_cli_response, print_debug_block
from cli.orchestrator import ChatOrchestrator
from cli.session_store import SessionStore
from config.loader import CLIConfig
from engine.state.state_manager import TaskStateManager
from models.task import Task


def resolve_incomplete_task_choice(
    manager: TaskStateManager,
    incomplete: list[Task],
    *,
    prompt_fn: Callable[..., Any] = Prompt.ask,
    print_fn: Callable[[str], Any] = print,
) -> None:
    """Apply the user's startup choice for unfinished tasks."""
    if not incomplete:
        return

    labels = ", ".join(f"{task.task_id} ({task.status.value})" for task in incomplete)
    resume = prompt_fn(
        f"Unfinished tasks found: {labels}. Resume a task?",
        choices=["yes", "no"],
        default="yes",
    )

    if resume == "no":
        manager.clear_active_task()
        return

    if len(incomplete) == 1:
        manager.set_active_task(incomplete[0].task_id)
        return

    active = manager.get_active_task()
    print_fn("Unfinished tasks found:")
    for index, task in enumerate(incomplete, start=1):
        marker = " [active]" if active and task.task_id == active.task_id else ""
        print_fn(f"  {index}. {task.task_id} ({task.status.value}){marker}")

    choices = [str(index) for index in range(1, len(incomplete) + 1)]
    choice = prompt_fn(
        f"Select task to resume [1-{len(incomplete)}]",
        choices=choices,
        default="1" if active is None else str(
            next(
                (index for index, task in enumerate(incomplete, start=1) if active and task.task_id == active.task_id),
                1,
            )
        ),
    )
    manager.set_active_task(incomplete[int(choice) - 1].task_id)


def run_chat(config: CLIConfig, *, debug_ai: bool = False) -> None:
    store = SessionStore(config.sessions_dir)
    manager = store.load_state_manager()
    incomplete = store.incomplete_tasks(manager)

    print_banner()

    if incomplete:
        resolve_incomplete_task_choice(manager, incomplete)
        store.save_state_manager(manager)

    orchestrator = ChatOrchestrator(manager)

    print_assistant(
        "Engineering assistant ready. "
        "Describe your piping analysis request (e.g. calculate pipe wall thickness)."
    )

    while True:
        user_message = Prompt.ask("\n[bold cyan]>[/bold cyan]").strip()
        if not user_message:
            continue
        if user_message.lower() in {"exit", "quit", ":q"}:
            break

        store.append_message("user", user_message)
        response, debug = orchestrator.handle_message(user_message, debug_ai=debug_ai)
        store.append_message("assistant", response.message or response.question or response.status)
        manager = orchestrator.state_manager
        store.save_state_manager(manager)

        print_cli_response(response)
        if debug_ai and debug:
            for title, payload in debug.items():
                print_debug_block(title, payload)

    print_assistant("Session saved. Goodbye.")
