"""Tests for activated node display blocks and workflow bootstrap."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from api.node_display import build_activated_node_blocks
from api.workflow_bootstrap import (
    bootstrap_new_task,
    refresh_task_planning,
    resolve_activated_definition_node,
    task_ready_for_execution,
)
from config.loader import CLIConfig
from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.api.conftest import api_session_id


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_resolve_definition_node_for_pipe_workflow(standards_reader: StandardsReader) -> None:
    node_id = resolve_activated_definition_node(standards_reader, "pipe_wall_thickness_design")
    assert node_id in {"304.1.1-a", "B313-304.1.1"}


def test_build_activated_node_blocks_for_304_1_1(standards_reader: StandardsReader) -> None:
    node_id = resolve_activated_definition_node(standards_reader, "pipe_wall_thickness_design")
    assert node_id is not None
    record = standards_reader.load(node_id)
    assert str(record.metadata.get("type", "")) in {"paragraph", "definition", "standard_section"}
    blocks = build_activated_node_blocks(standards_reader, node_id)
    if node_id == "B313-304.1.1":
        types = [block["type"] for block in blocks]
        assert "equation" in types


def test_bootstrap_new_task_activates_definition_node(
    tmp_path: Path,
    project_root: Path,
    standards_reader: StandardsReader,
) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-boot01", status=TaskStatus.AWAITING_INPUT)
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

    bootstrap_new_task(task, "pipe_wall_thickness_design", config)

    planning = planning_projection(task)
    assert task.active_nodes[0] in {"304.1.1-a", "B313-304.1.1"}
    assert planning["active_definition_node"] in {"304.1.1-a", "B313-304.1.1"}
    assert planning["current_phase"] == "expansion_assumptions"
    assert "straight_pipe_section" in (planning["phase_missing"].get("expansion_assumptions") or [])


def test_create_task_returns_node_activation_outputs(
    tmp_path: Path,
    project_root: Path,
) -> None:
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
    service = DesktopApiService(config=config, session_id="default")
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)

    assert state["active_nodes"][0] in {"304.1.1-a", "B313-304.1.1"}
    assert "WF-PIPE-WALL-THICKNESS" in state["active_nodes"]
    param_names = {item["name"] for item in state["parameters"]}
    assert "straight_pipe_section" in param_names
    assert state.get("active_node_context", {}).get("node_id") in {"304.1.1-a", "B313-304.1.1"}


def test_submit_input_advances_to_pressure_loading(
    tmp_path: Path,
    project_root: Path,
) -> None:
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
    service = DesktopApiService(config=config, session_id="default")
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        unit=None,
        session_id=session_id,
    )
    state = service.submit_input(
        task_id,
        parameter="pressure_loading",
        value="internal_pressure",
        unit=None,
        session_id=session_id,
    )

    pressure_param = next(item for item in state["parameters"] if item["name"] == "pressure_loading")
    assert pressure_param["status"] == "confirmed"
    assert any(
        item["name"] == "design_pressure" and item["status"] == "pending"
        for item in state["parameters"]
    )
    pressure_step = next(
        step for step in state["progress"]["timeline"] if step.get("id") == "pressure_loading"
    )
    assert pressure_step["status"] == "done"


def test_stale_empty_goal_tree_is_not_ready_for_execution(
    tmp_path: Path,
    project_root: Path,
    standards_reader: StandardsReader,
) -> None:
    """Corrupt planning (root goal only) must not mark the task ready for thickness."""
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-stale-goals", status=TaskStatus.AWAITING_INPUT)
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
    bootstrap_new_task(task, "pipe_wall_thickness_design", config)
    from engine.state.task_facts import store_user_fact

    store_user_fact(
        task,
        "straight_pipe_section",
        True,
        workflow_id="pipe_wall_thickness_design",
    )
    store_user_fact(
        task,
        "pressure_loading",
        "internal_pressure",
        workflow_id="pipe_wall_thickness_design",
    )
    refresh_task_planning(task, standards_reader, propose_defaults=False)
    roots = task.goal_store.roots()
    assert roots
    for child in list(task.goal_store.children(roots[0].id)):
        task.goal_store.goals.pop(child.id, None)
    task.goal_store.get(roots[0].id).state.child_goals = []

    assert task_ready_for_execution(task) is False
