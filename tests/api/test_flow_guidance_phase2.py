"""Phase 2 integration tests — durable input archive on submit."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
from api.flow_guidance_transcript import load_flow_guidance_transcript_blocks
from api.input_archive_transcript import InputArchiveEvent, append_input_archive_transcript
from config.loader import CLIConfig
from engine.state.state_manager import TaskStateManager
from models.fact import fact_from_user_submission
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


def _archive_blocks(transcript: list[dict]) -> list[dict]:
    return [
        block
        for block in transcript
        if isinstance(block, dict)
        and block.get("source") == "input_archive"
        and block.get("kind") in {"ask_archive", "answer_archive"}
    ]


def test_submit_appends_ask_and_answer_archive_once(tmp_path: Path, project_root: Path) -> None:
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

    transcript = state["flow_guidance"]["transcript_blocks"]
    archives = _archive_blocks(transcript)
    ask_blocks = [block for block in archives if block.get("kind") == "ask_archive"]
    answer_blocks = [block for block in archives if block.get("kind") == "answer_archive"]

    assert len(ask_blocks) == 1
    assert len(answer_blocks) == 1
    assert ask_blocks[0]["text"] == pre_short
    assert answer_blocks[0]["text"] == "Yes"
    assert ask_blocks[0]["block_id"] != answer_blocks[0]["block_id"]
    assert ask_blocks[0]["block_id"].startswith("archived-ask-straight_pipe_section-")
    assert answer_blocks[0]["block_id"].startswith("archived-answer-straight_pipe_section-")


def test_repeated_get_task_does_not_duplicate_archives(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )

    first = service.get_task(task_id, session_id)
    second = service.get_task(task_id, session_id)

    first_archives = _archive_blocks(first["flow_guidance"]["transcript_blocks"])
    second_archives = _archive_blocks(second["flow_guidance"]["transcript_blocks"])
    assert first_archives == second_archives
    assert len({block["block_id"] for block in first_archives}) == len(first_archives)


def test_archived_ask_uses_pre_submit_prompt_not_next_prompt(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    pre_short = str((state.get("current_ask") or {}).get("short_prompt") or "")
    assert "straight section" in pre_short.lower()

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )

    next_short = str((state.get("current_ask") or {}).get("short_prompt") or "")
    assert "internal or external" in next_short.lower()

    ask_blocks = [
        block
        for block in _archive_blocks(state["flow_guidance"]["transcript_blocks"])
        if block.get("kind") == "ask_archive"
    ]
    assert len(ask_blocks) == 1
    assert ask_blocks[0]["text"] == pre_short
    assert ask_blocks[0]["text"] != next_short


def test_resubmit_appends_distinct_archive_pair() -> None:
    manager = TaskStateManager()
    task = manager.create_task("archive-resubmit-test", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design"}

    fact_one = fact_from_user_submission(
        key="corrosion_allowance",
        value=0.5,
        unit="mm",
        task_id=task.task_id,
        workflow_id="pipe_wall_thickness_design",
    )
    fact_two = fact_from_user_submission(
        key="corrosion_allowance",
        value=1.0,
        unit="mm",
        task_id=task.task_id,
        workflow_id="pipe_wall_thickness_design",
    )
    assert fact_one.id != fact_two.id

    pre_ask = {
        "kind": "input",
        "parameter_id": "corrosion_allowance",
        "short_prompt": "Enter corrosion allowance c.",
        "prompt": "Enter the corrosion allowance c, including units.",
    }

    task, changed_one = append_input_archive_transcript(
        task,
        InputArchiveEvent(
            pre_submit_current_ask=pre_ask,
            submitted_parameter_id="corrosion_allowance",
            submitted_raw_value=0.5,
            submitted_unit="mm",
            fact=fact_one,
        ),
    )
    assert changed_one

    task, changed_two = append_input_archive_transcript(
        task,
        InputArchiveEvent(
            pre_submit_current_ask=pre_ask,
            submitted_parameter_id="corrosion_allowance",
            submitted_raw_value=1.0,
            submitted_unit="mm",
            fact=fact_two,
        ),
    )
    assert changed_two

    blocks = load_flow_guidance_transcript_blocks(task)
    ask_ids = [block.block_id for block in blocks if block.kind == "ask_archive"]
    answer_ids = [block.block_id for block in blocks if block.kind == "answer_archive"]
    assert len(ask_ids) == 2
    assert len(answer_ids) == 2
    assert len(set(ask_ids + answer_ids)) == 4


def test_transcript_excludes_active_prompt_and_presentation_blocks(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )

    transcript = state["flow_guidance"]["transcript_blocks"]
    assert not any(block.get("kind") == "prompt" for block in transcript if isinstance(block, dict))
    presentation_ids = {
        str(block.get("block_id"))
        for block in state.get("flow_guidance", {}).get("presentation_blocks") or []
        if isinstance(block, dict)
    }
    transcript_ids = {
        str(block.get("block_id")) for block in transcript if isinstance(block, dict)
    }
    assert presentation_ids.isdisjoint(transcript_ids) or not presentation_ids


def test_current_ask_still_from_planner_after_archive(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )

    current_ask = state.get("current_ask") or {}
    assert current_ask.get("kind") == "input"
    assert current_ask.get("parameter_id") == "pressure_loading"
    assert current_ask.get("prompt")
    assert current_ask.get("short_prompt")
