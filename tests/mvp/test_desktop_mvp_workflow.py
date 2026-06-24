"""MVP verification tests for the desktop engineering workflow.

Maps to roadmap Section 15 — MVP Completion Definition:
1. open application (Electron shell — covered by desktop build/tests)
2. create/select project
3. start engineering task
4. provide inputs
5. receive backend results
6. view calculations
7. generate report
"""

from __future__ import annotations

from api.desktop_service import DesktopApiService
from tests.acceptance.helpers import run_completed_workflow


def _submit_initial_pipe_inputs(service: DesktopApiService, task_id: str, session_id: str) -> dict:
    submissions = [
        ("pressure_loading", "internal_pressure", None),
        ("material", "SA-106B", None),
        ("design_pressure", 8.0, "bar"),
        ("design_temperature", 38.0, "degC"),
    ]

    state: dict = service.get_task(task_id, session_id)
    for parameter, value, unit in submissions:
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


def test_mvp_project_task_and_input_collection(mvp_service: DesktopApiService) -> None:
    project = mvp_service.create_project("MVP Verification Project")
    activated = mvp_service.activate_project(project["id"])
    session_id = activated["session_id"]

    task_state = mvp_service.create_task("pipe_wall_thickness_design", session_id)
    task_id = task_state["task_id"]
    assert task_state["workflow_id"] == "pipe_wall_thickness_design"
    assert task_state["parameters"][0]["name"] == "pressure_loading"
    assert task_state["active_nodes"] == ["B313-304.1.1"]

    updated = _submit_initial_pipe_inputs(mvp_service, task_id, session_id)
    assert "material" in updated["inputs"]
    assert updated["inputs"]["material"]["value"] == "SA-106B"

    tasks = mvp_service.list_tasks(session_id)
    assert len(tasks["tasks"]) == 1
    assert tasks["tasks"][0]["id"] == task_id


def test_mvp_calculation_outputs_and_report(
    mvp_service: DesktopApiService,
    standards_reader,
    state_manager,
) -> None:
    project = mvp_service.create_project("MVP Report Project")
    session_id = mvp_service.activate_project(project["id"])["session_id"]

    task_id = "pipe-wall-thickness-desi-mvp01"
    run_completed_workflow(state_manager, standards_reader, task_id)
    mvp_service._save_manager(state_manager, session_id)

    state = mvp_service.get_task(task_id, session_id)
    assert state["display_outputs"]
    assert state["progress"]["timeline"]

    generated = mvp_service.generate_task_report(task_id, report_format="html", session_id=session_id)
    assert generated["generation_status"] == "ready"
    assert generated["files"]["html"]["available"] is True

    preview = mvp_service.preview_task_report(task_id, preview_format="html", session_id=session_id)
    assert preview["content"]


def test_mvp_workflow_catalog_available(mvp_service: DesktopApiService) -> None:
    workflows = mvp_service.list_workflows()
    pipe = next(item for item in workflows if item["id"] == "pipe_wall_thickness_design")
    assert pipe["available"] is True
