"""API contract: user-facing table rows must not expose raw planner JSON."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from tests.api.conftest import api_session_id
from tests.helpers.user_visible_contract import (
    assert_task_state_table_cells_exclude_planner_blobs,
    assert_task_state_views_table_cells_exclude_planner_blobs,
    is_planner_blob_text,
)

_INTERNAL_PRESSURE_SUBMISSIONS: dict[str, tuple[object, str | None]] = {
    "straight_pipe_section": (True, None),
    "pressure_loading": ("internal_pressure", None),
    "internal_design_gage_pressure": (8.0, "bar"),
    "nominal_pipe_size": ("6", None),
    "material_grade": ("SA-106B", None),
    "design_temperature": (38.0, "C"),
    "pipe_construction_type": ("Seamless pipe", None),
    "corrosion_allowance": (0.0, "mm"),
}


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


def _run_internal_pressure_journey(service: DesktopApiService, session_id: str) -> dict:
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    for _ in range(len(_INTERNAL_PRESSURE_SUBMISSIONS) + 4):
        if state.get("status") == "completed":
            break

        submittable = list(state.get("progress", {}).get("submittable_parameters") or [])
        if not submittable:
            break

        current_ask = state.get("current_ask") or {}
        parameter_id = current_ask.get("parameter_id")
        if parameter_id not in submittable:
            parameter_id = submittable[0]

        if parameter_id not in _INTERNAL_PRESSURE_SUBMISSIONS:
            pytest.fail(f"unexpected prompt during journey setup: {parameter_id!r}")

        value, unit = _INTERNAL_PRESSURE_SUBMISSIONS[parameter_id]
        state = service.submit_input(
            task_id,
            parameter=parameter_id,
            value=value,
            unit=unit,
            session_id=session_id,
        )

    assert state.get("status") == "completed"
    return state


def test_planner_blob_detector_catches_goal_json() -> None:
    assert is_planner_blob_text('{"GOAL-1": {"status": "blocked"}}')
    assert not is_planner_blob_text("8 bar")
    assert not is_planner_blob_text("Awaiting user input")


def test_interactive_task_state_table_cells_exclude_planner_blobs(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    assert_task_state_table_cells_exclude_planner_blobs(created)

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    state = service.submit_input(
        task_id,
        parameter="pressure_loading",
        value="internal_pressure",
        session_id=session_id,
    )
    reloaded = service.get_task(task_id, session_id)

    assert_task_state_table_cells_exclude_planner_blobs(state)
    assert_task_state_table_cells_exclude_planner_blobs(reloaded)


def test_completed_pipe_wall_display_output_table_cells_exclude_planner_blobs(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = _run_internal_pressure_journey(service, session_id)

    assert_task_state_table_cells_exclude_planner_blobs(state)

    equation_blocks = [
        block
        for block in state.get("display_outputs") or []
        if isinstance(block, dict) and block.get("type") == "equation"
    ]
    assert equation_blocks
    for block in equation_blocks:
        input_table = block.get("input_table") or {}
        rows = input_table.get("rows") or []
        assert rows, f"equation block {block.get('id')!r} must expose input_table rows"


def test_inspection_task_state_views_table_cells_exclude_planner_blobs(
    tmp_path: Path,
    project_root: Path,
) -> None:
    os.environ["DEV_INSPECTION_ENABLED"] = "1"
    try:
        service = _service(tmp_path, project_root)
        session_id = api_session_id(service)
        state = _run_internal_pressure_journey(service, session_id)
        task_id = state["task_id"]

        payload = service.get_inspection(task_id, session_id)
        views = payload.get("task_state_views")
        assert isinstance(views, dict)

        assert_task_state_views_table_cells_exclude_planner_blobs(views)

        projection = payload.get("planner_debug_projection")
        assert isinstance(projection, dict)
        for group_name, items in (projection.get("groups") or {}).items():
            if not isinstance(items, list):
                continue
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                for key in ("node_id", "display_name", "label", "status_reason"):
                    value = item.get(key)
                    if value is not None:
                        assert not is_planner_blob_text(str(value)), (
                            f"planner_debug_projection.groups.{group_name}[{index}].{key}"
                        )
    finally:
        os.environ.pop("DEV_INSPECTION_ENABLED", None)
