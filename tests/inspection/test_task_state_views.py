"""Tests for task_state_views inspection projections."""

from __future__ import annotations

import os
from pathlib import Path

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.inspection.task_state_views import build_task_state_views
from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.legacy_goal_adapter import store_engineering_plan_on_task
from engine.planner.plan_inspector import build_planner_inspector_summary
from engine.state.state_manager import TaskStateManager
from engine.state.task_state_canonical import build_canonical_task_state
from engine.reference.standards_reader import StandardsReader
from models.task import TaskStatus
from tests.api.conftest import api_session_id

_DEBUG_FACT_KEYS = frozenset(
    {
        "engineering_plan",
        "engineering_plan_view",
        "planner_inspector_summary",
        "graph_navigation",
        "_plan_edges",
        "_planner_decisions",
        "_skipped_trace",
    }
)


def _service(tmp_path: Path, project_root: Path) -> DesktopApiService:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def test_build_task_state_views_from_canonical() -> None:
    manager = TaskStateManager()
    task = manager.create_task("ts-views-1", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"

    canonical = build_canonical_task_state(task, manager)
    views = build_task_state_views(task, canonical)

    assert views["state_summary"]["task_id"] == task.task_id
    assert views["state_summary"]["workflow_id"] == "pipe_wall_thickness_design"
    assert isinstance(views["facts_view"], list)
    assert isinstance(views["decisions_view"], list)
    assert isinstance(views["outputs_view"], list)
    assert views["validation_view"]["status"] in {"ok", "warning", "failed"}
    assert isinstance(views["trace_timeline"], list)


def test_trace_timeline_merges_execution_and_lifecycle_events() -> None:
    manager = TaskStateManager()
    task = manager.create_task("ts-views-2", status=TaskStatus.ACTIVE)
    canonical = build_canonical_task_state(task, manager)
    views = build_task_state_views(
        task,
        canonical,
        execution_events=[
            {"event": "input_requested", "node": "PARAM-test", "timestamp": "2026-01-01T00:00:00+00:00"},
        ],
        lifecycle_events=[
            {"event": "onEnter", "node_id": "304.1.2-a", "message": "Entered node", "timestamp": "2026-01-01T00:00:01+00:00"},
        ],
    )

    timeline = views["trace_timeline"]
    assert len(timeline) == 2
    assert timeline[0]["label"] == "Input requested"
    assert timeline[1]["label"] == "Node discovered"


def test_inspection_payload_includes_task_state_views(tmp_path: Path, project_root: Path) -> None:
    os.environ["DEV_INSPECTION_ENABLED"] = "1"
    try:
        service = _service(tmp_path, project_root)
        session_id = api_session_id(service)
        created = service.create_task("pipe_wall_thickness_design", session_id)
        payload = service.get_inspection(created["task_id"], session_id)

        assert "task_state_views" in payload
        views = payload["task_state_views"]
        assert "state_summary" in views
        assert "facts_view" in views
        assert "trace_timeline" in views

        summary = payload.get("planner_inspector_summary") or {}
        assert "header" in summary
        assert "phase_panel" in summary
        assert "traversal_path" in summary
        assert "requirements_panel" in summary
    finally:
        os.environ.pop("DEV_INSPECTION_ENABLED", None)


def test_facts_and_outputs_views_exclude_planner_debug_objects(project_root: Path) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("ts-views-debug", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"

    plan = build_pipe_wall_engineering_plan(task)
    store_engineering_plan_on_task(task, plan)
    task.outputs["_plan_edges"] = [{"from_node": "a", "to_node": "b", "edge_type": "next"}]
    task.outputs["_planner_decisions"] = {"304.1.2-a": {"why_selected": "test", "rejected_candidates": []}}
    task.outputs["_skipped_trace"] = [{"node_id": "304.1.3", "reason": "external path"}]

    canonical = build_canonical_task_state(task, manager, reader=reader)
    planner_summary = build_planner_inspector_summary(plan)
    views = build_task_state_views(
        task,
        canonical,
        planner_inspector_summary=planner_summary,
        skipped_trace=task.outputs["_skipped_trace"],
    )

    fact_fields = {row["field"] for row in views["facts_view"]}
    output_fields = {row["field"] for row in views["outputs_view"]}
    assert fact_fields.isdisjoint(_DEBUG_FACT_KEYS)
    assert output_fields.isdisjoint(_DEBUG_FACT_KEYS)

    assert views["state_summary"]["current_phase"] == planner_summary["current_phase"]
    assert views["state_summary"]["missing_input_count"] == len(
        planner_summary["outstanding_required_inputs"]
    )

    skipped_rows = [row for row in views["trace_timeline"] if row.get("event_type") == "node_skipped"]
    assert len(skipped_rows) == 1
    assert skipped_rows[0]["node_id"] == "304.1.3"
