"""Center-panel scroll blocks must use only registered output block types."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _pytest.outcomes import Failed

from api.center_panel_block_registry import (
    assert_blocks_use_registered_center_panel_types,
    center_panel_block_type_entries,
    center_panel_block_types,
    load_center_panel_block_registry,
)
from api.center_panel_contract import (
    assemble_center_panel_scroll_blocks,
    presentation_package_from_task_state,
)
from api.output_blocks import build_display_outputs
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import run_completed_workflow
from tests.api.test_equation_display_trace import _apply_simulated_completed_state

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_JSON = ROOT / "contracts" / "center_panel_output_block_types.json"


def _reader() -> StandardsReader:
    return StandardsReader(ROOT / "knowledge" / "standards", standard="asme_b31.3")


def test_center_panel_block_registry_matches_contract_json() -> None:
    payload = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    registry_types = [entry["type"] for entry in center_panel_block_type_entries()]
    contract_types = [entry["type"] for entry in payload["block_types"]]
    assert registry_types == contract_types
    assert center_panel_block_types() == frozenset(contract_types)


def test_registry_entries_define_desktop_renderer_components() -> None:
    for entry in center_panel_block_type_entries():
        assert str(entry.get("desktop_component") or "").strip()
        assert str(entry.get("label") or "").strip()


def test_assert_helper_rejects_unregistered_block_type() -> None:
    with pytest.raises(Failed):
        assert_blocks_use_registered_center_panel_types(
            [{"id": "rogue-1", "type": "planner_json_blob"}],
            context="unit",
        )


TRACE_DERIVED_DISPLAY_BLOCK_PREFIXES = (
    "table-steps-",
    "table-intermediates-",
    "table-lookup-",
)


def _assert_no_trace_derived_display_blocks(
    blocks: list[dict],
    *,
    context: str,
) -> None:
    for block in blocks:
        block_id = str(block.get("id") or "")
        assert block_id != "graph-intermediates", f"{context}: graph block must not render"
        assert str(block.get("type") or "") != "graph", f"{context}: graph type must not render"
        for prefix in TRACE_DERIVED_DISPLAY_BLOCK_PREFIXES:
            assert not block_id.startswith(prefix), (
                f"{context}: trace-derived table {block_id!r} must not render"
            )


def test_pipe_wall_display_outputs_exclude_trace_derived_graph_and_tables() -> None:
    reader = _reader()
    manager = TaskStateManager()
    task_id = "center-panel-block-types-pipe-wall"
    run_completed_workflow(manager, reader, task_id)
    task = manager.get_task(task_id)
    blocks = build_display_outputs(task, reader=reader, standards_root=reader.standards_root)
    assert blocks
    assert_blocks_use_registered_center_panel_types(
        blocks,
        context="pipe_wall display_outputs",
    )
    _assert_no_trace_derived_display_blocks(blocks, context="pipe_wall display_outputs")


def test_simulated_equation_trace_scroll_blocks_use_registered_types_only() -> None:
    reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("center-panel-block-types-trace", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, reader)

    display_outputs = build_display_outputs(
        task,
        reader=reader,
        standards_root=reader.standards_root,
    )
    package = presentation_package_from_task_state(
        {
            "display_outputs": display_outputs,
            "flow_guidance": {"transcript_blocks": []},
        }
    )
    scroll_blocks = package["ordered_scroll_blocks"]
    assert scroll_blocks
    assert_blocks_use_registered_center_panel_types(
        scroll_blocks,
        context="simulated equation trace scroll blocks",
    )
    assert any(str(block.get("type")) == "equation" for block in scroll_blocks)


def test_center_panel_assembly_filters_unregistered_engineering_blocks() -> None:
    scroll_blocks = assemble_center_panel_scroll_blocks(
        transcript_blocks=[],
        display_outputs=[
            {
                "id": "rogue-engineering",
                "type": "internal_planner_dump",
                "content": "must not render",
            },
            {
                "id": "equation-asme-b313-304-1-2-eq-3a",
                "type": "equation",
                "display_role": "equation",
                "content": "t = 1 mm",
            },
        ],
    )
    assert_blocks_use_registered_center_panel_types(
        scroll_blocks,
        context="filtered scroll blocks",
    )
    ids = {str(block.get("id") or "") for block in scroll_blocks}
    assert "rogue-engineering" not in ids
    assert "equation-asme-b313-304-1-2-eq-3a" in ids


def test_filter_center_panel_blocks_removes_unregistered_types() -> None:
    from api.center_panel_block_registry import filter_center_panel_blocks

    filtered = filter_center_panel_blocks(
        [
            {"id": "eq-1", "type": "equation", "content": "t = 1"},
            {"id": "rogue", "type": "planner_state_json"},
        ]
    )
    assert len(filtered) == 1
    assert filtered[0]["id"] == "eq-1"


def test_task_state_display_outputs_use_registered_block_types_only(
    standards_reader,
    state_manager,
) -> None:
    from api.serializers import task_state

    task_id = "center-panel-block-types-task-state"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)
    state = task_state(task, state_manager, standards_root=standards_reader.standards_root)
    display_outputs = state.get("display_outputs") or []
    assert display_outputs
    assert_blocks_use_registered_center_panel_types(
        display_outputs,
        context="task_state display_outputs",
    )
    package = presentation_package_from_task_state(state)
    assert_blocks_use_registered_center_panel_types(
        package["ordered_scroll_blocks"],
        context="task_state ordered_scroll_blocks",
    )
    _assert_no_trace_derived_display_blocks(
        display_outputs,
        context="task_state display_outputs",
    )


def test_canonicalize_center_panel_block_type_maps_text_roles() -> None:
    from api.center_panel_block_registry import canonicalize_center_panel_block_type

    assert (
        canonicalize_center_panel_block_type(
            {"id": "result-summary-pipe", "type": "text", "display_role": "result_summary"}
        )["type"]
        == "result_summary"
    )
    assert (
        canonicalize_center_panel_block_type(
            {"id": "warning-1", "type": "text", "display_role": "warning"}
        )["type"]
        == "warning"
    )


def test_registry_metadata_is_stable() -> None:
    registry = load_center_panel_block_registry()
    assert registry.get("version") == 1
    assert "equation" in center_panel_block_types()
