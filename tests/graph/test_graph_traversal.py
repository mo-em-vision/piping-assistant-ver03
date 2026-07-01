"""Legacy graph traversal flag tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.graph_engine import GraphEngine, GraphTraversalError, legacy_graph_traversal_enabled
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    return StandardsReader(root, standard="asme_b31.3")


def test_legacy_disabled_when_graph_cache_available(reader: StandardsReader, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VER03_LEGACY_GRAPH_TRAVERSAL", raising=False)
    if not reader.graph_store.available:
        pytest.skip("graph cache not built")
    assert legacy_graph_traversal_enabled(reader) is False


def test_legacy_enabled_via_env(reader: StandardsReader, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VER03_LEGACY_GRAPH_TRAVERSAL", "1")
    assert legacy_graph_traversal_enabled(reader) is True


def test_unknown_workflow_raises_without_legacy(reader: StandardsReader, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VER03_LEGACY_GRAPH_TRAVERSAL", "0")
    if not reader.graph_store.available:
        pytest.skip("graph cache not built")
    engine = GraphEngine()
    with pytest.raises(GraphTraversalError):
        engine.build_plan(
            task_id="t",
            root_id="nonexistent_workflow_slug",
            inputs={},
            reader=reader,
        )


def test_micro_graph_workflow_builds_plan(reader: StandardsReader) -> None:
    if not reader.graph_store.available:
        pytest.skip("graph cache not built")
    engine = GraphEngine()
    plan = engine.build_plan(
        task_id="t",
        root_id="pipe_wall_thickness_design",
        inputs={},
        reader=reader,
    )
    assert plan.root
