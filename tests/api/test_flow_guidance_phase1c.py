"""Phase 1C integration tests — short composer prompts and scroll/composer dedup."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
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


def _transcript_text(state: dict) -> str:
    parts: list[str] = []
    for block in state.get("flow_guidance", {}).get("transcript_blocks") or []:
        if isinstance(block, dict):
            parts.append(str(block.get("text") or ""))
    return " ".join(parts)


def test_current_ask_includes_short_prompt_shorter_than_full_prompt(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)

    current_ask = state.get("current_ask") or {}
    assert current_ask.get("kind") == "input"
    assert current_ask.get("parameter_id") == "straight_pipe_section"

    full_prompt = str(current_ask.get("prompt") or "")
    short_prompt = str(current_ask.get("short_prompt") or "")
    assert short_prompt
    assert len(short_prompt) < len(full_prompt)
    assert "choose one" not in short_prompt.lower()
    assert "reply with" not in short_prompt.lower()
    assert "straight section" in short_prompt.lower()


def test_pressure_loading_short_prompt_omits_numbered_branch_options(
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
    current_ask = state.get("current_ask") or {}
    assert current_ask.get("parameter_id") == "pressure_loading"

    short_prompt = str(current_ask.get("short_prompt") or "")
    full_prompt = str(current_ask.get("prompt") or "")
    assert short_prompt
    assert "1." not in short_prompt
    assert "304.1.2" not in short_prompt
    assert "304.1.2" in full_prompt
    assert len(short_prompt) < len(full_prompt)


def test_composer_short_prompt_not_duplicated_in_transcript_narration(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)

    short_prompt = str((state.get("current_ask") or {}).get("short_prompt") or "").strip().lower()
    transcript = _transcript_text(state).lower()
    assert short_prompt
    assert short_prompt not in transcript


def test_guidance_input_context_appears_in_transcript_for_parameter_gathering(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    values: dict[str, tuple[object, str | None]] = {
        "straight_pipe_section": (True, None),
        "pressure_loading": ("internal_pressure", None),
        "corrosion_allowance": (0.5, "mm"),
        "design_temperature": (200.0, "C"),
        "internal_design_gage_pressure": (8.0, "bar"),
        "nominal_pipe_size": ("4", None),
        "material_grade": ("ASTM A106 Grade B", None),
    }
    for _ in range(20):
        current_ask = state.get("current_ask") or {}
        if current_ask.get("parameter_id") == "internal_design_gage_pressure":
            break
        submittable = state["progress"].get("submittable_parameters") or []
        param = current_ask.get("parameter_id") or (submittable[0] if submittable else None)
        if not isinstance(param, str) or param not in values:
            break
        value, unit = values[param]
        state = service.submit_input(
            task_id,
            parameter=param,
            value=value,
            unit=unit,
            session_id=session_id,
        )

    current_ask = state.get("current_ask") or {}
    assert current_ask.get("parameter_id") == "internal_design_gage_pressure"
    short_prompt = str(current_ask.get("short_prompt") or "").lower()
    assert "500 psi" not in short_prompt

    transcript = state["flow_guidance"]["transcript_blocks"]
    input_context = [
        block
        for block in transcript
        if isinstance(block, dict)
        and (block.get("payload") or {}).get("display_role") == "input_context"
    ]
    assert input_context
    assert any("internal design gage pressure" in str(block.get("text") or "").lower() for block in input_context)
