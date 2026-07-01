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
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.api.conftest import api_session_id


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_resolve_definition_node_for_pipe_workflow(standards_reader: StandardsReader) -> None:
    node_id = resolve_activated_definition_node(standards_reader, "pipe_wall_thickness_design")
    assert node_id == "B313-304.1.1"


def test_build_activated_node_blocks_for_304_1_1(standards_reader: StandardsReader) -> None:
    blocks = build_activated_node_blocks(standards_reader, "B313-304.1.1")
    types = [block["type"] for block in blocks]
    ids = [block["id"] for block in blocks]

    assert "equation" in types
    assert "table" not in types
    assert not any(block.get("title") == "Section" for block in blocks)
    assert not any(block.get("title") == "Equation parameters" for block in blocks)
    assert not any(block_id.startswith("node-activation-reference-") for block_id in ids)
    assert any(
        block.get("display") == "t_m = t + c" or block.get("content")
        for block in blocks
        if block["type"] == "equation"
    )


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

    planning = task.outputs["planning_summary"]
    assert task.active_nodes == ["B313-304.1.1"]
    assert planning["active_definition_node"] == "B313-304.1.1"
    assert planning["current_phase"] == "path_decisions"
    assert planning["phase_missing"]["path_decisions"] == ["pressure_loading"]


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

    assert state["active_nodes"] == ["B313-304.1.1"]
    param_names = {item["name"] for item in state["parameters"]}
    assert "pressure_loading" in param_names
    block_ids = [block["id"] for block in state["display_outputs"]]
    assert any(block_id.startswith("node-activation-") for block_id in block_ids)


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
        parameter="pressure_loading",
        value="internal_pressure",
        unit=None,
        session_id=session_id,
    )

    pressure_param = next(item for item in state["parameters"] if item["name"] == "pressure_loading")
    assert pressure_param["status"] == "confirmed"
    assert any(
        item["name"] == "material" and item["status"] == "pending"
        for item in state["parameters"]
    )
    pressure_step = next(
        step for step in state["progress"]["timeline"] if step.get("id") == "pressure_loading"
    )
    assert pressure_step["status"] == "done"
