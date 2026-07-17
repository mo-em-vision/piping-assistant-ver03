"""MAWP navigation characterization tests."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.router import MAWP_DESIGN
from tests.api.conftest import api_session_id
from tests.api.test_mawp_geometry_journey import _MAWP_SUBMISSIONS

_APPROVED_FIRST_FIVE = [step[0] for step in _MAWP_SUBMISSIONS[:5]]


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


def _is_submittable(submittable: set[str], parameter: str) -> bool:
    if parameter in submittable:
        return True
    return parameter == "outside_diameter__resolution_branch" and "outside_diameter" in submittable


def _resolution_branch_preseeded(service: DesktopApiService, task_id: str, session_id: str) -> bool:
    manager = service._store_for(session_id).load_state_manager()
    task = manager.get_task(task_id)
    return task.fact_store.active_fact("outside_diameter__resolution_branch") is not None


def _observe_first_five_input_steps(
    service: DesktopApiService,
    task_id: str,
    session_id: str,
) -> list[str]:
    """Record when each approved MAWP step is satisfied during the API journey."""
    satisfied: set[str] = set()
    remaining = list(_MAWP_SUBMISSIONS)
    max_passes = max(len(remaining) * 4, 1)

    if _resolution_branch_preseeded(service, task_id, session_id):
        satisfied.add("outside_diameter__resolution_branch")

    for _ in range(max_passes):
        if satisfied.issuperset(_APPROVED_FIRST_FIVE):
            break
        state = service.get_task(task_id, session_id)
        submittable = set(state.get("progress", {}).get("submittable_parameters") or [])
        still_remaining: list[tuple[str, object, str | None]] = []
        progressed = False
        for parameter, value, unit in remaining:
            if parameter in satisfied:
                continue
            if not _is_submittable(submittable, parameter):
                still_remaining.append((parameter, value, unit))
                continue
            service.submit_input(
                task_id,
                parameter=parameter,
                value=value,
                unit=unit,
                session_id=session_id,
            )
            if parameter in _APPROVED_FIRST_FIVE:
                satisfied.add(parameter)
            progressed = True
        remaining = still_remaining
        if not progressed:
            break

    return [step for step in _APPROVED_FIRST_FIVE if step in satisfied]


def test_mawp_observed_first_five_input_steps(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service, "MAWP navigation characterization")
    created = service.create_task(MAWP_DESIGN, session_id)
    task_id = created["task_id"]

    observed = _observe_first_five_input_steps(service, task_id, session_id)
    assert observed == _APPROVED_FIRST_FIVE
