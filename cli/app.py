"""Typer application entry for the engineering assistant CLI."""

from __future__ import annotations

from typing import Optional

import typer

from cli.commands.chat import run_chat
from cli.commands.graph import register_graph_commands
from cli.commands.nodes import register_node_commands
from cli.commands.reports import register_report_commands
from cli.commands.tasks import register_task_commands
from config.loader import CLIConfig

app = typer.Typer(
    name="piping-assistant",
    help="Engineering assistant CLI — interface layer only; engineering truth lives in the engine.",
    no_args_is_help=True,
)

_config: CLIConfig | None = None
_debug_ai: bool = False


def get_config() -> CLIConfig:
    global _config
    if _config is None:
        _config = CLIConfig.load()
    return _config


@app.callback()
def main(
    debug_ai: bool = typer.Option(
        False,
        "--debug-ai",
        help="Display agent decision details.",
    ),
) -> None:
    """Global CLI options."""
    global _debug_ai
    _debug_ai = debug_ai


@app.command("chat")
def chat() -> None:
    """Start or continue an engineering conversation."""
    run_chat(get_config(), debug_ai=_debug_ai)


def build_app() -> typer.Typer:
    cfg = get_config()
    register_task_commands(app, cfg)
    register_report_commands(app, cfg)
    register_graph_commands(app, cfg)
    register_node_commands(app, cfg)
    return app


build_app()
