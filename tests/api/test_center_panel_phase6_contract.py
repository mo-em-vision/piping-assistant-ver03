"""Phase 6 — center panel / report presentation contract and cross-phase regression."""

from __future__ import annotations

import json
from pathlib import Path

from api.center_panel_contract import (
    REPORT_ROLE_ORDER,
    assemble_center_panel_scroll_blocks,
    collect_visible_text,
    load_report_role_order,
    presentation_package_from_task_state,
    report_role_index,
)
from api.desktop_service import DesktopApiService
from api.flow_guidance_transcript import FLOW_GUIDANCE_TRANSCRIPT_KEY
from config.loader import CLIConfig
from engine.reports.report_data import build_report_from_task
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.api.conftest import api_session_id


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


def _shared_contract_path() -> Path:
    return Path(__file__).resolve().parents[2] / "contracts" / "center_panel_report_role_order.json"


def test_report_role_order_matches_shared_contract_file() -> None:
    payload = json.loads(_shared_contract_path().read_text(encoding="utf-8"))
    assert tuple(payload) == REPORT_ROLE_ORDER == load_report_role_order()


def test_shared_contract_file_is_canonical() -> None:
    payload = json.loads(_shared_contract_path().read_text(encoding="utf-8"))
    assert list(REPORT_ROLE_ORDER) == payload


def test_presentation_package_keeps_workflow_intro_before_narration() -> None:
    package = presentation_package_from_task_state(
        {
            "flow_guidance": {
                "transcript_blocks": [
                    {
                        "block_id": "result-summary-pipe_wall_thickness_design",
                        "kind": "text",
                        "source": "runtime",
                        "text": "Done.",
                        "payload": {"display_role": "result_summary"},
                    },
                    {
                        "block_id": "workflow-intro-pipe_wall_thickness_design",
                        "kind": "text",
                        "source": "runtime",
                        "text": "Intro.",
                        "payload": {"display_role": "workflow_intro"},
                    },
                ]
            },
            "display_outputs": [],
        }
    )
    ordered = package["ordered_scroll_blocks"]
    roles = [block["display_role"] for block in ordered]
    assert roles.index("workflow_intro") < roles.index("result_summary")


def test_display_outputs_remain_separate_engineering_snapshot(
    tmp_path: Path,
    project_root: Path,
    standards_reader,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    package = presentation_package_from_task_state(state)
    assert package["display_outputs"] == state["display_outputs"]
    assert package["transcript_blocks"] == state["flow_guidance"]["transcript_blocks"]
    assert package["display_outputs"] is not package["transcript_blocks"]


def test_report_data_ignores_transcript_display_history(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("phase6-report-truth", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["_execution_trace"] = [
        {
            "node_id": "304.1.2-a",
            "trace": {"calculation": {"final_result": {"value": 2.5, "unit": "mm"}}},
        }
    ]
    task.outputs[FLOW_GUIDANCE_TRANSCRIPT_KEY] = [
        {
            "block_id": "fake-transcript-only",
            "kind": "text",
            "source": "runtime",
            "text": "TRANSCRIPT_ONLY_ENGINEERING_TRUTH_MUST_NOT_APPEAR",
            "payload": {"display_role": "result_summary"},
        }
    ]

    report_before = build_report_from_task(task, standards_reader)
    task.outputs[FLOW_GUIDANCE_TRANSCRIPT_KEY].append(
        {
            "block_id": "fake-transcript-only-2",
            "kind": "text",
            "source": "runtime",
            "text": "MORE_TRANSCRIPT_ONLY_DATA",
            "payload": {"display_role": "workflow_intro"},
        }
    )
    report_after = build_report_from_task(task, standards_reader)

    assert report_before.task_id == report_after.task_id
    assert report_before.sections == report_after.sections
    assert report_before.traceability == report_after.traceability
    serialized = json.dumps(
        {
            "sections": [section.__dict__ for section in report_after.sections],
            "traceability": [entry.__dict__ for entry in report_after.traceability],
        },
        default=str,
    )
    assert "TRANSCRIPT_ONLY_ENGINEERING_TRUTH_MUST_NOT_APPEAR" not in serialized


def test_report_preview_package_uses_transcript_plus_display_outputs(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    package = presentation_package_from_task_state(state)
    assembled = assemble_center_panel_scroll_blocks(
        transcript_blocks=package["transcript_blocks"],
        display_outputs=package["display_outputs"],
    )
    assert assembled == package["ordered_scroll_blocks"]


def test_completed_task_cross_phase_contract(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    pre_short = str((state.get("current_ask") or {}).get("short_prompt") or "")
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

    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(task_id)
    task.status = TaskStatus.COMPLETED
    manager.replace_task(task_id, task)
    store.save_state_manager(manager)

    state = service.get_task(task_id, session_id)
    transcript = state["flow_guidance"]["transcript_blocks"]

    guidance = [block for block in transcript if block.get("kind") == "guidance"]
    assert guidance
    assert len({block["block_id"] for block in guidance}) == len(guidance)

    intros = [
        block
        for block in transcript
        if block.get("block_id", "").startswith("workflow-intro-")
    ]
    assert len(intros) == 1

    results = [
        block
        for block in transcript
        if block.get("block_id", "").startswith("result-summary-")
    ]
    assert len(results) == 1

    next_workflows = [block for block in transcript if block.get("kind") == "next_workflows"]
    assert len(next_workflows) == 1

    archives = [
        block
        for block in transcript
        if block.get("source") == "input_archive"
    ]
    ask_blocks = [block for block in archives if block.get("kind") == "ask_archive"]
    assert ask_blocks
    straight_ask = next(
        block for block in ask_blocks if "straight_pipe_section" in block.get("block_id", "")
    )
    assert straight_ask["text"] == pre_short
    assert len({block["block_id"] for block in ask_blocks}) == len(ask_blocks)

    block_ids = [block["block_id"] for block in transcript if block.get("block_id")]
    assert len(block_ids) == len(set(block_ids))

    second = service.get_task(task_id, session_id)
    assert second["flow_guidance"]["transcript_blocks"] == transcript

    short_prompt = str((state.get("current_ask") or {}).get("short_prompt") or "").strip().lower()
    transcript_text = " ".join(str(block.get("text") or "") for block in transcript).lower()
    if short_prompt:
        assert short_prompt not in transcript_text

    visible = collect_visible_text(
        presentation_package_from_task_state(state)["ordered_scroll_blocks"]
    ).lower()
    scroll_roles = [
        str(block.get("display_role") or "")
        for block in presentation_package_from_task_state(state)["ordered_scroll_blocks"]
    ]
    assert "ask_archive" not in scroll_roles
    assert "answer_archive" not in scroll_roles
    assert "engineering_plan" not in visible
    assert '"goal-' not in visible
    assert "asme-b313-" not in visible

    for block in state.get("display_outputs") or []:
        if block.get("type") != "equation":
            continue
        for row in (block.get("input_table") or {}).get("rows") or []:
            provenance = row.get("value_provenance") or {}
            if provenance.get("source_type") in {"equation_output", "table_lookup"}:
                assert provenance.get("status") != "awaiting_user_input"
                assert row.get("value") != "Awaiting user input"

    for block in transcript:
        chips = block.get("reference_chips") or []
        for chip in chips:
            chip_id = str(chip.get("id") or "")
            chip_label = str(chip.get("label") or "")
            if chip_id and chip_label:
                assert chip_label != chip_id


def test_phase_regression_modules_remain_importable() -> None:
    import tests.api.test_flow_guidance_phase1a  # noqa: F401
    import tests.api.test_flow_guidance_phase1b  # noqa: F401
    import tests.api.test_flow_guidance_phase1c  # noqa: F401
    import tests.api.test_flow_guidance_phase2  # noqa: F401
    import tests.api.test_flow_guidance_phase3  # noqa: F401
    import tests.api.test_equation_row_provenance  # noqa: F401
    import tests.api.test_flow_guidance_phase5  # noqa: F401
