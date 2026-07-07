"""Required user input discovery tests for GraphEngine."""

from __future__ import annotations

from engine.graph.graph_engine import GraphEngine
from tests.acceptance.helpers import straight_section_assumption
from tests.graph.conftest import PIPE_WALL_ROOT, gate_open_inputs
from tests.helpers.facts import facts_from_inputs


def test_required_user_inputs_empty_while_gate_closed(b313_reader, graph_engine) -> None:
    assert graph_engine.required_user_inputs(PIPE_WALL_ROOT, b313_reader, task_inputs={}) == []


def test_required_user_inputs_empty_with_partial_gate_fields(b313_reader, graph_engine) -> None:
    inputs = facts_from_inputs(
        {"straight_pipe_section": straight_section_assumption()},
        task_id="partial-gate",
    )
    assert graph_engine.required_user_inputs(PIPE_WALL_ROOT, b313_reader, task_inputs=inputs) == []


def test_required_user_inputs_lists_missing_after_gate_passes(b313_reader, graph_engine) -> None:
    missing = graph_engine.required_user_inputs(
        PIPE_WALL_ROOT,
        b313_reader,
        task_inputs=gate_open_inputs(task_id="post-gate"),
    )
    assert missing
    assert "material_grade" in missing
    assert "internal_design_gage_pressure" in missing or "design_pressure" in missing


def test_required_user_inputs_excludes_inactive_branch_fields(b313_reader, graph_engine) -> None:
    missing = graph_engine.required_user_inputs(
        PIPE_WALL_ROOT,
        b313_reader,
        task_inputs=gate_open_inputs(task_id="internal-branch"),
    )
    assert "external_design_pressure" not in missing


def test_required_user_inputs_excludes_node_output_parameters(b313_reader, graph_engine) -> None:
    missing = graph_engine.required_user_inputs(
        PIPE_WALL_ROOT,
        b313_reader,
        task_inputs=gate_open_inputs(task_id="node-output"),
    )
    assert "minimum_required_thickness" not in missing
    assert "required_wall_thickness" not in missing
