"""API journey regression for MAWP geometry path (NPS + schedule, no deadlock)."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.router import MAWP_DESIGN
from tests.api.conftest import api_session_id

_REPO_ROOT = Path(__file__).resolve().parents[2]

_MAWP_SUBMISSIONS: list[tuple[str, object, str | None]] = [
    ("straight_pipe_section", True, None),
    ("wall_thickness_basis", "nominal_schedule", None),
    ("outside_diameter__resolution_branch", "nps_lookup", None),
    ("nominal_pipe_size", "6", None),
    ("pipe_schedule", "40", None),
    ("material_grade", "SA-106B", None),
    ("design_temperature", 38.0, "C"),
    ("corrosion_allowance", 0.0, "mm"),
    ("pipe_construction_type", "Seamless pipe", None),
]

_COEFFICIENT_PROMPT_KEYS = frozenset(
    {
        "basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
        "allowable_stress",
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


def _submit_while_requested(
    service: DesktopApiService,
    task_id: str,
    session_id: str,
    submissions: list[tuple[str, object, str | None]],
) -> dict:
    state: dict = service.get_task(task_id, session_id)
    remaining = list(submissions)
    max_passes = max(len(remaining) * 4, 1)

    for _ in range(max_passes):
        if not remaining:
            break
        state = service.get_task(task_id, session_id)
        submittable = set(state.get("progress", {}).get("submittable_parameters") or [])
        still_remaining: list[tuple[str, object, str | None]] = []
        progressed = False
        for parameter, value, unit in remaining:
            if parameter not in submittable and not (
                parameter == "outside_diameter__resolution_branch"
                and "outside_diameter" in submittable
            ):
                still_remaining.append((parameter, value, unit))
                continue
            state = service.submit_input(
                task_id,
                parameter=parameter,
                value=value,
                unit=unit,
                session_id=session_id,
            )
            progressed = True
        remaining = still_remaining
        if not progressed:
            break
    return state


def test_mawp_nps_geometry_path_not_blocked_after_seamless_pipe(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service, "MAWP geometry journey")
    created = service.create_task(MAWP_DESIGN, session_id)
    task_id = created["task_id"]

    state = _submit_while_requested(
        service,
        task_id,
        session_id,
        _MAWP_SUBMISSIONS,
    )

    submittable = set(state.get("progress", {}).get("submittable_parameters") or [])
    overlap = sorted(submittable & _COEFFICIENT_PROMPT_KEYS)
    assert not overlap, (
        "Lookup-derived coefficients must not remain user-submittable after seamless pipe; "
        f"found: {overlap}"
    )

    planning = state.get("planning") or {}
    root_goal = planning.get("root_goal") or {}
    blocked_by = root_goal.get("blocked_by") or []
    assert "outside_diameter" not in blocked_by, (
        "NPS mode must not deadlock on direct outside_diameter after schedule lookup"
    )
    assert "actual_wall_thickness" not in blocked_by, (
        "NPS mode must not deadlock on direct wall thickness after schedule lookup"
    )

    facts = state.get("facts") or {}
    assert facts.get("outside_diameter") is not None
    assert facts.get("actual_wall_thickness") is not None
