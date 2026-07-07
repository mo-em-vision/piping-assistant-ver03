"""Tests for workflow root discovery — specific lookup vs broad discovery."""

from __future__ import annotations

from engine.graph.root_discovery import (
    BROAD_DISCOVERY_BASE_CONFIDENCE,
    EXACT_WORKFLOW_MATCH_CONFIDENCE,
    PARTIAL_SLUG_MATCH_CONFIDENCE,
    broad_discovery_confidence,
    workflow_lookup_confidence,
)
from engine.planner.planner import Planner
from models.agent import AgentAction, IntentResult
from models.task import new_task, TaskStatus
from tests.graph.conftest import PIPE_WALL_ROOT, MAWP_ROOT


def test_workflow_lookup_confidence_exact_and_partial() -> None:
    assert (
        workflow_lookup_confidence(
            "pipe_wall_thickness_design",
            slug="pipe_wall_thickness_design",
            intent="pipe_wall_thickness_design",
        )
        == EXACT_WORKFLOW_MATCH_CONFIDENCE
    )
    assert (
        workflow_lookup_confidence(
            "pipe_wall",
            slug="pipe_wall_thickness_design",
        )
        == PARTIAL_SLUG_MATCH_CONFIDENCE
    )
    assert workflow_lookup_confidence("unknown_slug", slug="pipe_wall_thickness_design") == 0.0


def test_broad_discovery_confidence_keyword_boost() -> None:
    baseline = broad_discovery_confidence(
        keyword_text="",
        title="Pipe Wall Thickness Design",
    )
    boosted = broad_discovery_confidence(
        keyword_text="pipe wall thickness design",
        title="Pipe Wall Thickness Design",
    )
    assert baseline == BROAD_DISCOVERY_BASE_CONFIDENCE
    assert boosted > BROAD_DISCOVERY_BASE_CONFIDENCE


def test_discover_roots_known_slug_returns_only_matching(b313_reader, graph_engine) -> None:
    candidates = graph_engine.discover_roots(
        b313_reader,
        workflow=PIPE_WALL_ROOT,
    )

    assert candidates
    assert all(candidate.root_id == PIPE_WALL_ROOT for candidate in candidates)
    assert candidates[0].confidence >= 0.85


def test_discover_roots_mawp_slug_returns_only_matching(b313_reader, graph_engine) -> None:
    candidates = graph_engine.discover_roots(
        b313_reader,
        workflow=MAWP_ROOT,
    )

    assert candidates
    assert all(candidate.root_id in {"WF-MAWP", MAWP_ROOT} for candidate in candidates)
    assert candidates[0].confidence >= 0.85


def test_discover_roots_broad_includes_mawp(b313_reader, graph_engine) -> None:
    candidates = graph_engine.discover_roots(b313_reader)
    root_ids = {candidate.root_id for candidate in candidates}
    assert MAWP_ROOT in root_ids or "WF-MAWP" in root_ids


def test_discover_roots_mawp_keywords_boost(b313_reader, graph_engine) -> None:
    candidates = graph_engine.discover_roots(
        b313_reader,
        keywords=["calculate mawp maximum allowable working pressure"],
    )
    assert any(candidate.root_id in {"WF-MAWP", MAWP_ROOT} for candidate in candidates)


def test_discover_roots_unknown_slug_returns_empty(b313_reader, graph_engine) -> None:
    candidates = graph_engine.discover_roots(
        b313_reader,
        workflow="totally_unknown_workflow_slug",
    )

    assert candidates == []


def test_discover_roots_unknown_slug_ignores_keyword_broad_fallback(
    b313_reader,
    graph_engine,
) -> None:
    """Keywords must not widen an explicit unknown slug into broad discovery."""
    candidates = graph_engine.discover_roots(
        b313_reader,
        workflow="totally_unknown_workflow_slug",
        keywords=["pipe wall thickness", "verify pipe integrity"],
    )

    assert candidates == []


def test_discover_roots_broad_discovery_without_slug(b313_reader, graph_engine) -> None:
    candidates = graph_engine.discover_roots(b313_reader)

    assert len(candidates) >= 2
    root_ids = {candidate.root_id for candidate in candidates}
    assert PIPE_WALL_ROOT in root_ids
    assert all(candidate.confidence >= BROAD_DISCOVERY_BASE_CONFIDENCE for candidate in candidates)


def test_discover_roots_broad_discovery_with_keywords(b313_reader, graph_engine) -> None:
    candidates = graph_engine.discover_roots(
        b313_reader,
        keywords=["calculate pipe wall thickness design"],
    )

    assert candidates
    assert any(candidate.root_id == PIPE_WALL_ROOT for candidate in candidates)
    pipe_wall = next(c for c in candidates if c.root_id == PIPE_WALL_ROOT)
    assert pipe_wall.confidence > BROAD_DISCOVERY_BASE_CONFIDENCE


def test_discover_roots_unknown_slug_does_not_use_baseline_confidence_mask(
    b313_reader,
    graph_engine,
) -> None:
    candidates = graph_engine.discover_roots(
        b313_reader,
        workflow="totally_unknown_workflow_slug",
    )

    assert not any(candidate.confidence == BROAD_DISCOVERY_BASE_CONFIDENCE for candidate in candidates)


def test_planner_unknown_slug_does_not_select_implemented_root(
    b313_reader,
) -> None:
    from engine.state.state_manager import TaskStateManager

    state_manager = TaskStateManager()
    planner = Planner(b313_reader, state=state_manager)
    intent = IntentResult(
        intent="totally_unknown_workflow_slug",
        domain="piping",
        workflow="totally_unknown_workflow_slug",
        confidence=0.95,
    )

    plan = planner.plan(intent, new_task("unknown-slug", status=TaskStatus.ACTIVE))

    assert plan.selected_root is None
    assert plan.action == AgentAction.CLARIFY
    assert plan.candidate_roots == []
