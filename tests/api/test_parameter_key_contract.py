"""API contract: facts and parameter_id fields must use canonical PARAM registry keys."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.reference.parameter_keys import MATERIAL_GRADE_KEY
from tests.api.conftest import api_session_id
from tests.helpers.parameter_key_contract import (
    PIPE_WALL_SYSTEM_FACT_KEYS,
    assert_api_state_uses_canonical_parameter_keys,
    collect_api_parameter_fields,
    load_global_parameter_registry_keys,
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


def test_global_parameter_registry_contains_material_grade(project_root: Path) -> None:
    registry = load_global_parameter_registry_keys(project_root)
    assert MATERIAL_GRADE_KEY in registry
    assert "material" not in registry


def test_pipe_wall_api_state_uses_canonical_parameter_keys_through_journey(
    tmp_path: Path,
    project_root: Path,
) -> None:
    registry = load_global_parameter_registry_keys(project_root)
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    for _ in range(len(_INTERNAL_PRESSURE_SUBMISSIONS) + 4):
        assert_api_state_uses_canonical_parameter_keys(state, registry=registry)

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
            collected = collect_api_parameter_fields(state)
            pytest.fail(
                "unexpected parameter prompt before journey complete: "
                f"{parameter_id!r} (collected={collected})"
            )

        value, unit = _INTERNAL_PRESSURE_SUBMISSIONS[parameter_id]
        state = service.submit_input(
            task_id,
            parameter=parameter_id,
            value=value,
            unit=unit,
            session_id=session_id,
        )

    assert state.get("status") == "completed"
    assert_api_state_uses_canonical_parameter_keys(state, registry=registry)

    collected = collect_api_parameter_fields(state)
    assert MATERIAL_GRADE_KEY in collected["facts"]
    assert "material" not in collected["facts"]
    assert PIPE_WALL_SYSTEM_FACT_KEYS.issubset(collected["facts"])

    reloaded = service.get_task(task_id, session_id)
    assert_api_state_uses_canonical_parameter_keys(reloaded, registry=registry)
    assert collect_api_parameter_fields(reloaded)["facts"] == collected["facts"]
