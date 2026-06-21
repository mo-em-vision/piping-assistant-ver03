"""Load default node interaction specs for chat extraction."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from engine.graph.node_interaction import NodeInteractionSpec, load_node_interactions
from engine.reference.standards_reader import StandardsReader

_NOMENCLATURE_NODE = "B313-304.1.1"


@lru_cache(maxsize=1)
def default_pipe_wall_thickness_decision_interactions() -> tuple[NodeInteractionSpec, ...]:
    """Decision interactions for the pipe wall thickness workflow (cached)."""
    project_root = Path(__file__).resolve().parents[1]
    reader = StandardsReader(project_root / "standards", standard="asme_b31.3")
    record = reader.load(_NOMENCLATURE_NODE)
    specs = load_node_interactions(record, reader)
    return tuple(spec for spec in specs if spec.mode.value == "decision")
