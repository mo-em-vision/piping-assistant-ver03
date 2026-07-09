"""Schedule lookup trace persistence → generic table display block."""

from __future__ import annotations

from engine.executor.pipe_schedule_recommendation import (
    B36_10_TRACE_NODE_ID,
    append_schedule_lookup_trace_to_payload,
    build_b36_10_schedule_lookup_trace_entry,
)
from engine.state.state_manager import TaskStateManager
from models.input import InputSource, InputStatus
from models.task import TaskStatus

from api.output_blocks import build_display_outputs
from tests.helpers.facts import legacy_input, set_fact_from_input


def test_schedule_trace_entry_appended_once_and_rendered(project_root) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("schedule-trace-e2e", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["minimum_required_thickness"] = 2.252
    task.outputs["t_m"] = 2.252
    set_fact_from_input(
        task,
        legacy_input(
            input_id="nominal_pipe_size",
            value="2",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )

    trace_payload: list[dict] = []
    assert append_schedule_lookup_trace_to_payload(task, trace_payload, standards_root) is True
    assert append_schedule_lookup_trace_to_payload(task, trace_payload, standards_root) is False
    assert len(trace_payload) == 1
    assert trace_payload[0]["node_id"] == B36_10_TRACE_NODE_ID

    task.outputs["_execution_trace"] = trace_payload
    blocks = build_display_outputs(task, standards_root=standards_root)
    table_blocks = [
        block for block in blocks if str(block.get("id", "")).startswith("table-lookup-")
    ]
    assert table_blocks
    table = table_blocks[0]
    assert table.get("highlight_row")
    assert table.get("rows")


def test_build_schedule_trace_entry_shape(project_root) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("schedule-trace-shape", status=TaskStatus.COMPLETED)
    task.outputs["t_m"] = 0.73
    set_fact_from_input(
        task,
        legacy_input(
            input_id="nominal_pipe_size",
            value="2",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )

    entry = build_b36_10_schedule_lookup_trace_entry(task, standards_root)
    assert entry is not None
    lookup = entry["trace"]["lookup"]
    assert lookup.get("rows")
    assert lookup.get("highlight", {}).get("column") == "schedule"
    assert lookup.get("recommendation_summary")
