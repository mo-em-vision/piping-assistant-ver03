"""Typer CLI smoke tests."""

from __future__ import annotations

from typer.testing import CliRunner

from cli.app import app


def test_task_list_empty() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["task", "list"])
    assert result.exit_code == 0


def test_node_inspect_wall_thickness() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["node", "inspect", "B313-304.1.2"])
    assert result.exit_code == 0
    assert "B313-304.1.2" in result.stdout


def test_node_validate_wall_thickness() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["node", "validate", "B313-304.1.2"])
    assert result.exit_code == 0
    assert "PASS" in result.stdout


def test_node_validate_nomenclature_node() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["node", "validate", "B313-304.1.1"])
    assert result.exit_code == 0
    assert "PASS" in result.stdout


def test_graph_show_root() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["graph", "show", "pipe_wall_thickness_design"])
    assert result.exit_code == 0
    assert "B313-304.1.1" in result.stdout
    assert "B313-304.1.2" in result.stdout
