"""Regression tests for pipe wall center panel output lifecycle."""

from __future__ import annotations

from api.center_panel_contract import report_role_index
from api.display_block_metadata import append_equation_trace_blocks, tag_equation_block
from api.output_blocks import build_display_outputs
from api.serializers import task_state
from engine.state.state_manager import TaskStateManager
from models.display_role import DisplayRole, DisplayState
from models.task import TaskStatus
from tests.api.test_equation_display_trace import (
    EQ_2_ID,
    EQ_3A_ID,
    _apply_simulated_completed_state,
)
from tests.helpers.goals import task_with_planning

AWAITING = "Awaiting user input"
EQ_2_BLOCK_ID = "equation-asme-b313-304-1-1-eq-2"
EQ_3A_BLOCK_ID = "equation-asme-b313-304-1-2-eq-3a"


def test_api_display_role_emits_canonical_equation_shape(standards_reader) -> None:
    block = tag_equation_block(
        {"id": EQ_3A_BLOCK_ID, "type": "equation"},
        display_state=DisplayState.evaluated.value,
        equation_node_id=EQ_3A_ID,
        source_node_id="304.1.2-a",
    )
    assert block["display_role"] == DisplayRole.equation.value
    assert block["display_state"] == DisplayState.evaluated.value
    assert block.get("internal_display_role") is None


def test_contract_role_ordering_equation_single_slot() -> None:
    assert report_role_index(DisplayRole.equation.value) == report_role_index("equation")
    assert report_role_index(DisplayRole.branch_narration.value) < report_role_index(
        DisplayRole.equation.value
    )


def test_post_eval_pipe_wall_omits_eq3a_preview(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-lifecycle-post-eval", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "definition_equation_completion",
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    _apply_simulated_completed_state(task, standards_reader)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    preview_eq_ids = [
        str(block.get("equation_node_id"))
        for block in blocks
        if str(block.get("id", "")).startswith("path-preview-equation-")
    ]
    assert EQ_3A_ID not in preview_eq_ids

    trace_blocks = [
        block
        for block in blocks
        if str(block.get("id", "")) == EQ_3A_BLOCK_ID
        or str(block.get("equation_node_id")) == EQ_3A_ID
    ]
    assert any(str(block.get("equation_node_id")) == EQ_3A_ID for block in trace_blocks)


def test_post_eval_no_legacy_substituted_when_trace_present(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-lifecycle-no-sub", status=TaskStatus.AWAITING_INPUT)
    task_with_planning(
        task,
        {"path_decision": {"selected_node": "304.1.2-a"}},
        workflow_id="pipe_wall_thickness_design",
    )
    _apply_simulated_completed_state(task, standards_reader)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = {block.get("id") for block in blocks}
    assert "path-calculation-substituted-equation" not in ids


def test_evaluated_trace_input_table_has_no_awaiting_user_input(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-lifecycle-awaiting", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)

    blocks = append_equation_trace_blocks([], task, standards_reader)
    eq3a_trace = next(
        block for block in blocks if str(block.get("equation_node_id")) == EQ_3A_ID
    )
    rows = (eq3a_trace.get("input_table") or {}).get("rows") or []
    for row in rows:
        assert AWAITING not in str(row.get("value") or "")


def test_trace_blocks_generated_from_execution_trace_without_preview(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-lifecycle-exec-only", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)

    blocks = append_equation_trace_blocks([], task, standards_reader)
    equation_ids = {str(block.get("equation_node_id")) for block in blocks}
    assert EQ_3A_ID in equation_ids


def test_serializer_display_outputs_emit_canonical_roles(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-lifecycle-serializer", status=TaskStatus.AWAITING_INPUT)
    task_with_planning(
        task,
        {"path_decision": {"selected_node": "304.1.2-a"}},
        workflow_id="pipe_wall_thickness_design",
    )
    _apply_simulated_completed_state(task, standards_reader)
    manager.replace_task(task.task_id, task)

    state = task_state(task, manager, reader=standards_reader)
    roles = {block.get("display_role") for block in state.get("display_outputs") or []}
    internal_roles = {
        block.get("internal_display_role") for block in state.get("display_outputs") or []
    }
    assert DisplayRole.equation.value in roles
    assert not roles.intersection(
        {"preview", "equation_trace", "substituted", "calculation_trace", "equation_preview"}
    )
    assert not internal_roles or all(role is None for role in internal_roles)


def test_eq2_trace_coexists_with_eq3a_evaluated_state(standards_reader) -> None:
    """After eq-3a evaluates, durable eq-2 trace can still be emitted from execution trace."""
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-lifecycle-multi-eq", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)

    blocks = append_equation_trace_blocks([], task, standards_reader)
    equation_ids = {str(block.get("equation_node_id")) for block in blocks}
    assert EQ_3A_ID in equation_ids
    assert EQ_2_ID in equation_ids


def test_gate_phase_single_eq3a_preview_before_thickness_eval(
    tmp_path, project_root,
    ) -> None:
    """After expansion/path gates only: eq-3a preview only until upstream thickness exists."""
    from api.desktop_service import DesktopApiService
    from config.loader import CLIConfig
    from tests.api.conftest import api_session_id

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
    service = DesktopApiService(config=config, session_id="default")
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    for param, value in [
        ("straight_pipe_section", True),
        ("pressure_loading", "internal_pressure"),
    ]:
        service.submit_input(task_id, parameter=param, value=value, unit=None, session_id=session_id)

    state = service.get_task(task_id, session_id)
    blocks = state.get("display_outputs") or []
    block_ids = [str(block.get("id")) for block in blocks]

    preview_eq = [
        block
        for block in blocks
        if str(block.get("equation_node_id")) == EQ_3A_ID
    ]
    assert len(preview_eq) == 1
    assert preview_eq[0].get("id") == EQ_3A_BLOCK_ID
    assert str(preview_eq[0].get("title") or "").strip()
    assert str(preview_eq[0].get("context_intro") or "").strip()
    assert "paragraph-304.1.2-a" in block_ids
    eq2_blocks = [
        block for block in blocks if str(block.get("equation_node_id")) == EQ_2_ID
    ]
    assert len(eq2_blocks) == 0
    assert not any(str(block.get("id", "")).startswith("equation-trace-") for block in blocks)
    assert not any(str(block.get("id", "")).startswith("path-preview-equation-") for block in blocks)
    assert not any(str(block.get("id", "")).startswith("node-activation-equation-") for block in blocks)
    assert state["outputs"].get("required_thickness") is None
