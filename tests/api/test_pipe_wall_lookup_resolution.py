"""API contract: completed pipe-wall task state resolves lookup keys to table-derived values."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from tests.api.conftest import api_session_id
from tests.helpers.lookup_resolution_contract import (
    assert_pipe_wall_lookup_resolution_in_final_state,
)

_INTERNAL_PRESSURE_SUBMISSIONS: dict[str, tuple[object, str | None]] = {
    "straight_pipe_section": (True, None),
    "pressure_design_case": ("internal_pressure", None),
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


def _completed_internal_pressure_state(
    service: DesktopApiService,
    session_id: str,
) -> dict:
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
            pytest.fail(f"unexpected prompt before journey complete: {parameter_id!r}")

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


def test_completed_pipe_wall_task_state_resolves_lookup_keys(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = _completed_internal_pressure_state(service, session_id)

    assert_pipe_wall_lookup_resolution_in_final_state(state)

    reloaded = service.get_task(state["task_id"], session_id)
    assert_pipe_wall_lookup_resolution_in_final_state(reloaded)
