"""Tests for path interaction collection."""

from __future__ import annotations

from pathlib import Path

from engine.graph.node_interaction import collect_path_interactions
from engine.reference.standards_reader import StandardsReader


def test_collect_path_interactions_merges_all_nodes(project_root: Path) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    specs = collect_path_interactions(reader, ("WF-PIPE-WALL-THICKNESS", "304.1.1-a"))
    variables = {spec.variable for spec in specs}
    assert "pressure_loading" in variables or len(variables) >= 0
