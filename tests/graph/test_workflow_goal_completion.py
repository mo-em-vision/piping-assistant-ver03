"""Workflow goal anchor, completion metadata, and post-completion expansion tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.expansion_traversal_trace import load_expansion_trace
from engine.graph.graph_engine import GraphEngine
from engine.graph.lazy_expander import expand_workflow
from engine.planner.workflow_goal_metadata import resolve_root_goal_spec
from engine.reference.graph_edge_schema import workflow_anchor_target
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from engine.state.workflow_completion import workflow_marked_finished, workflow_target_satisfied
from engine.validation.workflow_node_validator import validate_workflow_node
from models.execution import ExecutionStatus
from models.goal import SatisfactionStatus
from models.task import TaskStatus
from tests.acceptance.helpers import (
    MAWP_ROOT,
    PIPE_WALL_THICKNESS_ROOT,
    load_workflow_frontmatter,
    mawp_sample_inputs,
    refresh_completed_workflow_planning,
    run_completed_mawp_workflow,
    run_completed_workflow,
    sample_inputs,
)

_FORBIDDEN_ANCHOR_EDGE_TYPES = frozenset({"starts_from_parameter", "starts_from_paragraph"})

_WORKFLOW_AUTHORING_CASES = (
    pytest.param(
        "mawp",
        MAWP_ROOT,
        "PARAM-maximum-allowable-working-pressure",
        id="mawp",
    ),
    pytest.param(
        "pipe-wall-thickness",
        PIPE_WALL_THICKNESS_ROOT,
        "PARAM-minimum-required-thickness",
        id="pipe-wall",
    ),
)


def _micro_store_and_root(reader: StandardsReader, workflow_id: str):
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    assert micro is not None
    resolved = engine._resolve_micro_root(workflow_id, reader)
    return micro.store, resolved


def _assert_post_completion_expansion(task, reader: StandardsReader, workflow_id: str) -> None:
    spec = resolve_root_goal_spec(reader, workflow_id)
    assert workflow_target_satisfied(task, spec)
    assert workflow_marked_finished(task, spec)

    roots = task.goal_store.roots()
    assert roots
    assert roots[0].satisfaction.status == SatisfactionStatus.SATISFIED

    store, resolved = _micro_store_and_root(reader, workflow_id)
    expansion = expand_workflow(
        store,
        resolved,
        task.fact_store.active_facts(),
        lazy=False,
    )
    assert expansion.pending_fields == []

    trace = load_expansion_trace(task.outputs)
    assert trace, "expected expansion trace after planning refresh"
    assert any(step.get("operation_type") == "expansion" for step in trace)


@pytest.mark.parametrize(
    ("workflow_stem", "workflow_id", "target_parameter"),
    _WORKFLOW_AUTHORING_CASES,
)
def test_workflow_authoring_contract(
    workflow_stem: str,
    workflow_id: str,
    target_parameter: str,
) -> None:
    meta = load_workflow_frontmatter(workflow_stem)
    assert validate_workflow_node(meta) == []

    for edge in meta.get("edges") or []:
        if isinstance(edge, dict):
            assert edge.get("type") not in _FORBIDDEN_ANCHOR_EDGE_TYPES

    root_goal = (meta.get("goal_expansion") or {}).get("root_goal") or {}
    assert root_goal.get("target_parameter") == target_parameter

    completion = root_goal.get("completion") or {}
    assert completion.get("when") == "target_parameter_satisfied"
    assert completion.get("status") == "finished"

    anchor_entry = next(
        entry
        for entry in meta.get("entry_points") or []
        if isinstance(entry, dict) and entry.get("role") == "definition_anchor"
    )
    assert anchor_entry.get("parameter") == target_parameter
    assert workflow_anchor_target(meta) == target_parameter


@pytest.mark.parametrize(
    ("workflow_stem", "workflow_id", "target_parameter"),
    _WORKFLOW_AUTHORING_CASES,
)
def test_workflow_anchor_from_live_graph(
    project_root: Path,
    workflow_stem: str,
    workflow_id: str,
    target_parameter: str,
) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    reader.graph_store.load()
    meta = load_workflow_frontmatter(workflow_stem)
    node_id = str(meta["id"])
    wf = reader.graph_store.get_node(node_id)
    assert wf is not None
    assert workflow_anchor_target(wf.metadata) == target_parameter


def test_validator_rejects_starts_from_parameter_edge() -> None:
    meta = load_workflow_frontmatter("mawp")
    meta = dict(meta)
    edges = list(meta.get("edges") or [])
    edges.append({"type": "starts_from_parameter", "target": "PARAM-maximum-allowable-working-pressure"})
    meta["edges"] = edges
    issues = validate_workflow_node(meta)
    assert any("starts_from_parameter" in issue for issue in issues)


def test_completed_pipe_wall_has_no_queued_expansion_nodes(b313_reader) -> None:
    manager = TaskStateManager()
    task_id = "pipe-wall-goal-completion"
    result = run_completed_workflow(
        manager,
        b313_reader,
        task_id,
        inputs=sample_inputs(),
    )
    assert result.status == ExecutionStatus.COMPLETED

    task = manager.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED
    refresh_completed_workflow_planning(task, b313_reader)
    _assert_post_completion_expansion(task, b313_reader, PIPE_WALL_THICKNESS_ROOT)


def test_completed_mawp_has_no_queued_expansion_nodes(b313_reader) -> None:
    manager = TaskStateManager()
    task_id = "mawp-goal-completion"
    result = run_completed_mawp_workflow(
        manager,
        b313_reader,
        task_id,
        inputs=mawp_sample_inputs(),
    )
    assert result.status == ExecutionStatus.COMPLETED

    task = manager.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED
    refresh_completed_workflow_planning(task, b313_reader)
    _assert_post_completion_expansion(task, b313_reader, MAWP_ROOT)
