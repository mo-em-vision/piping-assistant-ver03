"""Tests for graph-derived planning refresh gating."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

from api.desktop_service import DesktopApiService
from api.parameter_definitions import submit_task_input
from api.workflow_bootstrap import refresh_task_planning
from config.loader import CLIConfig
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import deactivate_fact
from models.task import TaskStatus
from tests.acceptance.helpers import run_completed_workflow, sample_inputs


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _pipe_wall_service() -> tuple[DesktopApiService, str]:
    os.environ["DEV_INSPECTION_ENABLED"] = "1"
    project_root = Path(__file__).resolve().parents[2]
    tmpdir = tempfile.mkdtemp()
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=Path(tmpdir),
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    service = DesktopApiService(config=config, session_id="default")
    project = service.create_project("Planning Gating Test")
    session_id = service.activate_project(project["id"])["session_id"]
    return service, session_id


def _ensure_pipe_wall_workflow(task) -> None:
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"


def _prepare_awaiting_corrosion(manager: TaskStateManager, reader: StandardsReader, task_id: str):
    run_completed_workflow(manager, reader, task_id)
    task = manager.get_task(task_id)
    _ensure_pipe_wall_workflow(task)
    deactivate_fact(task, "corrosion_allowance")
    task.outputs.pop("minimum_required_thickness", None)
    task.outputs.pop("t_m", None)
    task.status = TaskStatus.AWAITING_INPUT
    manager.replace_task(task_id, task)
    refresh_task_planning(
        task,
        reader,
        propose_defaults=False,
        allow_lightweight_refresh=False,
    )
    manager.replace_task(task_id, task)
    return manager.get_task(task_id)


def test_pressure_loading_triggers_goal_tree_refresh(monkeypatch) -> None:
    goal_tree_calls: list[int] = []
    import engine.planner.goal_builder as goal_builder

    original_refresh = goal_builder.refresh_goal_tree

    def tracked_refresh(*args, **kwargs):
        goal_tree_calls.append(1)
        return original_refresh(*args, **kwargs)

    monkeypatch.setattr("api.workflow_bootstrap.refresh_goal_tree", tracked_refresh)

    service, session_id = _pipe_wall_service()
    state = service.create_task("pipe_wall_thickness_design", session_id=session_id)
    service.submit_input(
        state["task_id"],
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    goal_tree_calls.clear()
    service.submit_input(
        state["task_id"],
        parameter="pressure_loading",
        value="internal_pressure",
        session_id=session_id,
    )
    assert goal_tree_calls == [1]


def test_non_structural_corrosion_allowance_skips_goal_tree_refresh(monkeypatch) -> None:
    reader = _reader()
    manager = TaskStateManager()
    task_id = "planning-gating-corrosion"
    task = _prepare_awaiting_corrosion(manager, reader, task_id)
    assert isinstance(task.outputs.get("planning_structure_signature"), dict)

    goal_tree_calls: list[int] = []
    import engine.planner.goal_builder as goal_builder

    original_refresh = goal_builder.refresh_goal_tree

    def tracked_refresh(*args, **kwargs):
        goal_tree_calls.append(1)
        return original_refresh(*args, **kwargs)

    monkeypatch.setattr("api.workflow_bootstrap.refresh_goal_tree", tracked_refresh)

    task = submit_task_input(
        manager,
        task_id,
        parameter="corrosion_allowance",
        value=3.0,
        unit="mm",
        standards_root=reader.standards_root,
    )
    refresh_task_planning(
        task,
        reader,
        propose_defaults=True,
        allow_lightweight_refresh=True,
    )

    # Corrosion submit completes definition-equation phase → structural phase change → goal tree rebuild.
    assert goal_tree_calls == [1]
    assert task.fact_store.active_fact("corrosion_allowance") is not None


def test_uncertain_signature_falls_back_to_full_refresh(monkeypatch) -> None:
    reader = _reader()
    manager = TaskStateManager()
    task_id = "planning-gating-fallback"
    run_completed_workflow(manager, reader, task_id)
    task = manager.get_task(task_id)
    _ensure_pipe_wall_workflow(task)
    manager.replace_task(task_id, task)

    goal_tree_calls: list[int] = []
    import engine.planner.goal_builder as goal_builder

    original_refresh = goal_builder.refresh_goal_tree

    def tracked_refresh(*args, **kwargs):
        goal_tree_calls.append(1)
        return original_refresh(*args, **kwargs)

    monkeypatch.setattr("api.workflow_bootstrap.refresh_goal_tree", tracked_refresh)
    monkeypatch.setattr(
        "api.workflow_bootstrap.build_planning_structure_snapshot",
        lambda **_kwargs: None,
    )

    refresh_task_planning(
        task,
        reader,
        propose_defaults=False,
        allow_lightweight_refresh=True,
    )
    assert goal_tree_calls == [1]


def test_desktop_submit_input_completes_after_corrosion_allowance() -> None:
    """Desktop submit after thickness run finalizes corrosion and completes the task."""
    service, session_id = _pipe_wall_service()
    reader = _reader()
    state = service.create_task("pipe_wall_thickness_design", session_id=session_id)
    task_id = state["task_id"]
    manager = service._store_for(session_id).load_state_manager()
    run_completed_workflow(manager, reader, task_id, inputs=sample_inputs())
    task = manager.get_task(task_id)
    _ensure_pipe_wall_workflow(task)
    deactivate_fact(task, "corrosion_allowance")
    task.outputs.pop("minimum_required_thickness", None)
    task.outputs.pop("t_m", None)
    task.status = TaskStatus.AWAITING_INPUT
    manager.replace_task(task_id, task)
    refresh_task_planning(
        task,
        reader,
        propose_defaults=False,
        allow_lightweight_refresh=False,
    )
    manager.replace_task(task_id, task)
    service._save_manager(manager, session_id)

    state = service.submit_input(
        task_id,
        parameter="corrosion_allowance",
        value=3.0,
        unit="mm",
        session_id=session_id,
    )

    assert state["status"] == "completed"
    assert state["outputs"].get("minimum_required_thickness") is not None
    assert state["outputs"].get("t_m") is not None


def test_pipe_wall_advances_after_corrosion_allowance_submit() -> None:
    reader = _reader()
    manager = TaskStateManager()
    task_id = "planning-gating-advance"
    task = _prepare_awaiting_corrosion(manager, reader, task_id)

    task = submit_task_input(
        manager,
        task_id,
        parameter="corrosion_allowance",
        value=3.0,
        unit="mm",
        standards_root=reader.standards_root,
    )
    refresh_task_planning(
        task,
        reader,
        propose_defaults=True,
        allow_lightweight_refresh=True,
    )

    assert task.fact_store.active_fact("corrosion_allowance") is not None
    from engine.state.goal_projection import missing_input_keys

    assert "corrosion_allowance" not in missing_input_keys(task)
