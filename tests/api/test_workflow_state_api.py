"""API tests for workflow state exposure (Phase 4-5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from api.json_encoding import json_safe
from config.loader import CLIConfig
from engine.executor.executor import execute_workflow
from engine.state import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from tests.acceptance.helpers import sample_inputs
from tests.api.conftest import api_session_id


def _service(tmp_path: Path, project_root: Path) -> DesktopApiService:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def test_task_state_includes_workflow_state(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = service.get_task(task_id, session_id)
    workflow_state = state["workflow_state"]

    json.dumps(workflow_state)
    assert workflow_state["task_id"] == task_id
    assert workflow_state["workflow_id"]
    assert "variable_values" in workflow_state
    assert "lookup_results" in workflow_state
    assert "selections" in workflow_state
    assert "parameters" in workflow_state
    assert "history" in workflow_state
    assert "timestamp" in workflow_state
    assert workflow_state["version"] in {"1", "2", "3", "4", "5", "6"}
    assert "presentation_blocks" in workflow_state
    assert "node_outputs" in workflow_state


def test_get_workflow_state_endpoint_matches_embedded_payload(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    embedded = service.get_task(task_id, session_id)["workflow_state"]
    dedicated = service.get_workflow_state(task_id, session_id)
    embedded.pop("timestamp", None)
    dedicated.pop("timestamp", None)
    assert dedicated == embedded


def test_workflow_state_parameters_resolve_quantity_dimension(
    tmp_path: Path,
    project_root: Path,
    standards_reader,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    manager = TaskStateManager()
    task_id = "workflow-state-parameters"
    manager.create_task(task_id)
    manager.store_input(
        task_id,
        EngineeringInput(
            input_id="design_pressure",
            value=1_000_000,
            unit="Pa",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    manager.store_input(
        task_id,
        EngineeringInput(
            input_id="nominal_pipe_size",
            value=4,
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    manager.store_output(task_id, "workflow", "pipe_wall_thickness_design")
    manager.store_output(task_id, "required_thickness", 0.084)
    manager.store_output(task_id, "required_thickness_unit", "mm")

    workflow_state = manager.get_workflow_state(task_id, reader=standards_reader)
    payload = json_safe(workflow_state)
    json.dumps(payload)

    pressure = payload["parameters"]["design_pressure"]
    assert pressure["dimension"] == "pressure"
    assert pressure["source"] == "user_input"
    assert pressure["concept_id"] == "B313-quantity-pressure"
    assert pressure["canonical_unit"] == "UNIT-Pa"
    assert "UNIT-psi" in pressure["allowed_units"]
    assert pressure["unit_id"] == "UNIT-Pa"

    nps = payload["parameters"]["nominal_pipe_size"]
    assert nps["dimension"] is None
    assert nps["concept_id"] == "B313-designation-nps"
    assert nps["allowed_units"] == ["UNIT-dimensionless"]

    thickness = payload["parameters"]["required_thickness"]
    assert thickness["dimension"] == "length"
    assert thickness["source"] == "derived"

    assert "node_documentation" in payload
    assert payload["version"] == "6"
    assert payload["presentation_blocks"]
    assert payload["node_outputs"]


def test_workflow_state_execution_events_after_run(
    tmp_path: Path,
    project_root: Path,
    standards_reader,
) -> None:
    manager = TaskStateManager()
    task_id = "workflow-state-api-lifecycle"
    manager.create_task(task_id)
    for engineering_input in sample_inputs().values():
        manager.store_input(task_id, engineering_input)

    execute_workflow(
        task_id,
        "pipe_wall_thickness_design",
        state=manager,
        reader=standards_reader,
    )

    workflow_state = manager.get_workflow_state(task_id, reader=standards_reader)
    payload = json_safe(workflow_state)
    assert payload["version"] == "6"
    assert payload["presentation_blocks"]
    assert "execution_events" in payload
    assert len(payload["execution_events"]) >= 3
