"""Tests for GraphExplorerAdapter induced subgraph building."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.loader import CLIConfig
from dev.graph_explorer.adapter import GraphExplorerAdapter, TaskContextReader
from dev.graph_explorer.serializer import GraphEdgeDto, GraphNodeDto


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def config(project_root: Path) -> CLIConfig:
    return CLIConfig.load(project_root=project_root)


def test_build_subgraph_induced_edges(config: CLIConfig) -> None:
    adapter = GraphExplorerAdapter(config, session_id="default")
    active = ["WF-PIPE-WALL-THICKNESS", "304.1.1-a", "B313-param-P"]
    nodes, edges = adapter._build_subgraph(active)

    node_ids = {node.id for node in nodes}
    assert "WF-PIPE-WALL-THICKNESS" in node_ids
    for edge in edges:
        assert edge.source in node_ids
        assert edge.target in node_ids


def test_read_unknown_task_returns_empty(config: CLIConfig) -> None:
    reader = TaskContextReader(config, session_id="default")
    ctx = reader.read(task_id="nonexistent-task-id")
    assert ctx.task_id is None
    assert ctx.active_nodes == []


def test_get_context_unknown_task_in_session_reports_message(config: CLIConfig) -> None:
    adapter = GraphExplorerAdapter(config, session_id="default")
    context = adapter.get_context(task_id="nonexistent-task-id", session_id="default")
    assert context.task_id is None
    assert "not found" in (context.message or "").lower()


def test_get_snapshot_has_revision(config: CLIConfig) -> None:
    adapter = GraphExplorerAdapter(config, session_id="default")
    snapshot = adapter.get_snapshot()
    assert snapshot.revision
    assert isinstance(snapshot.nodes, list)
    assert isinstance(snapshot.edges, list)


def test_task_context_reader_default_session(config: CLIConfig) -> None:
    reader = TaskContextReader(config, session_id="default")
    ctx = reader.read()
    assert ctx.session_id == "default"
