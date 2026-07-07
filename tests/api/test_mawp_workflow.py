"""API tests for MAWP workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from api.serializers import WORKFLOW_CATALOG, workflow_catalog
from api.workflow_timeline import is_mawp_task, revealed_mawp_input_ids
from engine.state.goal_projection import planning_projection
from engine.router import MAWP_DESIGN
from engine.state.state_manager import TaskStateManager


@pytest.fixture
def temp_service(tmp_path: Path) -> DesktopApiService:
    sessions_dir = tmp_path / "sessions"
    standards_root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    from config.loader import CLIConfig

    config = CLIConfig(
        report_format="pdf",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=sessions_dir,
        standards_root=standards_root,
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def test_workflow_catalog_includes_mawp() -> None:
    ids = {item["id"] for item in workflow_catalog()}
    assert MAWP_DESIGN in ids
    mawp = next(item for item in WORKFLOW_CATALOG if item["id"] == MAWP_DESIGN)
    assert mawp["available"] is True


def test_mawp_bootstrap_planning(temp_service: DesktopApiService) -> None:
    project = temp_service.create_project("MAWP Project")
    state = temp_service.create_task(MAWP_DESIGN, project["id"])
    assert state["workflow_id"] == MAWP_DESIGN
    manager = temp_service._store_for(project["id"]).load_state_manager()
    task = manager.get_task(state["task_id"])
    planning = planning_projection(task)
    assert planning["selected_root"] == MAWP_DESIGN
    assert planning["current_phase"] in {
        "expansion_assumptions",
        "path_decisions",
        "parameter_gathering",
        "coefficient_resolution",
    }


def test_mawp_task_detection() -> None:
    manager = TaskStateManager()
    task = manager.create_task("mawp-detect")
    task.outputs["workflow"] = MAWP_DESIGN
    assert is_mawp_task(task) is True


def test_mawp_bootstrap_seeds_pressure_loading_and_geometry_defaults(
    temp_service: DesktopApiService,
) -> None:
    project = temp_service.create_project("MAWP Defaults")
    state = temp_service.create_task(MAWP_DESIGN, project["id"])
    manager = temp_service._store_for(project["id"]).load_state_manager()
    task = manager.get_task(state["task_id"])
    assert task.fact_store.active_fact("pressure_loading") is not None
    assert task.fact_store.active_fact("geometry_input_mode") is not None


def test_revealed_mawp_inputs_include_geometry() -> None:
    manager = TaskStateManager()
    task = manager.create_task("mawp-reveal")
    task.outputs["workflow"] = MAWP_DESIGN
    planning = {
        "current_phase": "parameter_gathering",
        "phase_missing": {
            "parameter_gathering": ["nominal_pipe_size", "pipe_schedule"],
        },
    }
    revealed = revealed_mawp_input_ids(task, planning)
    assert "nominal_pipe_size" in revealed
    assert "pipe_schedule" in revealed
