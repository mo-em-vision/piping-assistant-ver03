"""Interactive chat command."""

from __future__ import annotations

import typer
from rich.prompt import Prompt

from cli.display import print_assistant, print_banner, print_cli_response, print_debug_block
from cli.orchestrator import ChatOrchestrator
from cli.session_store import SessionStore
from config.loader import CLIConfig


def run_chat(config: CLIConfig, *, debug_ai: bool = False) -> None:
    store = SessionStore(config.sessions_dir)
    manager = store.load_state_manager()
    incomplete = store.incomplete_tasks(manager)

    print_banner()

    if incomplete:
        labels = ", ".join(f"{task.task_id} ({task.status.value})" for task in incomplete)
        resume = Prompt.ask(
            f"Unfinished tasks found: {labels}. Resume the active task?",
            choices=["yes", "no"],
            default="yes",
        )
        if resume == "no" and manager.get_active_task() is None and incomplete:
            chosen = Prompt.ask("Enter task ID to resume", default=incomplete[0].task_id)
            manager.set_active_task(chosen)

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
