"""Node inspection and validation commands."""

from __future__ import annotations

import typer
from rich.table import Table

from cli.display import console, print_assistant, print_error
from cli.standards_reader import StandardsReader
from config.loader import CLIConfig


def _standard_slug(config: CLIConfig) -> str:
    return config.default_standard.lower()


def register_node_commands(app: typer.Typer, config: CLIConfig) -> None:
    node_app = typer.Typer(help="Inspect and validate standards nodes.")
    app.add_typer(node_app, name="node")

    @node_app.command("inspect")
    def node_inspect(node_id: str) -> None:
        """Display node metadata from the standards pack."""
        reader = StandardsReader(config.standards_root, standard=_standard_slug(config))
        try:
            record = reader.load(node_id)
        except FileNotFoundError:
            print_error(f"Node not found: {node_id}")
            raise typer.Exit(code=1) from None

        table = Table(title=f"Node: {record.node_id}")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Type", str(record.node_type or ""))
        table.add_row("Title", str(record.metadata.get("title", "")))
        table.add_row("Paragraph", str(record.metadata.get("paragraph", "")))
        table.add_row("Path", str(record.path))
        console.print(table)

        inputs = record.metadata.get("inputs", []) or []
        if inputs:
            input_table = Table(title="Inputs")
            input_table.add_column("ID")
            input_table.add_column("Symbol")
            input_table.add_column("Unit")
            input_table.add_column("Source")
            for item in inputs:
                if isinstance(item, dict):
                    input_table.add_row(
                        str(item.get("id", "")),
                        str(item.get("name", "")),
                        str(item.get("unit", "")),
                        str(item.get("source", "")),
                    )
            console.print(input_table)

        outputs = record.metadata.get("outputs", []) or []
        if outputs:
            output_table = Table(title="Outputs")
            output_table.add_column("ID")
            output_table.add_column("Symbol")
            output_table.add_column("Unit")
            for item in outputs:
                if isinstance(item, dict):
                    output_table.add_row(
                        str(item.get("id", "")),
                        str(item.get("name", "")),
                        str(item.get("unit", "")),
                    )
            console.print(output_table)

        deps = record.depends_on
        if deps:
            console.print(f"Dependencies: {', '.join(deps)}")

        equations = record.metadata.get("equations", []) or record.metadata.get("formulas", []) or []
        if equations:
            console.print(
                "Equations: "
                + ", ".join(
                    str(e.get("file", e.get("id", "")))
                    for e in equations
                    if isinstance(e, dict)
                )
            )

    @node_app.command("validate")
    def node_validate(node_id: str) -> None:
        """Validate node schema and references."""
        reader = StandardsReader(config.standards_root, standard=_standard_slug(config))
        result = reader.validate(node_id)

        status = "PASS" if result.passed else "FAIL"
        warnings = [issue for issue in result.issues if issue.level == "warning"]
        errors = [issue for issue in result.issues if issue.level == "error"]

        lines = [f"Validation: {status}"]
        if errors:
            lines.append("Errors:")
            lines.extend(f"- {issue.message}" for issue in errors)
        if warnings:
            lines.append("Warnings:")
            lines.extend(f"- {issue.message}" for issue in warnings)
        if not errors and not warnings:
            lines.append("Warnings: None")

        print_assistant("\n".join(lines))
        if not result.passed:
            raise typer.Exit(code=1)
