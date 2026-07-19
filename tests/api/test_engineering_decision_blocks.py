"""Engineering decision blocks — node-owned copy, transcript, and scroll contract."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from api.center_panel_contract import presentation_package_from_task_state
from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.messaging.decision_interaction_resolver import (
    NODE_OWNED_DECISION_KEYS,
    resolve_decision_interaction,
)
from engine.messaging.decision_statement import render_decision_statement
from engine.messaging.parameter_input_prompt import build_parameter_input_prompt
from engine.reference.parameter_keys import load_parameter_node_metadata
from engine.reference.standards_reader import StandardsReader
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


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _decision_blocks(transcript: list[dict]) -> list[dict]:
    return [
        block
        for block in transcript
        if isinstance(block, dict) and block.get("source") == "engineering_decision"
    ]


def _scroll_decision_blocks(state: dict) -> list[dict]:
    package = presentation_package_from_task_state(state)
    return [
        block
        for block in package["ordered_scroll_blocks"]
        if str(block.get("display_role") or "") == "engineering_decision"
    ]


def _archive_blocks(transcript: list[dict]) -> list[dict]:
    return [
        block
        for block in transcript
        if isinstance(block, dict) and block.get("source") == "input_archive"
    ]


@pytest.mark.parametrize("decision_key", sorted(NODE_OWNED_DECISION_KEYS))
def test_node_owned_decision_resolves_from_single_authored_owner(
    project_root: Path,
    tmp_path: Path,
    decision_key: str,
) -> None:
    """Proof 1 — each migrated decision has exactly one node-owned copy source."""
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]
    reader = _reader(project_root)
    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(task_id)

    if decision_key.endswith("__resolution_branch"):
        service.submit_input(task_id, parameter="straight_pipe_section", value=True, session_id=session_id)
        service.submit_input(
            task_id,
            parameter="pressure_design_case",
            value="internal_pressure",
            session_id=session_id,
        )
        manager = store.load_state_manager()
        task = manager.get_task(task_id)

    view = resolve_decision_interaction(reader, task, decision_key)
    assert view is not None
    assert view.question.strip()
    assert view.options
    assert all(option.report_statement.strip() for option in view.options)

    if decision_key == "straight_pipe_section":
        assert view.requesting_node_id == "304.1.1-a"
    elif decision_key == "pressure_design_case":
        assert view.requesting_node_id == "304.1.1-a"
    elif decision_key.endswith("__resolution_branch"):
        assert view.requesting_node_id == "PARAM-outside-diameter"


def test_migrated_decisions_do_not_fallback_to_param_user_prompt(
    project_root: Path,
    tmp_path: Path,
) -> None:
    """Proof 2 — PARAM nodes no longer own decision prompts for migrated keys."""
    reader = _reader(project_root)
    for param_id in ("PARAM-straight-pipe-section", "PARAM-pressure-design-case"):
        meta = load_parameter_node_metadata(param_id)
        assert meta is not None
        block = meta.get("metadata") or meta
        assert not block.get("user_prompt")
        assert not block.get("composer_options")

    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    store = service._store_for(session_id)
    task = store.load_state_manager().get_task(state["task_id"])
    prompt = build_parameter_input_prompt(reader, task, "straight_pipe_section")
    assert "straight section" in prompt.lower()
    assert "straight_pipe_section" not in prompt


def test_unresolved_prompt_not_in_scroll_blocks(tmp_path: Path, project_root: Path) -> None:
    """Proof 3 — composer prompts stay out of ordered_scroll_blocks."""
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    pre_short = str((state.get("current_ask") or {}).get("short_prompt") or "").strip().lower()
    assert pre_short

    scroll_text = " ".join(
        str(block.get("content") or block.get("text") or "")
        for block in presentation_package_from_task_state(state)["ordered_scroll_blocks"]
    ).lower()
    assert pre_short not in scroll_text


def test_submit_creates_one_engineering_decision_block_per_key(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Proof 4 — one visible engineering_decision block per submitted decision key."""
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
    decisions = _decision_blocks(transcript)
    assert len(decisions) == 1
    assert decisions[0]["block_id"] == "engineering-decision-straight_pipe_section"

    scroll = _scroll_decision_blocks(state)
    assert len(scroll) == 1
    assert scroll[0]["id"] == "engineering-decision-straight_pipe_section"


def test_engineering_decision_uses_canonical_display_role(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Proof 5 — decision blocks use engineering_decision, not scope_assumption."""
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
    block = _decision_blocks(state["flow_guidance"]["transcript_blocks"])[0]
    payload = block.get("payload") or {}
    assert payload.get("display_role") == "engineering_decision"
    assert payload.get("display_role") != "scope_assumption"


def test_rendered_text_matches_authored_report_statement(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Proof 6 — rendered text follows authored report_statement with resolved refs."""
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]
    reader = _reader(project_root)

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    block = _decision_blocks(state["flow_guidance"]["transcript_blocks"])[0]
    rendered = str(block.get("text") or "")
    assert "ASME B31.3 §304.1.1" in rendered
    assert "straight pipe section" in rendered.lower()
    assert "{" not in rendered

    store = service._store_for(session_id)
    task = store.load_state_manager().get_task(task_id)
    view = resolve_decision_interaction(reader, task, "straight_pipe_section")
    assert view is not None
    expected = render_decision_statement(
        reader,
        view=view,
        selected_value=True,
        activated_node_ids=[],
    )
    assert block["text"] == expected


def test_rejected_option_labels_absent_from_decision_block(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Proof 7 — only the selected branch label appears in the decision block."""
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
    rendered = str(_decision_blocks(state["flow_guidance"]["transcript_blocks"])[0].get("text") or "")
    assert "fitting, bend, or other non-straight component" not in rendered
    assert "not a straight pipe section" not in rendered.lower()


def test_placeholder_references_resolve_from_node_metadata(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Proof 8 — requesting/activated references come from presentation metadata."""
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
    state = service.submit_input(
        task_id,
        parameter="pressure_design_case",
        value="internal_pressure",
        session_id=session_id,
    )
    block = next(
        item
        for item in _decision_blocks(state["flow_guidance"]["transcript_blocks"])
        if item.get("block_id") == "engineering-decision-pressure_design_case"
    )
    rendered = str(block.get("text") or "")
    assert "internal pressure" in rendered.lower()
    assert "§304.1.2" in rendered or "304.1.2" in rendered
    assert "external pressure" not in rendered.lower()


def test_archives_remain_in_transcript_but_not_scroll_roles(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Proof 9 — ask/answer archives stay audit-only."""
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
    archives = _archive_blocks(transcript)
    assert any(block.get("kind") == "ask_archive" for block in archives)
    assert any(block.get("kind") == "answer_archive" for block in archives)

    scroll_roles = [
        str(block.get("display_role") or "")
        for block in presentation_package_from_task_state(state)["ordered_scroll_blocks"]
    ]
    assert "ask_archive" not in scroll_roles
    assert "answer_archive" not in scroll_roles


def test_repeated_get_task_does_not_duplicate_decision_blocks(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Proof 10 — reload does not duplicate decision blocks."""
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
    first_ids = [block["block_id"] for block in _decision_blocks(first["flow_guidance"]["transcript_blocks"])]
    second_ids = [block["block_id"] for block in _decision_blocks(second["flow_guidance"]["transcript_blocks"])]
    assert first_ids == second_ids == ["engineering-decision-straight_pipe_section"]


def test_resubmit_updates_decision_block_in_place(tmp_path: Path, project_root: Path) -> None:
    """Proof 11 — changing the answer updates the same block id."""
    from api.engineering_decision_transcript import (
        EngineeringDecisionEvent,
        append_engineering_decision_transcript,
        latest_decision_for_key,
    )
    from engine.state.decision_recorder import record_decision_from_fact

    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]
    reader = _reader(project_root)

    service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    first_text = _decision_blocks(
        service.get_task(task_id, session_id)["flow_guidance"]["transcript_blocks"]
    )[0]["text"]

    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(task_id)
    record_decision_from_fact(task, "straight_pipe_section", False, reader=reader)
    decision = latest_decision_for_key(task, "straight_pipe_section")
    assert decision is not None
    task, _changed = append_engineering_decision_transcript(
        task,
        reader,
        EngineeringDecisionEvent(decision_key="straight_pipe_section", decision=decision),
    )
    manager.replace_task(task_id, task)
    store.save_state_manager(manager)

    blocks = _decision_blocks(
        service.get_task(task_id, session_id)["flow_guidance"]["transcript_blocks"]
    )
    assert len(blocks) == 1
    assert blocks[0]["block_id"] == "engineering-decision-straight_pipe_section"
    assert blocks[0]["text"] != first_text
    assert "not a straight pipe section" in str(blocks[0]["text"]).lower()


def test_composer_payload_includes_option_help_text(tmp_path: Path, project_root: Path) -> None:
    """Proof 12 — composer options expose node-owned help_text for tooltips."""
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    params = {item["name"]: item for item in state.get("parameters") or []}
    straight = params["straight_pipe_section"]
    assert straight.get("help_text")
    options = straight.get("options") or []
    assert any(option.get("help_text") for option in options)

    service.submit_input(
        state["task_id"],
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    state = service.get_task(state["task_id"], session_id)
    params = {item["name"]: item for item in state.get("parameters") or []}
    pressure = params["pressure_design_case"]
    assert pressure.get("help_text")
    assert any(option.get("help_text") for option in pressure.get("options") or [])


def test_generic_renderer_has_no_workflow_or_node_id_branches() -> None:
    """Proof 13 — generic decision renderer stays metadata-driven."""
    root = Path(__file__).resolve().parents[2]
    decision_statement = (root / "engine" / "messaging" / "decision_statement.py").read_text(
        encoding="utf-8"
    )
    decision_transcript = (root / "api" / "engineering_decision_transcript.py").read_text(
        encoding="utf-8"
    )
    for source in (decision_statement, decision_transcript):
        assert "pipe_wall_thickness_design" not in source
        assert 'if workflow ==' not in source
        assert "if node_id ==" not in source
        assert "if interaction_id ==" not in source


def test_planner_modules_do_not_own_decision_report_copy() -> None:
    """Proof 14 — planner does not author decision report sentences."""
    root = Path(__file__).resolve().parents[2]
    planner_dir = root / "engine" / "planner"
    joined = "\n".join(path.read_text(encoding="utf-8") for path in planner_dir.glob("*.py"))
    assert "report_statement" not in joined
    assert "engineering_decision" not in joined
    assert "engineering-decision-" not in joined


def test_engineering_decision_role_present_in_contract() -> None:
    """Proof 15 — shared contract keeps engineering_decision ordering slot."""
    contract_path = Path(__file__).resolve().parents[2] / "contracts" / "center_panel_report_role_order.json"
    roles = contract_path.read_text(encoding="utf-8")
    assert '"engineering_decision"' in roles
    assert roles.index('"engineering_decision"') > roles.index('"scope_assumption"')
