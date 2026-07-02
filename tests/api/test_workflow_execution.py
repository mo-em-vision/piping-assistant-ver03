"""API tests for post-calculation definition equation completion."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.reference.pack_tables_db import resolve_pack_tables_db
from engine.state.goal_projection import planning_projection
from tests.api.conftest import api_session_id

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _standards_db_available(project_root: Path | None = None) -> bool:
    root = project_root or _REPO_ROOT
    return resolve_pack_tables_db(root / "knowledge" / "standards" / "asme" / "asme_b31.3").exists()


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


def _submit_while_requested(
    service: DesktopApiService,
    task_id: str,
    session_id: str,
    submissions: list[tuple],
) -> dict:
    state: dict = service.get_task(task_id, session_id)
    for parameter, value, unit in submissions:
        state = service.get_task(task_id, session_id)
        pending = {
            item["name"]
            for item in state.get("parameters", [])
            if item.get("status") in {"pending", "confirmation_required"}
        }
        if parameter not in pending:
            continue
        state = service.submit_input(
            task_id,
            parameter=parameter,
            value=value,
            unit=unit,
            session_id=session_id,
        )
    return state


@pytest.mark.skipif(
    not _standards_db_available(),
    reason="standards_tables.db must be built for end-to-end thickness execution",
)
def test_submit_input_runs_wall_thickness_calculation(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = _submit_while_requested(
        service,
        task_id,
        session_id,
        [
            ("pressure_loading", "internal_pressure", None),
            ("material", "SA-106B", None),
            ("design_pressure", 8.0, "bar"),
            ("design_temperature", 38.0, "C"),
            ("nominal_pipe_size", "6", None),
            ("joint_category", "seamless", None),
            ("weld_joint_efficiency", 1.0, None),
            ("weld_joint_strength_reduction_factor_W", 1.0, None),
            ("temperature_coefficient_Y", 0.4, None),
        ],
    )

    task = service._load_manager().get_task(task_id)
    planning = planning_projection(task)
    assert state["status"] == "awaiting_input"
    assert planning["current_phase"] == "definition_equation_completion"
    assert "corrosion_allowance" in state["progress"]["submittable_parameters"]
    assert "corrosion_allowance" in {item["name"] for item in state["parameters"]}
    assert state["outputs"].get("required_thickness") is not None
    assert state["outputs"].get("minimum_required_thickness") is None

    state = service.submit_input(
        task_id,
        parameter="corrosion_allowance",
        value=0.0,
        unit="mm",
        session_id=session_id,
    )

    assert state["status"] == "completed"
    assert state["outputs"].get("minimum_required_thickness") is not None
    assert state["outputs"].get("t_m") is not None
    report_step = next(step for step in state["progress"]["timeline"] if step["id"] == "report")
    assert report_step["status"] == "done"
