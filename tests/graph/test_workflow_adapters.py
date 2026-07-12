"""Tests for workflow adapter isolation in generic graph engine code."""

from __future__ import annotations

import ast
from pathlib import Path

from engine.graph import lazy_expander, path_decision, traversal
from engine.graph.graph_engine import resolve_workflow_node_id
from engine.graph.workflow_adapters import (
    DEFINITION_PHASE_INPUTS,
    LEGACY_ROOT_ALIASES,
    PATH_DECISION_FIELDS,
)


def test_legacy_aliases_resolved_via_adapter() -> None:
    assert resolve_workflow_node_id("pipe_wall_thickness_design") == (
        LEGACY_ROOT_ALIASES["pipe_wall_thickness_design"]
    )


def test_path_decision_fields_live_in_adapter() -> None:
    assert PATH_DECISION_FIELDS == path_decision._PATH_DECISION_FIELDS


def test_definition_phase_inputs_live_in_adapter() -> None:
    from engine.graph import micro_graph_engine

    assert DEFINITION_PHASE_INPUTS == micro_graph_engine._DEFINITION_PHASE_INPUTS


def test_generic_graph_modules_avoid_pipe_wall_node_literals() -> None:
    """Generic expansion modules must not embed workflow-specific node ids."""
    forbidden = (
        "304.1.2-a",
        "304.1.3",
        "B313-WF-PIPE-WALL-THICKNESS",
    )
    modules = (lazy_expander, path_decision, traversal)
    for module in modules:
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for token in forbidden:
                    assert token not in node.value, f"{module.__name__} contains {token!r}"
