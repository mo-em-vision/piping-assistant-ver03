"""Graph inspection commands (standards/ only)."""

from __future__ import annotations

import typer
from rich.tree import Tree

from cli.display import console, print_error
from cli.standards_reader import StandardsReader
from config.loader import CLIConfig


def _standard_slug(config: CLIConfig) -> str:
    return config.default_standard.lower()


def register_graph_commands(app: typer.Typer, config: CLIConfig) -> None:
    graph_app = typer.Typer(help="Inspect dependency graphs from standards packs.")
    app.add_typer(graph_app, name="graph")

    @graph_app.command("show")
    def graph_show(
        node_id: str = typer.Argument(
            ...,
            help="Node or root id (e.g. B313-304.1.1 or pipe_wall_thickness_design)",
        ),
    ) -> None:
        """Show dependency tree for a node."""
        reader = StandardsReader(config.standards_root, standard=_standard_slug(config))
        try:
            tree_data = reader.dependency_tree(node_id)
        except FileNotFoundError:
            print_error(f"Node reference missing: {node_id}")
            raise typer.Exit(code=1) from None

        root_label = f"{tree_data['id']} ({tree_data.get('type', 'node')})"
        tree = Tree(root_label)
        _build_rich_tree(tree, tree_data.get("children", []))
        console.print(tree)


def _build_rich_tree(parent: Tree, children: list[dict]) -> None:
    for child in children:
        if child.get("cycle"):
            parent.add("[yellow]cycle detected[/yellow]")
            continue
        if child.get("missing"):
            parent.add(f"[red]{child['id']} (missing)[/red]")
            continue
        label = f"{child['id']} ({child.get('type', '?')})"
        branch = parent.add(label)
        _build_rich_tree(branch, child.get("children", []))
